"""Deterministic resolution of bounded age relaxations and exemptions."""

from __future__ import annotations

from dataclasses import dataclass

from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup


@dataclass(frozen=True, slots=True)
class DeltaRelaxation:
    categories: tuple[str, ...]
    delta_years: float
    source_text: str
    evidence_ids: tuple[str, ...]


def _category_guard(
    categories: tuple[str, ...],
    comparator: Comparator,
    evidence_ids: tuple[str, ...],
    suffix: str,
) -> ConditionGroup:
    return ConditionGroup(
        group_id=f"guard_{suffix}",
        operator="AND",
        children=[
            Condition(
                condition_id=f"guard_{suffix}_category",
                attribute="category",
                comparator=comparator,
                value=list(categories),
                source_text="/".join(categories),
                evidence_ids=list(evidence_ids),
            )
        ],
        evidence_ids=list(evidence_ids),
    )


def resolve_age_delta(
    base: Condition | None,
    relaxation: DeltaRelaxation,
) -> tuple[ConditionGroup | None, str | None]:
    """Resolve base maximum + delta without creating ``base AND relaxed``."""
    if (
        base is None
        or base.attribute != "age"
        or base.comparator not in {Comparator.LT, Comparator.LTE}
        or not isinstance(base.value, (int, float))
    ):
        return None, "Age-relaxation delta retained unresolved because no supported base maximum exists."
    combined_evidence = list(dict.fromkeys(base.evidence_ids + list(relaxation.evidence_ids)))
    general = base.model_copy(
        update={
            "condition_id": f"{base.condition_id}_general",
            "applies_when": _category_guard(
                relaxation.categories,
                Comparator.NOT_IN,
                relaxation.evidence_ids,
                f"{base.condition_id}_general",
            ),
        }
    )
    relaxed = base.model_copy(
        update={
            "condition_id": f"{base.condition_id}_relaxed",
            "value": float(base.value) + relaxation.delta_years,
            "scope": "/".join(relaxation.categories),
            "source_text": f"{base.source_text or ''}\n{relaxation.source_text}".strip(),
            "evidence_ids": combined_evidence,
            "applies_when": _category_guard(
                relaxation.categories,
                Comparator.IN,
                relaxation.evidence_ids,
                f"{base.condition_id}_relaxed",
            ),
        }
    )
    return (
        ConditionGroup(
            group_id=f"{base.condition_id}_age_policy",
            operator="OR",
            label="Mutually exclusive general and relaxed age limits",
            children=[general, relaxed],
            evidence_ids=combined_evidence,
        ),
        None,
    )


def apply_age_exemption(
    base: Condition,
    *,
    attribute: str,
    exempt_value: object,
    evidence_ids: list[str],
) -> ConditionGroup:
    """Make the base requirement inapplicable for an explicitly exempt group."""
    guard = ConditionGroup(
        group_id=f"guard_{base.condition_id}_not_exempt",
        operator="AND",
        children=[
            Condition(
                condition_id=f"guard_{base.condition_id}_not_exempt_value",
                attribute=attribute,
                comparator=Comparator.NEQ,
                value=exempt_value,
                evidence_ids=evidence_ids,
            )
        ],
        evidence_ids=evidence_ids,
    )
    guarded = base.model_copy(
        update={
            "condition_id": f"{base.condition_id}_unless_exempt",
            "applies_when": guard,
            "evidence_ids": list(dict.fromkeys(base.evidence_ids + evidence_ids)),
        }
    )
    return ConditionGroup(
        group_id=f"{base.condition_id}_exemption_policy",
        operator="AND",
        label="Base condition with explicit exemption",
        children=[guarded],
        evidence_ids=guarded.evidence_ids,
    )
