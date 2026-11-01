from __future__ import annotations

from pathlib import Path

import pytest

from services.nlp.evaluation import character_error_rate, word_error_rate
from services.nlp.ingestion import DocumentIngestor
from services.nlp.ingestion.errors import OCRBackendUnavailableError
from services.nlp.ocr import TesseractBackend


FIXTURES = Path("datasets/fixtures/nlp1")


@pytest.mark.integration
def test_real_hindi_digital_notice_uses_native_pdf():
    path = FIXTURES / "hindi/nfc_recruitment_01_2026_hindi.pdf"
    result = DocumentIngestor().ingest(path)
    assert result.document.page_count == 20
    assert result.document.extraction_method == "native_pdf"
    assert result.document.detected_language == "hi"
    assert len(result.document.full_text) > 40_000
    assert len(result.evidence) > 300
    assert all(route.method == "native_pdf" for route in result.routes)
    assert all(span.bbox is not None and span.document_id == result.document.document_id for span in result.evidence)


@pytest.mark.integration
def test_real_telugu_scanned_notice_runs_tesseract_and_retains_evidence():
    path = FIXTURES / "telugu/ananthapuramu_anganwadi_recruitment_2025.pdf"
    try:
        backend = TesseractBackend()
    except OCRBackendUnavailableError as exc:
        pytest.skip(str(exc))
    result = DocumentIngestor(
        ocr_backend=backend,
        render_dpi=250,
        cache_dir=".cache/nlp1-integration",
    ).ingest(path)
    assert result.document.page_count == 10
    assert result.document.extraction_method == "tesseract"
    assert result.document.has_embedded_text is False
    assert len(result.document.full_text) > 10_000
    assert all(route.method == "tesseract" and route.native_useful_characters == 0 for route in result.routes)
    assert all(span.original_ocr_text is not None for span in result.evidence)
    assert all(span.bbox is not None for span in result.evidence)
    assert any(span.confidence is not None for span in result.evidence)
    assert {span.language for span in result.evidence} & {"te", "mixed"}

    reference = (FIXTURES / "ground_truth/telugu_page1_title.txt").read_text(encoding="utf-8").strip()
    prediction = next(block.text for block in result.document.pages[0].blocks if "ప్రభుత్వం" in block.text)
    assert character_error_rate(reference, prediction) <= 0.25
    assert 0.0 <= word_error_rate(reference, prediction) <= 1.0
