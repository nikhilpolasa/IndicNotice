from __future__ import annotations

from pathlib import Path
import subprocess

import pymupdf
import pytest
from PIL import Image

from indicnotice.schemas.document import Document, DocumentBlock, DocumentPage
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.ingestion.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    EncryptedPDFError,
    FileSignatureMismatchError,
    OCRBackendUnavailableError,
    OCRLanguageUnavailableError,
    NoReadableTextError,
    PageLimitExceededError,
    UnsupportedDocumentTypeError,
)
from services.nlp.ingestion.native_pdf import NativePDFBackend
from services.nlp.ingestion.router import DocumentIngestor
from services.nlp.ingestion.validation import validate_input
from services.nlp.ocr import TesseractBackend


@pytest.fixture
def work_path() -> Path:
    """Use a pre-existing workspace dir; the managed Windows runner blocks user temp."""
    path = Path("tests/.runtime").resolve()
    for child in path.iterdir():
        if child.name != ".gitkeep" and child.is_file():
            child.unlink()
    return path


def make_pdf(path: Path, texts: list[str]) -> None:
    document = pymupdf.open()
    for text in texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    document.save(path)
    document.close()


class FakeOCR:
    def extract_page(self, image_path: Path, document_id: str, page_number: int = 1):
        text = "తెలుగు ప్రకటన పాఠ్యం"
        block_id = f"{document_id}:p{page_number}:b0"
        block = DocumentBlock(
            block_id=block_id,
            page_number=page_number,
            text=text,
            original_ocr_text=text,
            bbox=[0, 0, 100, 30],
            reading_order=0,
            confidence=0.9,
        )
        page = DocumentPage(page_number=page_number, full_text=text, blocks=[block], extraction_method="tesseract")
        span = EvidenceSpan(
            evidence_id=f"ev:{block_id}", document_id=document_id, page_number=page_number,
            text=text, original_ocr_text=text, bbox=block.bbox, block_id=block_id,
            char_start=0, char_end=len(text), extraction_method="tesseract", confidence=0.9,
        )
        return page, (span,)

    def extract_with_evidence(self, document_path: str):
        identifier = validate_input(document_path).sha256
        page, spans = self.extract_page(Path(document_path), identifier)
        return Document(
            document_id=identifier, source_path=document_path, source_type="image", pages=[page],
            full_text=page.full_text, page_count=1, extraction_method="tesseract",
        ), spans


def test_content_signatures_and_hash(work_path: Path):
    png = work_path / "notice.png"
    Image.new("RGB", (20, 20), "white").save(png)
    validated = validate_input(png)
    assert validated.media_type == "image/png"
    assert len(validated.sha256) == 64


def test_empty_unsupported_and_mismatched_files(work_path: Path):
    empty = work_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(EmptyDocumentError):
        validate_input(empty)
    unsupported = work_path / "notice.txt"
    unsupported.write_text("hello")
    with pytest.raises(UnsupportedDocumentTypeError):
        validate_input(unsupported)
    mismatch = work_path / "image.pdf"
    Image.new("RGB", (10, 10)).save(mismatch, format="PNG")
    with pytest.raises(FileSignatureMismatchError):
        validate_input(mismatch)


def test_corrupt_and_encrypted_pdf_errors(work_path: Path):
    corrupt = work_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-1.7\nnot-a-real-pdf")
    validate_input(corrupt)
    with pytest.raises(CorruptDocumentError):
        NativePDFBackend().extract(str(corrupt))

    encrypted = work_path / "locked.pdf"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "secret")
    document.save(encrypted, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    with pytest.raises(EncryptedPDFError):
        NativePDFBackend().extract(str(encrypted))


def test_native_pdf_preserves_pages_geometry_order_and_evidence(work_path: Path):
    pdf = work_path / "native.pdf"
    make_pdf(pdf, ["Official Hindi Notice 2026 with enough native text", "Second page content is also searchable"])
    document, evidence = NativePDFBackend().extract_with_evidence(str(pdf))
    assert document.page_count == 2
    assert document.has_embedded_text is True
    assert [page.page_number for page in document.pages] == [1, 2]
    assert all(page.width_pt and page.height_pt for page in document.pages)
    assert all(block.reading_order == 0 for page in document.pages for block in page.blocks)
    assert len(evidence) == 2
    assert document.pages[0].full_text[evidence[0].char_start:evidence[0].char_end] == evidence[0].text


def test_single_page_empty_page_and_page_limit(work_path: Path):
    single = work_path / "single.pdf"
    make_pdf(single, ["single page with useful content"])
    assert NativePDFBackend().extract(str(single)).page_count == 1
    empty_page = work_path / "empty-page.pdf"
    make_pdf(empty_page, [""])
    assert NativePDFBackend().extract(str(empty_page)).pages[0].full_text == ""
    two_pages = work_path / "two-pages.pdf"
    make_pdf(two_pages, ["first", "second"])
    with pytest.raises(PageLimitExceededError):
        NativePDFBackend(max_pages=1).extract(str(two_pages))


def test_router_routes_mixed_pdf_by_page(work_path: Path):
    pdf = work_path / "mixed.pdf"
    make_pdf(pdf, ["This page has a sufficient amount of embedded searchable text.", ""])
    result = DocumentIngestor(ocr_backend=FakeOCR(), cache_dir=work_path).ingest(pdf)
    assert [route.method for route in result.routes] == ["native_pdf", "tesseract"]
    assert result.document.extraction_method == "mixed"
    assert result.document.pages[1].page_number == 2
    assert result.document.detected_language == "mixed"
    assert any(span.language == "te" for span in result.evidence)


def test_router_requires_ocr_for_image_and_low_text_pdf(work_path: Path):
    image = work_path / "notice.jpg"
    Image.new("RGB", (40, 20), "white").save(image)
    with pytest.raises(OCRBackendUnavailableError):
        DocumentIngestor().ingest(image)
    pdf = work_path / "blank.pdf"
    make_pdf(pdf, [""])
    with pytest.raises(OCRBackendUnavailableError):
        DocumentIngestor().ingest(pdf)


def test_router_ingests_image_through_backend(work_path: Path):
    image = work_path / "notice.jpeg"
    Image.new("RGB", (40, 20), "white").save(image)
    result = DocumentIngestor(ocr_backend=FakeOCR()).ingest(image)
    assert result.media_type == "image/jpeg"
    assert result.document.detected_language == "te"
    assert result.routes[0].reason == "image inputs require OCR"


def _fake_tesseract(work_path: Path) -> TesseractBackend:
    executable = work_path / "fake-tesseract.exe"
    executable.write_bytes(b"test fixture")
    return TesseractBackend(executable=executable)


def test_tesseract_missing_executable_is_typed(work_path: Path):
    with pytest.raises(OCRBackendUnavailableError):
        TesseractBackend(executable=work_path / "does-not-exist.exe")


def test_tesseract_missing_language_and_empty_output_are_typed(work_path: Path, monkeypatch: pytest.MonkeyPatch):
    image = work_path / "ocr.png"
    Image.new("RGB", (100, 30), "white").save(image)
    backend = _fake_tesseract(work_path)
    monkeypatch.setattr(backend, "available_languages", lambda: {"eng"})
    with pytest.raises(OCRLanguageUnavailableError):
        backend.extract_page(image, "doc")

    monkeypatch.setattr(backend, "available_languages", lambda: {"eng", "hin", "tel"})
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    monkeypatch.setattr(backend, "_run", lambda arguments: subprocess.CompletedProcess(arguments, 0, header, ""))
    with pytest.raises(NoReadableTextError):
        backend.extract_page(image, "doc")


def test_tesseract_preserves_zero_confidence_bbox_and_json_roundtrip(work_path: Path, monkeypatch: pytest.MonkeyPatch):
    image = work_path / "ocr-low.png"
    Image.new("RGB", (100, 30), "white").save(image)
    backend = _fake_tesseract(work_path)
    monkeypatch.setattr(backend, "available_languages", lambda: {"eng", "hin", "tel"})
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t2\t3\t20\t10\t0\tnotice\n"
    )
    monkeypatch.setattr(backend, "_run", lambda arguments: subprocess.CompletedProcess(arguments, 0, tsv, ""))
    page, spans = backend.extract_page(image, "doc")
    assert page.blocks[0].confidence == 0.0
    assert spans[0].bbox == [2.0, 3.0, 22.0, 13.0]
    assert EvidenceSpan.model_validate_json(spans[0].model_dump_json()) == spans[0]
