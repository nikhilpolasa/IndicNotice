"""
Deterministic eligibility evaluator for IndicNotice.

=============================================================================
DESIGN PRINCIPLE
=============================================================================

NLP/LLM extracts the eligibility rules into a ConditionGroup AST.
This module evaluates that AST deterministically against a candidate profile.

NO generative model is called here.  The result is fully reproducible.

=============================================================================
EVALUATION SEMANTICS
=============================================================================

Atomic Condition evaluation:
  - PASS  : condition is satisfied by the candidate's profile value
  - FAIL  : condition is not satisfied
  - UNKNOWN: the candidate profile does not contain the required attribute

AND group:
  - PASS  if ALL children are PASS
  - FAIL  if ANY child is FAIL
  - UNKNOWN otherwise (at least one UNKNOWN, none FAIL)

OR group:
  - PASS  if ANY child is PASS
  - FAIL  if ALL children are FAIL
  - UNKNOWN otherwise (at least one UNKNOWN, none PASS)

NEGATION (negated=True on a Condition):
  - PASS ↔ FAIL (swapped)
  - UNKNOWN stays UNKNOWN

=============================================================================
CANDIDATE PROFILE
=============================================================================

A simple dict[str, Any] where keys are normalized attribute names, e.g.:
  {
    "age": 22,
    "marks_percentage": 82.0,
    "annual_family_income_inr": 180000,
    "category": "SC",
    "education_level": "B.Tech",
  }

Missing keys produce UNKNOWN results.

=============================================================================
DISCLAIMER
=============================================================================

The PASS/FAIL/UNKNOWN result is a mechanical rule-match output.
It is NOT a legal or governmental eligibility determination.
The user-facing layer must add appropriate disclaimers.
"""

from __future__ import annotations

import logging
from typing import Any

from indicnotice.schemas.eligibility import (
    Comparator,
    Condition,
    ConditionGroup,
    ConditionNode,
    ConditionResult,
    EligibilityResult,
    EvalStatus,
)

logger = logging.getLogger(__name__)

CandidateProfile = dict[str, Any]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

from datetime import date
import re

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_if_date(v: Any) -> date | None:
    if isinstance(v, str) and _ISO_DATE_PATTERN.match(v):
        try:
            return date.fromisoformat(v)
        except ValueError:
            return None
    elif isinstance(v, date):
        return v
    return None


def _norm_str(v: Any) -> str:
    return str(v).strip().lower()


def _compare(
    profile_value: Any,
    comparator: Comparator,
    threshold: Any,
) -> bool:
    """
    Apply a comparator to profile_value vs threshold.
    Supports numbers, ISO dates, collections, and strings.
    """
    if comparator == Comparator.EXISTS:
        return profile_value is not None
    if comparator == Comparator.NOT_EXISTS:
        return profile_value is None

    # Date comparison
    profile_looks_like_date = isinstance(profile_value, str) and bool(_ISO_DATE_PATTERN.match(profile_value))
    threshold_looks_like_date = isinstance(threshold, str) and bool(_ISO_DATE_PATTERN.match(threshold))
    p_date = _parse_if_date(profile_value)
    t_date = _parse_if_date(threshold)
    if (profile_looks_like_date and p_date is None) or (threshold_looks_like_date and t_date is None):
        raise ValueError("invalid ISO calendar date")
    if p_date is not None and t_date is not None:
        match comparator:
            case Comparator.GT: return p_date > t_date
            case Comparator.GTE: return p_date >= t_date
            case Comparator.LT: return p_date < t_date
            case Comparator.LTE: return p_date <= t_date
            case Comparator.EQ: return p_date == t_date
            case Comparator.NEQ: return p_date != t_date

    # Range / BETWEEN
    if comparator == Comparator.BETWEEN:
        if not isinstance(threshold, (list, tuple)) or len(threshold) != 2:
            raise ValueError(f"BETWEEN comparator requires 2-element threshold, got {threshold!r}")
        lo, hi = threshold[0], threshold[1]
        p_d = _parse_if_date(profile_value)
        lo_d = _parse_if_date(lo)
        hi_d = _parse_if_date(hi)
        if p_d and lo_d and hi_d:
            return lo_d <= p_d <= hi_d
        return float(lo) <= float(profile_value) <= float(hi)

    # Numeric comparison
    try:
        if comparator in (Comparator.GT, Comparator.GTE, Comparator.LT, Comparator.LTE):
            p_num = float(profile_value)
            t_num = float(threshold)
            match comparator:
                case Comparator.GT: return p_num > t_num
                case Comparator.GTE: return p_num >= t_num
                case Comparator.LT: return p_num < t_num
                case Comparator.LTE: return p_num <= t_num
    except (ValueError, TypeError):
        pass

    # Equality / Inequality (supports collections and case-insensitivity)
    if comparator == Comparator.EQ:
        if isinstance(profile_value, (list, tuple, set)):
            return any(_norm_str(x) == _norm_str(threshold) for x in profile_value)
        if isinstance(profile_value, str) and isinstance(threshold, str):
            return _norm_str(profile_value) == _norm_str(threshold)
        return profile_value == threshold

    if comparator == Comparator.NEQ:
        if isinstance(profile_value, (list, tuple, set)):
            return all(_norm_str(x) != _norm_str(threshold) for x in profile_value)
        if isinstance(profile_value, str) and isinstance(threshold, str):
            return _norm_str(profile_value) != _norm_str(threshold)
        return profile_value != threshold

    # Membership: IN / NOT_IN
    if comparator == Comparator.IN:
        if isinstance(threshold, (list, tuple, set)):
            norm_thresh = [_norm_str(x) for x in threshold]
            if isinstance(profile_value, (list, tuple, set)):
                return any(_norm_str(p) in norm_thresh for p in profile_value)
            return _norm_str(profile_value) in norm_thresh
        return profile_value in threshold

    if comparator == Comparator.NOT_IN:
        if isinstance(threshold, (list, tuple, set)):
            norm_thresh = [_norm_str(x) for x in threshold]
            if isinstance(profile_value, (list, tuple, set)):
                return not any(_norm_str(p) in norm_thresh for p in profile_value)
            return _norm_str(profile_value) not in norm_thresh
        return profile_value not in threshold

    raise ValueError(f"Unsupported comparator: {comparator}")


def _eval_condition(
    condition: Condition,
    profile: CandidateProfile,
    results: list[ConditionResult],
    _depth: int = 0,
    _max_depth: int = 20,
) -> EvalStatus:
    """Evaluate a single atomic Condition and append a ConditionResult."""
    if _depth > _max_depth:
        logger.warning("Max recursion depth (%d) exceeded in condition evaluation.", _max_depth)
        status = EvalStatus.UNKNOWN
        results.append(ConditionResult(
            condition_id=condition.condition_id,
            status=status,
            reason=f"Evaluation aborted: maximum recursion depth ({_max_depth}) exceeded.",
        ))
        return status

    # Guard check: applies_when
    if condition.applies_when is not None:
        guard_results: list[ConditionResult] = []
        guard_status = _eval_group(
            condition.applies_when,
            profile,
            guard_results,
            _depth=_depth + 1,
            _max_depth=_max_depth,
        )
        if guard_status in (EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE):
            status = EvalStatus.NOT_APPLICABLE
            reason = (
                f"Condition '{condition.condition_id}' does not apply "
                f"(guard applies_when not satisfied)"
            )
            results.append(ConditionResult(
                condition_id=condition.condition_id,
                status=status,
                reason=reason,
            ))
            return status
        elif guard_status == EvalStatus.UNKNOWN:
            status = EvalStatus.UNKNOWN
            reason = (
                f"Cannot determine if condition '{condition.condition_id}' applies "
                f"(guard applies_when is UNKNOWN)"
            )
            results.append(ConditionResult(
                condition_id=condition.condition_id,
                status=status,
                reason=reason,
            ))
            return status

    attr = condition.attribute
    profile_value = None

    # Handle EXISTS / NOT_EXISTS
    if condition.comparator in (Comparator.EXISTS, Comparator.NOT_EXISTS):
        profile_value = profile.get(attr)
    elif attr == "age" and condition.reference_date:
        # A cutoff-date age must be derived from date_of_birth. A supplied
        # current-age value is not equivalent and must not override it.
        try:
            ref_d = date.fromisoformat(condition.reference_date)
            dob_d = date.fromisoformat(profile["date_of_birth"])
            if dob_d > ref_d:
                raise ValueError("date_of_birth is after reference_date")
            profile_value = ref_d.year - dob_d.year - (
                (ref_d.month, ref_d.day) < (dob_d.month, dob_d.day)
            )
        except (KeyError, ValueError, TypeError):
            profile_value = None
    elif attr in profile:
        profile_value = profile[attr]

    if profile_value is None and condition.comparator not in (Comparator.EXISTS, Comparator.NOT_EXISTS):
        status = EvalStatus.UNKNOWN
        reason = (
            f"Attribute '{attr}' not in candidate profile; "
            f"cannot evaluate {condition.comparator.value} {condition.value!r}"
        )
        results.append(ConditionResult(
            condition_id=condition.condition_id,
            status=status,
            reason=reason,
        ))
        return status

    try:
        passed = _compare(profile_value, condition.comparator, condition.value)
    except (TypeError, ValueError, IndexError) as exc:
        logger.warning(
            "Type mismatch evaluating condition %s (%s %s %r) with profile value %r: %s",
            condition.condition_id,
            attr,
            condition.comparator.value,
            condition.value,
            profile_value,
            exc,
        )
        status = EvalStatus.UNKNOWN
        reason = (
            f"Type error comparing '{attr}' ({profile_value!r}) "
            f"{condition.comparator.value} {condition.value!r}: {exc}"
        )
        results.append(ConditionResult(
            condition_id=condition.condition_id,
            status=status,
            reason=reason,
        ))
        return status

    if condition.negated:
        passed = not passed

    status = EvalStatus.PASS if passed else EvalStatus.FAIL
    unit_str = f" {condition.unit}" if condition.unit else ""
    scope_str = f" [{condition.scope}]" if condition.scope else ""
    reason = (
        f"'{attr}' {condition.comparator.value} {condition.value!r}{unit_str}: "
        f"candidate has {profile_value!r} → "
        f"{'PASS' if status == EvalStatus.PASS else 'FAIL'}{scope_str}"
    )
    if condition.negated:
        reason += " (negated)"

    results.append(ConditionResult(
        condition_id=condition.condition_id,
        status=status,
        reason=reason,
    ))
    return status


def _eval_group(
    group: ConditionGroup,
    profile: CandidateProfile,
    results: list[ConditionResult],
    _depth: int = 0,
    _max_depth: int = 20,
) -> EvalStatus:
    """Evaluate a ConditionGroup recursively with defensive depth limit."""
    if _depth > _max_depth:
        logger.warning("Max recursion depth (%d) exceeded in ConditionGroup evaluation.", _max_depth)
        return EvalStatus.UNKNOWN

    if group.applies_when is not None:
        guard_results: list[ConditionResult] = []
        guard_status = _eval_group(
            group.applies_when,
            profile,
            guard_results,
            _depth=_depth + 1,
            _max_depth=_max_depth,
        )
        if guard_status in (EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE):
            return EvalStatus.NOT_APPLICABLE
        elif guard_status == EvalStatus.UNKNOWN:
            return EvalStatus.UNKNOWN

    child_statuses: list[EvalStatus] = []

    for child in group.children:
        if isinstance(child, Condition):
            s = _eval_condition(child, profile, results, _depth=_depth + 1, _max_depth=_max_depth)
        elif isinstance(child, ConditionGroup):
            s = _eval_group(child, profile, results, _depth=_depth + 1, _max_depth=_max_depth)
        else:
            logger.error("Unknown ConditionNode type: %s", type(child))
            s = EvalStatus.UNKNOWN
        child_statuses.append(s)

    if not child_statuses:
        return EvalStatus.UNKNOWN

    applicable_statuses = [s for s in child_statuses if s != EvalStatus.NOT_APPLICABLE]
    if not applicable_statuses:
        return EvalStatus.NOT_APPLICABLE

    op = group.operator.upper()
    if op == "AND":
        # AND: FAIL dominates, then UNKNOWN, otherwise PASS, ignoring N/A
        if any(s == EvalStatus.FAIL for s in applicable_statuses):
            return EvalStatus.FAIL
        if any(s == EvalStatus.UNKNOWN for s in applicable_statuses):
            return EvalStatus.UNKNOWN
        if all(s == EvalStatus.PASS for s in applicable_statuses):
            return EvalStatus.PASS
        return EvalStatus.UNKNOWN

    elif op == "OR":
        # OR: PASS dominates, then UNKNOWN, otherwise FAIL, ignoring N/A
        if any(s == EvalStatus.PASS for s in applicable_statuses):
            return EvalStatus.PASS
        if any(s == EvalStatus.UNKNOWN for s in applicable_statuses):
            return EvalStatus.UNKNOWN
        if all(s == EvalStatus.FAIL for s in applicable_statuses):
            return EvalStatus.FAIL
        return EvalStatus.UNKNOWN

    else:
        logger.error("Unknown group operator: %s", op)
        return EvalStatus.UNKNOWN


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_eligibility(
    candidate_profile: CandidateProfile,
    eligibility_ast: ConditionGroup | None,
) -> EligibilityResult:
    """
    Evaluate a candidate profile against an eligibility AST.

    Parameters
    ----------
    candidate_profile:
        A dict mapping normalized attribute names to candidate values.
        Example: {"age": 22, "marks_percentage": 82.0, "category": "SC"}

    eligibility_ast:
        The root ConditionGroup from NoticeAnalysis.eligibility.
        If None (no eligibility conditions stated), returns UNKNOWN.

    Returns
    -------
    EligibilityResult with overall PASS/FAIL/UNKNOWN and per-condition details.

    Notes
    -----
    This function is DETERMINISTIC — it does not call any model.
    It is NOT a legal eligibility determination.
    """
    if eligibility_ast is None:
        return EligibilityResult(
            overall=EvalStatus.UNKNOWN,
            conditions=[
                ConditionResult(
                    condition_id="__root__",
                    status=EvalStatus.UNKNOWN,
                    reason="No eligibility conditions were extracted from the notice.",
                )
            ],
        )

    results: list[ConditionResult] = []
    overall = _eval_group(eligibility_ast, candidate_profile, results)

    return EligibilityResult(overall=overall, conditions=results)
