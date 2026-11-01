"""Grounding, schema and runtime diagnostics for NLP-3."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from indicnotice.schemas.eligibility import Condition, ConditionGroup
from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.extraction.contextual.types import ExtractionDiagnostics


_WS = re.compile(r"\s+")


def _normal(value: str) -> str:
    return _WS.sub(" ", value).strip().casefold()


@dataclass(frozen=True, slots=True)
class GroundingMetrics:
    referenced_evidence: int
    valid_evidence_references: int
    evidence_reference_validity: float
    support_checked_claims: int
    supported_claims: int
    evidence_support_rate: float
    hallucination_count: int
    schema_valid: bool
    repair_count: int
    failed_attempt_count: int
    latency_seconds: float
    prompt_tokens: int | None
    completion_tokens: int | None
    evidence_realignments: int


def _condition_claims(group: ConditionGroup | None) -> Iterable[tuple[str, list[str]]]:
    if group is None:
        return
    for child in group.children:
        if isinstance(child, Condition):
            if child.source_text:
                yield child.source_text, child.evidence_ids
            yield from _condition_claims(child.applies_when)
        else:
            yield from _condition_claims(child)
    yield from _condition_claims(group.applies_when)


def grounding_metrics(analysis: NoticeAnalysis, diagnostics: ExtractionDiagnostics) -> GroundingMetrics:
    evidence = {item.evidence_id: item for item in analysis.evidence}
    references: list[str] = []
    claims: list[tuple[str, list[str]]] = []
    metadata = analysis.metadata
    for value, ids in (
        (metadata.title, metadata.title_evidence_ids),
        (metadata.issuing_authority, metadata.issuing_authority_evidence_ids),
        (metadata.notice_number, metadata.notice_number_evidence_ids),
    ):
        references.extend(ids)
        if value:
            claims.append((value, ids))
    for item in analysis.dates:
        references.extend(item.evidence_ids)
        if item.source_text:
            claims.append((item.source_text, item.evidence_ids))
    for collection in (analysis.fees, analysis.benefits):
        for item in collection:
            references.extend(item.evidence_ids)
            if item.source_text:
                claims.append((item.source_text, item.evidence_ids))
    for item in analysis.required_documents:
        references.extend(item.evidence_ids)
        claims.append((item.source_name, item.evidence_ids))
    for source_text, ids in _condition_claims(analysis.eligibility):
        references.extend(ids)
        claims.append((source_text, ids))
    for item in analysis.actions:
        references.extend(item.evidence_ids)
        claims.append((item.description, item.evidence_ids))
    for item in analysis.links:
        references.extend(item.evidence_ids)
        claims.append((item.url, item.evidence_ids))

    valid = sum(item in evidence for item in references)
    supported = 0
    for value, ids in claims:
        joined = "\n".join(evidence[item].text for item in ids if item in evidence)
        if ids and _normal(value) in _normal(joined):
            supported += 1
    schema_valid = True
    try:
        NoticeAnalysis.model_validate(analysis.model_dump(mode="json"))
    except ValueError:
        schema_valid = False
    failed_attempts = sum(not (item.schema_valid and item.evidence_valid) for item in diagnostics.attempts)
    return GroundingMetrics(
        referenced_evidence=len(references),
        valid_evidence_references=valid,
        evidence_reference_validity=valid / len(references) if references else 1.0,
        support_checked_claims=len(claims),
        supported_claims=supported,
        evidence_support_rate=supported / len(claims) if claims else 1.0,
        hallucination_count=len(claims) - supported + diagnostics.rejected_claims,
        schema_valid=schema_valid,
        repair_count=diagnostics.repair_count,
        failed_attempt_count=failed_attempts,
        latency_seconds=diagnostics.latency_seconds,
        prompt_tokens=diagnostics.prompt_tokens,
        completion_tokens=diagnostics.completion_tokens,
        evidence_realignments=diagnostics.evidence_realignments,
    )
