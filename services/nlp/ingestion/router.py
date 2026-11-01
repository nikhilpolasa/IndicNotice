"""Validated document ingestion with page-level native/OCR routing."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pymupdf

from indicnotice.schemas.document import Document, DocumentBlock, DocumentPage
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.ingestion.errors import (
    NoReadableTextError,
    OCRBackendUnavailableError,
    PageLimitExceededError,
)
from services.nlp.ingestion.native_pdf import NativePDFBackend
from services.nlp.ingestion.types import IngestionResult, PageRoute
from services.nlp.ingestion.validation import ValidatedInput, validate_input
from services.nlp.language_id.script_detector import ScriptHeuristicDetector


class DocumentIngestor:
    """The NLP-1 orchestration boundary for PDF, PNG, and JPEG input."""

    def __init__(
        self,
        *,
        ocr_backend: object | None = None,
        language_detector: ScriptHeuristicDetector | None = None,
        max_bytes: int = 50 * 1024 * 1024,
        max_pages: int = 250,
        min_native_characters: int = 20,
        render_dpi: int = 300,
        cache_dir: str | Path = ".cache/nlp1",
    ):
        self.ocr_backend = ocr_backend
        self.language_detector = language_detector or ScriptHeuristicDetector()
        self.max_bytes = max_bytes
        self.max_pages = max_pages
        self.min_native_characters = min_native_characters
        self.render_dpi = render_dpi
        self.cache_dir = Path(cache_dir)
        self.native = NativePDFBackend(max_pages=max_pages)

    def ingest(self, document_path: str | Path) -> IngestionResult:
        validated = validate_input(document_path, max_bytes=self.max_bytes)
        if validated.media_type == "application/pdf":
            document, evidence, routes = self._ingest_pdf(validated)
        else:
            document, evidence, routes = self._ingest_image(validated)
        document, evidence = self._apply_language_labels(document, evidence)
        if not document.full_text.strip():
            raise NoReadableTextError("Document contains no readable text after extraction.")
        return IngestionResult(document, evidence, validated.sha256, validated.media_type, routes)

    def _ingest_image(self, validated: ValidatedInput) -> tuple[Document, tuple[EvidenceSpan, ...], tuple[PageRoute, ...]]:
        if self.ocr_backend is None:
            raise OCRBackendUnavailableError("Image input requires an OCR backend.")
        extractor = getattr(self.ocr_backend, "extract_with_evidence", None)
        if extractor is not None:
            document, evidence = extractor(str(validated.path))
        else:
            document = self.ocr_backend.extract(str(validated.path))
            evidence = self._evidence_from_document(document)
        if not document.pages:
            raise NoReadableTextError("OCR backend returned a document with no pages.")
        route = PageRoute(1, document.pages[0].extraction_method, "image inputs require OCR", 0)
        return document, evidence, (route,)

    def _ingest_pdf(self, validated: ValidatedInput) -> tuple[Document, tuple[EvidenceSpan, ...], tuple[PageRoute, ...]]:
        source = self.native._open(validated.path)
        try:
            if source.page_count > self.max_pages:
                raise PageLimitExceededError(f"PDF has {source.page_count} pages; limit is {self.max_pages}.")
            pages: list[DocumentPage] = []
            spans: list[EvidenceSpan] = []
            routes: list[PageRoute] = []
            for pdf_page in source:
                native = self.native.extract_page(pdf_page, validated.sha256)
                if native.useful_characters >= self.min_native_characters:
                    pages.append(native.page)
                    spans.extend(native.evidence)
                    routes.append(PageRoute(pdf_page.number + 1, "native_pdf", "embedded text passed quality threshold", native.useful_characters))
                    continue
                if self.ocr_backend is None:
                    raise OCRBackendUnavailableError(
                        f"Page {pdf_page.number + 1} has only {native.useful_characters} useful native characters and requires OCR."
                    )
                ocr_page, ocr_spans = self._ocr_pdf_page(pdf_page, validated.sha256)
                pages.append(ocr_page.model_copy(update={"width_pt": float(pdf_page.rect.width), "height_pt": float(pdf_page.rect.height)}))
                spans.extend(ocr_spans)
                routes.append(PageRoute(pdf_page.number + 1, ocr_page.extraction_method, "native text was absent or below quality threshold", native.useful_characters))
        finally:
            source.close()
        methods = {page.extraction_method for page in pages}
        extraction_method = methods.pop() if len(methods) == 1 else "mixed"
        full_text = "\n\n".join(page.full_text for page in pages)
        document = Document(
            document_id=validated.sha256,
            source_path=str(validated.path),
            source_type="pdf",
            pages=pages,
            full_text=full_text,
            page_count=len(pages),
            has_embedded_text=any(route.method == "native_pdf" for route in routes),
            extraction_method=extraction_method,
            ingestion_warnings=[
                f"Pages routed to OCR: {', '.join(str(route.page_number) for route in routes if route.method != 'native_pdf')}"
            ] if any(route.method != "native_pdf" for route in routes) else [],
        )
        return document, tuple(spans), tuple(routes)

    def _ocr_pdf_page(self, pdf_page: pymupdf.Page, document_id: str) -> tuple[DocumentPage, tuple[EvidenceSpan, ...]]:
        extractor = getattr(self.ocr_backend, "extract_page", None)
        if extractor is None:
            raise OCRBackendUnavailableError("Configured OCR backend cannot process individual rendered PDF pages.")
        # Rendered uploads must not remain in a shared, persistent cache.
        with tempfile.TemporaryDirectory(prefix="indicnotice-ocr-") as directory:
            image_path = Path(directory) / "page.png"
            scale = self.render_dpi / 72.0
            pdf_page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).save(str(image_path))
            return extractor(image_path, document_id, pdf_page.number + 1)

    def _apply_language_labels(self, document: Document, evidence: tuple[EvidenceSpan, ...]) -> tuple[Document, tuple[EvidenceSpan, ...]]:
        pages: list[DocumentPage] = []
        block_languages: dict[str, str] = {}
        for page in document.pages:
            blocks: list[DocumentBlock] = []
            for block in page.blocks:
                language, _ = self.language_detector.detect_primary(block.text)
                block_languages[block.block_id] = language
                blocks.append(block.model_copy(update={"language_hint": language}))
            pages.append(page.model_copy(update={"blocks": blocks}))
        language, confidence = self.language_detector.detect_primary(document.full_text)
        labelled_document = document.model_copy(update={"pages": pages, "detected_language": language, "language_confidence": confidence})
        labelled_evidence = tuple(
            span.model_copy(update={"language": block_languages.get(span.block_id or "", self.language_detector.detect_primary(span.text)[0])})
            for span in evidence
        )
        return labelled_document, labelled_evidence

    @staticmethod
    def _evidence_from_document(document: Document) -> tuple[EvidenceSpan, ...]:
        evidence: list[EvidenceSpan] = []
        for page in document.pages:
            cursor = 0
            for block in page.blocks:
                start = page.full_text.find(block.text, cursor)
                if start < 0:
                    start = cursor
                end = start + len(block.text)
                cursor = end
                evidence.append(EvidenceSpan(
                    evidence_id=f"ev:{block.block_id}",
                    document_id=document.document_id,
                    page_number=page.page_number,
                    text=block.text,
                    original_ocr_text=block.original_ocr_text,
                    bbox=block.bbox,
                    block_id=block.block_id,
                    char_start=start,
                    char_end=end,
                    extraction_method=page.extraction_method,
                    confidence=block.confidence,
                ))
        return tuple(evidence)
