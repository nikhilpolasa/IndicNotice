"""Deterministic, evidence-linked explanations for eligibility outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from indicnotice.schemas.eligibility import Condition, ConditionGroup, EvalStatus
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.eligibility.evaluator import CandidateProfile, evaluate_eligibility
from services.nlp.semantic.canonical import iter_conditions


@dataclass(frozen=True, slots=True)
class ConditionExplanation:
    condition_id: str
    requirement: str
    candidate_value: object
    computed_value: object
    status: EvalStatus
    reason: str
    evidence_ids: tuple[str, ...]
    source_pages: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class EligibilityExplanation:
    overall: EvalStatus
    user_facing_summary: str
    conditions: tuple[ConditionExplanation, ...]


_SUMMARY = {
    EvalStatus.PASS: "Appears eligible based on the conditions stated in this notice.",
    EvalStatus.FAIL: "Does not meet the stated condition.",
    EvalStatus.UNKNOWN: "Cannot determine because required information is missing.",
    EvalStatus.NOT_APPLICABLE: "The stated conditions are not applicable to this profile.",
}


def _candidate_value(profile: CandidateProfile, condition: Condition) -> tuple[object, object]:
    supplied = profile.get(condition.attribute)
    if condition.attribute == "age" and condition.reference_date:
        dob = profile.get("date_of_birth")
        try:
            cutoff = date.fromisoformat(condition.reference_date)
            birth = date.fromisoformat(str(dob))
            computed = cutoff.year - birth.year - ((cutoff.month, cutoff.day) < (birth.month, birth.day))
            return dob, computed
        except (TypeError, ValueError):
            return dob, None
    return supplied, supplied


def explain_eligibility(
    candidate_profile: CandidateProfile,
    eligibility_ast: ConditionGroup | None,
    evidence: Mapping[str, EvidenceSpan] | list[EvidenceSpan],
) -> EligibilityExplanation:
    """Evaluate once, then render an auditable explanation without an LLM."""
    evidence_map = evidence if isinstance(evidence, Mapping) else {item.evidence_id: item for item in evidence}
    result = evaluate_eligibility(candidate_profile, eligibility_ast)
    statuses = {item.condition_id: item for item in result.conditions}
    explanations: list[ConditionExplanation] = []
    if eligibility_ast is not None:
        for condition in iter_conditions(eligibility_ast):
            evaluated = statuses.get(condition.condition_id)
            if evaluated is None:
                continue
            supplied, computed = _candidate_value(candidate_profile, condition)
            pages = tuple(sorted({evidence_map[eid].page_number for eid in condition.evidence_ids if eid in evidence_map}))
            requirement = f"{condition.attribute} {condition.comparator.value} {condition.value!r}"
            if condition.reference_date:
                requirement += f" as on {condition.reference_date}"
            explanations.append(ConditionExplanation(
                condition_id=condition.condition_id,
                requirement=requirement,
                candidate_value=supplied,
                computed_value=computed,
                status=evaluated.status,
                reason=evaluated.reason,
                evidence_ids=tuple(condition.evidence_ids),
                source_pages=pages,
            ))
    return EligibilityExplanation(result.overall, _SUMMARY[result.overall], tuple(explanations))
