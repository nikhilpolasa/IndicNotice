from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.nlp.extraction.contextual import ContextualStructuredExtractor, HTTPChatProvider
from services.nlp.ingestion.router import DocumentIngestor


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("INDICNOTICE_RUN_NLP3_REAL") != "1",
    reason="requires an explicitly configured real local model endpoint",
)
@pytest.mark.parametrize(
    "path,language",
    [
        ("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf", "hi"),
        ("datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf", "mixed"),
    ],
)
def test_real_qwen_contextual_extraction(path: str, language: str):
    ingestion = DocumentIngestor().ingest(Path(path))
    provider = HTTPChatProvider(
        base_url=os.getenv("INDICNOTICE_NLP3_BASE_URL", "http://127.0.0.1:18089"),
        model_id=os.getenv("INDICNOTICE_NLP3_MODEL_ID", "Qwen3-4B-Q4_K_M"),
        max_tokens=4096,
    )
    result = ContextualStructuredExtractor(provider, timeout_seconds=600).extract_ingestion(ingestion)
    assert result.analysis.document_id == ingestion.document.document_id
    assert result.analysis.source_language == language
    assert result.analysis.extractor_model == provider.model_id
    assert result.diagnostics.attempts
