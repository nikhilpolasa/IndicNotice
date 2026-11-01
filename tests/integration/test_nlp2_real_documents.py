from __future__ import annotations

from pathlib import Path

import pytest

from indicnotice.schemas import NoticeCategory
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.ingestion.router import DocumentIngestor


@pytest.mark.integration
def test_real_hindi_scholarship_notice_extracts_without_false_fee_amounts():
    path = Path("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf")
    ingestion = DocumentIngestor().ingest(path)
    result = RegexBaselineExtractor().extract_ingestion(ingestion)
    analysis = result.analysis
    assert analysis.source_language == "hi"
    assert analysis.category == NoticeCategory.SCHOLARSHIP
    assert [(item.amount_inr, item.source_text) for item in analysis.fees] == [(0.0, "कोई शुल्क नहीं")]
    assert all(item.amount_inr not in {350000.0} for item in analysis.fees)
    assert any(item.attribute == "marks_percentage" for item in analysis.eligibility.children)
    assert not [warning for warning in analysis.warnings if warning.severity == "error"]
    assert result.traces
