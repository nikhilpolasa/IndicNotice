"""UI-independent adapter from an uploaded PDF to existing NLP services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import json
from pathlib import Path
import tempfile
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup, EvalStatus
from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.eligibility.explanations import EligibilityExplanation, explain_eligibility
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.extraction.contextual import ContextualStructuredExtractor, HTTPChatProvider
from services.nlp.ingestion.router import DocumentIngestor
from services.nlp.ingestion.types import IngestionResult
from services.nlp.semantic import EvidenceGatedSemanticExtractor
from services.nlp.semantic.canonical import iter_conditions


NLP2_MODE = "NLP-2 — Deterministic"
NLP4_MODE = "NLP-4 — Hybrid"
NLP3_MODE = "NLP-3 — Contextual Qwen"
ANALYSIS_MODES = (NLP2_MODE, NLP4_MODE, NLP3_MODE)
DEFAULT_QWEN_URL = "http://127.0.0.1:8080"
DEFAULT_QWEN_MODEL = "Qwen3-4B-Q4_K_M"


@dataclass(frozen=True, slots=True)
class QwenHealth:
    available: bool
    message: str


@dataclass(frozen=True, slots=True)
class DemoAnalysis:
    mode: str
    ingestion: IngestionResult
    analysis: NoticeAnalysis
    baseline_analysis: NoticeAnalysis
    contextual_diagnostics: object | None = None
    hybrid_diagnostics: object | None = None
    notices: tuple[str, ...] = ()


def qwen_health(base_url: str = DEFAULT_QWEN_URL, *, timeout_seconds: float = 1.0) -> QwenHealth:
    """Return a clean availability result; never leak a connection exception."""
    request = Request(f"{base_url.rstrip('/')}/v1/models", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if not 200 <= response.status < 300:
                return QwenHealth(False, f"Qwen server returned HTTP {response.status}.")
            json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return QwenHealth(False, f"Qwen server unavailable — deterministic mode remains available. ({type(exc).__name__})")
    return QwenHealth(True, "Qwen server available.")


def _validate_upload(data: bytes, filename: str) -> None:
    if Path(filename).suffix.casefold() != ".pdf":
        raise ValueError("Only PDF uploads are accepted.")
    if not data.startswith(b"%PDF-"):
        raise ValueError("The uploaded file does not have a valid PDF signature.")


def analyze_uploaded_pdf(
    data: bytes,
    filename: str,
    mode: str,
    *,
    qwen_base_url: str = DEFAULT_QWEN_URL,
    qwen_model: str = DEFAULT_QWEN_MODEL,
    health_timeout_seconds: float = 1.0,
) -> DemoAnalysis:
    """Analyze upload bytes with the repository pipeline and delete the temp PDF."""
    if mode not in ANALYSIS_MODES:
        raise ValueError(f"Unsupported analysis mode: {mode}")
    _validate_upload(data, filename)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="indicnotice-demo-", suffix=".pdf", delete=False) as handle:
            handle.write(data)
            temporary_path = Path(handle.name)
        ingestion = DocumentIngestor().ingest(temporary_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    baseline = RegexBaselineExtractor().extract_ingestion(ingestion).analysis
    if mode == NLP2_MODE:
        return DemoAnalysis(mode, ingestion, baseline, baseline)

    health = qwen_health(qwen_base_url, timeout_seconds=health_timeout_seconds)
    if mode == NLP3_MODE and not health.available:
        raise RuntimeError(health.message)

    contextual = None
    contextual_diagnostics = None
    notices: list[str] = []
    if health.available:
        provider = HTTPChatProvider(base_url=qwen_base_url, model_id=qwen_model)
        contextual_result = ContextualStructuredExtractor(provider).extract_ingestion(ingestion)
        contextual = contextual_result.analysis
        contextual_diagnostics = contextual_result.diagnostics
    else:
        notices.append(health.message)

    if mode == NLP3_MODE:
        assert contextual is not None
        return DemoAnalysis(mode, ingestion, contextual, baseline, contextual_diagnostics=contextual_diagnostics)

    hybrid = EvidenceGatedSemanticExtractor().combine(baseline, ingestion.evidence, contextual)
    if contextual is None:
        notices.append("Hybrid ran with deterministic NLP-2 plus semantic rules; no contextual Qwen candidates were supplied.")
    return DemoAnalysis(
        mode,
        ingestion,
        hybrid.analysis,
        baseline,
        contextual_diagnostics=contextual_diagnostics,
        hybrid_diagnostics=hybrid.diagnostics,
        notices=tuple(notices),
    )


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return to_jsonable(value.model_dump(mode="json"))
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def render_ast_text(group: ConditionGroup | None, *, depth: int = 0) -> str:
    if group is None:
        return "NOT_STATED"
    indent = "  " * depth
    lines = [f"{indent}{group.operator}" + (f" — {group.label}" if group.label else "")]
    if group.applies_when is not None:
        lines.append(f"{indent}  APPLIES WHEN:")
        lines.append(render_ast_text(group.applies_when, depth=depth + 2))
    for child in group.children:
        if isinstance(child, ConditionGroup):
            lines.append(render_ast_text(child, depth=depth + 1))
            continue
        value = "" if child.value is None else f" {child.value!r}"
        reference = f" as on {child.reference_date}" if child.reference_date else ""
        negation = "NOT " if child.negated else ""
        lines.append(f"{indent}  - {negation}{child.attribute} {child.comparator.value}{value}{reference}")
        if child.applies_when is not None:
            lines.append(f"{indent}    APPLIES WHEN:")
            lines.append(render_ast_text(child.applies_when, depth=depth + 3))
    return "\n".join(lines)


def required_profile_attributes(group: ConditionGroup | None) -> list[str]:
    if group is None:
        return []
    values = {
        "date_of_birth" if item.attribute == "age" and item.reference_date else item.attribute
        for item in iter_conditions(group)
    }
    return sorted(values)


def profile_field_specs(group: ConditionGroup | None) -> dict[str, dict[str, Any]]:
    """Derive stable generic widget hints and provenance from the eligibility AST."""
    specs: dict[str, dict[str, Any]] = {}
    if group is None:
        return specs
    for condition in iter_conditions(group):
        attribute = "date_of_birth" if condition.attribute == "age" and condition.reference_date else condition.attribute
        spec = specs.setdefault(attribute, {
            "kind": "text", "options": [], "required": True,
            "source_texts": [], "evidence_ids": [],
        })
        if condition.source_text and condition.source_text not in spec["source_texts"]:
            spec["source_texts"].append(condition.source_text)
        spec["evidence_ids"].extend(
            evidence_id for evidence_id in condition.evidence_ids
            if evidence_id not in spec["evidence_ids"]
        )
        values = condition.value if isinstance(condition.value, (list, tuple, set)) else [condition.value]
        concrete = [value for value in values if value is not None]
        if condition.comparator in {Comparator.EXISTS, Comparator.NOT_EXISTS}:
            if spec["kind"] == "text":
                spec["kind"] = "presence"
        elif attribute == "date_of_birth" or any(isinstance(value, str) and len(value) == 10 and value[4:5] == "-" for value in concrete):
            spec["kind"] = "date"
        elif concrete and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in concrete):
            spec["kind"] = "number"
        elif concrete and all(isinstance(value, str) for value in concrete):
            spec["options"] = list(dict.fromkeys([*spec["options"], *map(str, concrete)]))
            spec["kind"] = "select" if spec["options"] else "text"
    # The user-facing form order is independent of source traversal or hash order.
    return {attribute: specs[attribute] for attribute in sorted(specs)}


def eligibility_outcome(profile: dict[str, Any], analysis: NoticeAnalysis) -> tuple[str, EligibilityExplanation]:
    result = evaluate_eligibility(profile, analysis.eligibility)
    explanation = explain_eligibility(profile, analysis.eligibility, analysis.evidence)
    return eligibility_state_label(result.overall), explanation


def eligibility_state_label(status: EvalStatus | str) -> str:
    value = status.value if isinstance(status, EvalStatus) else str(status)
    allowed = {item.value for item in EvalStatus}
    if value not in allowed:
        raise ValueError(f"Unknown eligibility state: {value}")
    return value


def evidence_for(ids: Iterable[str], analysis: NoticeAnalysis) -> list[dict[str, Any]]:
    evidence = {item.evidence_id: item for item in analysis.evidence}
    return [
        evidence[evidence_id].model_dump(mode="json")
        for evidence_id in dict.fromkeys(ids)
        if evidence_id in evidence
    ]
