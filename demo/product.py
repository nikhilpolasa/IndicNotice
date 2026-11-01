"""Session-owned production workflow; research entry points stay independent."""
from __future__ import annotations

from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor, Future
from copy import deepcopy
from hashlib import sha256
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import MutableMapping, Any

from demo.pipeline import DemoAnalysis, _validate_upload, DEFAULT_QWEN_URL, DEFAULT_QWEN_MODEL
from services.nlp.ingestion.router import DocumentIngestor
from services.nlp.ocr.tesseract import TesseractBackend
from services.nlp.ingestion.errors import OCRBackendUnavailableError
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.extraction.contextual import ContextualStructuredExtractor, HTTPChatProvider
from services.nlp.extraction.contextual.errors import ProviderTimeout
from services.nlp.semantic import EvidenceGatedSemanticExtractor
from services.nlp.semantic.canonical import iter_conditions
from indicnotice.schemas.eligibility import Comparator

LOG = logging.getLogger(__name__)
FAST_MODE = "initial-rules"
ADVANCED_MODE = "verified-contextual"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
INITIAL_ANALYSIS_CONFIG = "initial-rules-v1;native-pdf+optional-tesseract-ocr"


def analysis_cache_key(data: bytes) -> str:
    """Bind per-session results to the upload and the fixed initial pipeline config."""
    digest = sha256()
    digest.update(INITIAL_ANALYSIS_CONFIG.encode("utf-8"))
    try:
        ocr = TesseractBackend()
        ocr_config = f"{ocr.executable}|{','.join(ocr.languages)}|psm={ocr.psm}"
    except OCRBackendUnavailableError:
        ocr_config = "ocr-unavailable"
    digest.update(ocr_config.encode("utf-8"))
    digest.update(b"\0")
    digest.update(data)
    return digest.hexdigest()


def initial_analysis(data: bytes, filename: str) -> DemoAnalysis:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Upload exceeds size limit")
    _validate_upload(data, filename)
    try:
        ocr = TesseractBackend()
    except OCRBackendUnavailableError:
        ocr = None
    with tempfile.TemporaryDirectory(prefix="indicnotice-upload-") as directory:
        path = Path(directory) / "notice.pdf"
        path.write_bytes(data)
        ingestion = DocumentIngestor(ocr_backend=ocr).ingest(path)
    baseline = RegexBaselineExtractor().extract_ingestion(ingestion).analysis
    semantic = EvidenceGatedSemanticExtractor().combine(baseline, ingestion.evidence, None)
    return DemoAnalysis(FAST_MODE, ingestion, semantic.analysis, baseline,
                        hybrid_diagnostics=semantic.diagnostics)


def session_analysis(state: MutableMapping[str, Any], data: bytes, filename: str) -> tuple[DemoAnalysis, bool, float]:
    """One bounded cache per caller's session, keyed by content, never by filename."""
    started = time.perf_counter()
    digest = sha256(data).hexdigest()
    cache_key = analysis_cache_key(data)
    if state.get("upload_digest") == digest and state.get("analysis_cache_key") == cache_key and state.get("demo_result") is not None:
        return state["demo_result"], True, time.perf_counter() - started
    clear_notice(state)
    result = initial_analysis(data, filename)
    state["upload_digest"] = digest
    state["analysis_cache_key"] = cache_key
    state["demo_result"] = result
    return result, False, time.perf_counter() - started


def clear_notice(state: MutableMapping[str, Any]) -> None:
    if job := state.get("advanced_job"):
        job.cancel()
    for key in list(state):
        if key in {"upload_digest", "analysis_cache_key", "demo_result", "candidate_profile", "qa_response", "qa_input", "eligibility_response", "advanced_job", "advanced_error"} or key.startswith(("provide-", "value-", "eligibility-widget-")):
            del state[key]


class _BudgetProvider:
    """One total wall-clock budget across every chunk and repair request."""
    def __init__(self, provider: HTTPChatProvider, seconds: float):
        self.provider = provider
        self.deadline = time.monotonic() + seconds

    @property
    def model_id(self):
        return self.provider.model_id

    def complete(self, request):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderTimeout("Advanced analysis budget exhausted")
        messages = tuple(dict(message) for message in request.messages)
        messages = ({**messages[0], "content": messages[0]["content"] +
                    "\nProduction review scope: extract eligibility, required_documents and actions only. "
                    "Dates, fees, benefits, links and metadata are outside this review. "
                    "Return category=null, category_evidence_ids=[], metadata={}, dates=[], fees=[], benefits=[], links=[]. "
                    "Return compact single-line JSON with short verbatim quotations."}, *messages[1:])
        response = self.provider.complete(replace(
            request, messages=messages, response_schema=production_schema(request.response_schema),
            timeout_seconds=min(request.timeout_seconds, remaining),
        ))
        LOG.info("Advanced request completed: seconds=%.3f output_tokens=%s finish=%s",
                 response.latency_seconds, response.completion_tokens, response.finish_reason)
        return response


def production_schema(schema: dict) -> dict:
    """Bound verbose quotations/citation lists without changing research schemas.

    Source units remain complete. The same validators still reject unsupported
    values; these transport limits can leave information unresolved.
    """
    bounded = deepcopy(schema)
    visited = set()
    def visit(node, name=""):
        if not isinstance(node, dict) or id(node) in visited:
            return
        visited.add(id(node))
        if node.get("type") == "string" and "enum" not in node and "const" not in node:
            node["maxLength"] = 320
        for key, value in node.items():
            if key == "properties":
                for field, child in value.items():
                    visit(child, field)
            elif isinstance(value, dict):
                visit(value, name)
            elif isinstance(value, list):
                for child in value:
                    visit(child, name)
    visit(bounded)
    # Initial facts remain visible as initial facts. Advanced review concentrates
    # on the complex requirements that benefit from contextual reasoning.
    for name in ("category_evidence_ids", "dates", "fees", "benefits", "links"):
        bounded["properties"][name] = {**bounded["properties"][name], "maxItems": 0}
    bounded["properties"]["category"] = {"type": "null"}
    bounded["properties"]["metadata"] = {"type": "object", "properties": {}, "additionalProperties": False}
    return bounded


def advanced_analysis(result: DemoAnalysis, *, budget_seconds: float = 120) -> DemoAnalysis:
    provider = HTTPChatProvider(
        base_url=os.environ.get("INDICNOTICE_MODEL_URL", DEFAULT_QWEN_URL),
        model_id=os.environ.get("INDICNOTICE_MODEL_ID", DEFAULT_QWEN_MODEL),
        max_tokens=4096, enable_thinking=False,
    )
    extractor = ContextualStructuredExtractor(
        _BudgetProvider(provider, budget_seconds), max_chunk_chars=5_000,
        timeout_seconds=budget_seconds, max_repair_attempts=0, compact_context=True,
    )
    extractor.extraction_prompt = Path(__file__).with_name("requirements_prompt.txt").read_text(encoding="utf-8")
    contextual = extractor.extract_ingestion(result.ingestion)
    contextual = replace(contextual, diagnostics=replace(
        contextual.diagnostics, prompt_version="indicnotice-production-requirements-v1"))
    hybrid = EvidenceGatedSemanticExtractor().combine(result.baseline_analysis, result.ingestion.evidence, contextual.analysis)
    analysis = hybrid.analysis.model_copy(update={"warnings": [
        *hybrid.analysis.warnings,
        *(warning for warning in contextual.analysis.warnings if warning.code == "unsupported_model_claims_rejected"),
    ]})
    return replace(result, mode=ADVANCED_MODE, analysis=analysis,
                   contextual_diagnostics=contextual.diagnostics, hybrid_diagnostics=hybrid.diagnostics)


def start_advanced(result: DemoAnalysis) -> Future:
    """Keep the initial reader usable during optional contextual processing.

    The caller owns the future; no global result cache or profile is shared.
    """
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notice-review")
    future = executor.submit(advanced_analysis, result)
    future.add_done_callback(lambda _: executor.shutdown(wait=False))
    return future


def eligibility_display_state(status: str, result: DemoAnalysis, profile: dict | None = None) -> str:
    # Not answering a presence question is different from explicitly saying no.
    if profile is not None and any(
        condition.comparator in {Comparator.EXISTS, Comparator.NOT_EXISTS}
        and condition.attribute not in profile
        for condition in iter_conditions(result.analysis.eligibility)
    ):
        return "UNKNOWN"
    # Neither baseline nor contextual extraction has a completeness certificate.
    # Passing every extracted rule therefore cannot establish notice-wide eligibility.
    if status == "PASS":
        return "UNKNOWN"
    return status
