from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

import pymupdf
import pytest

import demo.app
from demo import pipeline
from indicnotice.schemas.eligibility import EvalStatus


ROOT = Path(__file__).resolve().parents[2]


def _notice_pdf() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Admission Notice\nApplications must be submitted by 15 October 2026.\nNo application fee is required.",
    )
    payload = document.tobytes()
    document.close()
    return payload


def test_demo_modules_import_without_streamlit_core_dependency():
    assert callable(demo.app.main)
    assert callable(pipeline.analyze_uploaded_pdf)


def test_upload_adapter_runs_real_pipeline_and_removes_temporary_pdf(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "qwen_health",
        lambda *args, **kwargs: pipeline.QwenHealth(False, "Qwen server unavailable — deterministic mode remains available."),
    )
    result = pipeline.analyze_uploaded_pdf(_notice_pdf(), "notice.pdf", pipeline.NLP4_MODE)
    assert result.analysis.document_id == result.ingestion.document.document_id
    assert result.analysis.extractor_model == "evidence-gated-semantic-nlp4-v1"
    assert not Path(result.ingestion.document.source_path).exists()
    assert any("no contextual Qwen candidates" in message for message in result.notices)


@pytest.mark.parametrize("status", list(EvalStatus))
def test_eligibility_display_preserves_all_four_states(status):
    assert pipeline.eligibility_state_label(status) == status.value


def test_offline_qwen_health_is_clean(monkeypatch):
    def unavailable(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr(pipeline, "urlopen", unavailable)
    result = pipeline.qwen_health(timeout_seconds=0.01)
    assert result.available is False
    assert "deterministic mode remains available" in result.message


def test_demo_has_no_fixture_or_gold_dependency():
    forbidden = (
        "datasets/fixtures",
        "datasets/annotations",
        "SCERT",
        "KVS",
        "hi-q",
        "te-q",
    )
    offenders = []
    for path in (ROOT / "demo").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_invalid_upload_is_rejected_before_ingestion():
    with pytest.raises(ValueError, match="Only PDF"):
        pipeline.analyze_uploaded_pdf(b"not a pdf", "notice.txt", pipeline.NLP2_MODE)
