"""Native PDF text and layout extraction backed by PyMuPDF."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pymupdf

from indicnotice.schemas.document import Document, DocumentBlock, DocumentPage
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.ingestion.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    EncryptedPDFError,
    PageLimitExceededError,
)
from services.nlp.ingestion.normalization import normalize_extracted_text


@dataclass(frozen=True, slots=True)
class NativePage:
    page: DocumentPage
    evidence: tuple[EvidenceSpan, ...]
    useful_characters: int


def useful_character_count(text: str) -> int:
    return sum(char.isalpha() or char.isdigit() for char in text)


class NativePDFBackend:
    def __init__(self, *, max_pages: int = 250):
        self.max_pages = max_pages

    @staticmethod
    def _open(path: str | Path) -> pymupdf.Document:
        try:
            document = pymupdf.open(str(path))
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise CorruptDocumentError("PDF cannot be parsed.") from exc
        if document.needs_pass:
            document.close()
            raise EncryptedPDFError("Password-protected PDFs are not accepted.")
        if document.page_count == 0:
            document.close()
            raise EmptyDocumentError("PDF contains no pages.")
        return document

    def extract_page(self, page: pymupdf.Page, document_id: str) -> NativePage:
        blocks: list[DocumentBlock] = []
        evidence: list[EvidenceSpan] = []
        page_parts: list[str] = []
        cursor = 0
        raw_blocks = sorted(page.get_text("blocks"), key=lambda item: (round(item[1], 2), round(item[0], 2)))
        for raw in raw_blocks:
            if len(raw) < 7 or int(raw[6]) != 0:
                continue
            text = normalize_extracted_text(str(raw[4]))
            if not text:
                continue
            if page_parts:
                cursor += 1
            start = cursor
            cursor += len(text)
            block_id = f"{document_id}:p{page.number + 1}:b{len(blocks)}"
            bbox = [float(value) for value in raw[:4]]
            block = DocumentBlock(
                block_id=block_id,
                page_number=page.number + 1,
                text=text,
                bbox=bbox,
                block_type="text",
                reading_order=len(blocks),
            )
            blocks.append(block)
            page_parts.append(text)
            evidence.append(
                EvidenceSpan(
                    evidence_id=f"ev:{block_id}",
                    document_id=document_id,
                    page_number=page.number + 1,
                    text=text,
                    bbox=bbox,
                    block_id=block_id,
                    char_start=start,
                    char_end=cursor,
                    extraction_method="native_pdf",
                )
            )
        full_text = "\n".join(page_parts)
        result = DocumentPage(
            page_number=page.number + 1,
            full_text=full_text,
            blocks=blocks,
            width_pt=float(page.rect.width),
            height_pt=float(page.rect.height),
            extraction_method="native_pdf",
        )
        return NativePage(result, tuple(evidence), useful_character_count(full_text))

    def extract_with_evidence(self, document_path: str) -> tuple[Document, tuple[EvidenceSpan, ...]]:
        path = Path(document_path).resolve()
        document_id = sha256(path.read_bytes()).hexdigest()
        source = self._open(path)
        try:
            if source.page_count > self.max_pages:
                raise PageLimitExceededError(f"PDF has {source.page_count} pages; limit is {self.max_pages}.")
            extracted = [self.extract_page(page, document_id) for page in source]
        finally:
            source.close()
        pages = [item.page for item in extracted]
        full_text = "\n\n".join(page.full_text for page in pages)
        return (
            Document(
                document_id=document_id,
                source_path=str(path),
                source_type="pdf",
                pages=pages,
                full_text=full_text,
                page_count=len(pages),
                has_embedded_text=any(item.useful_characters for item in extracted),
                extraction_method="native_pdf",
            ),
            tuple(span for item in extracted for span in item.evidence),
        )

    def extract(self, document_path: str) -> Document:
        return self.extract_with_evidence(document_path)[0]
