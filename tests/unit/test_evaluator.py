"""
Unit tests for the deterministic eligibility evaluator.

These tests verify all PASS/FAIL/UNKNOWN semantics, AND/OR logic,
negation, BETWEEN, IN, EXISTS, and missing-attribute handling.

No models are called in these tests — the evaluator is purely deterministic.
"""

import pytest

from indicnotice.schemas.eligibility import (
    Comparator,
    Condition,
    ConditionGroup,
    EvalStatus,
)
from services.nlp.eligibility.evaluator import evaluate_eligibility


def _make_condition(
    cid: str,
    attribute: str,
    comparator: Comparator,
    value=None,
    unit: str | None = None,
    negated: bool = False,
    exception_of: str | None = None,
    scope: str | None = None,
) -> Condition:
    return Condition(
        condition_id=cid,
        attribute=attribute,
        comparator=comparator,
        value=value,
        unit=unit,
        negated=negated,
        exception_of=exception_of,
        scope=scope,
        evidence_ids=[],
    )


# ===========================================================================
# Basic PASS / FAIL / UNKNOWN
# ===========================================================================

class TestBasicEvaluation:
    def test_age_lte_pass(self):
        """age <= 25, candidate age=22 → PASS"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c1", "age", Comparator.LTE, 25)],
        )
        result = evaluate_eligibility({"age": 22}, ast)
        assert result.overall == EvalStatus.PASS
        assert result.conditions[0].status == EvalStatus.PASS

    def test_age_lte_fail(self):
        """age <= 25, candidate age=30 → FAIL"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c1", "age", Comparator.LTE, 25)],
        )
        result = evaluate_eligibility({"age": 30}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_age_unknown_when_missing(self):
        """age attribute missing from profile → UNKNOWN"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c1", "age", Comparator.LTE, 25)],
        )
        result = evaluate_eligibility({}, ast)
        assert result.overall == EvalStatus.UNKNOWN

    def test_marks_gte_pass(self):
        """marks_percentage >= 75, candidate=82 → PASS"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c2", "marks_percentage", Comparator.GTE, 75.0)],
        )
        result = evaluate_eligibility({"marks_percentage": 82.0}, ast)
        assert result.overall == EvalStatus.PASS

    def test_marks_gte_fail_exact_boundary(self):
        """marks_percentage >= 75, candidate=74.9 → FAIL (strict: 74.9 < 75)"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c2", "marks_percentage", Comparator.GTE, 75.0)],
        )
        result = evaluate_eligibility({"marks_percentage": 74.9}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_marks_gte_pass_exact_boundary(self):
        """marks_percentage >= 75, candidate=75.0 → PASS (inclusive)"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c2", "marks_percentage", Comparator.GTE, 75.0)],
        )
        result = evaluate_eligibility({"marks_percentage": 75.0}, ast)
        assert result.overall == EvalStatus.PASS

    def test_income_lte_pass(self):
        """annual_family_income_inr <= 250000, candidate=180000 → PASS"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c3", "annual_family_income_inr", Comparator.LTE, 250000.0)],
        )
        result = evaluate_eligibility({"annual_family_income_inr": 180000}, ast)
        assert result.overall == EvalStatus.PASS

    def test_income_lte_fail(self):
        """annual_family_income_inr <= 250000, candidate=300000 → FAIL"""
        ast = ConditionGroup(
            operator="AND",
            children=[_make_condition("c3", "annual_family_income_inr", Comparator.LTE, 250000.0)],
        )
        result = evaluate_eligibility({"annual_family_income_inr": 300000}, ast)
        assert result.overall == EvalStatus.FAIL


# ===========================================================================
# AND / OR group semantics
# ===========================================================================

class TestAndOrSemantics:
    def test_and_all_pass(self):
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "age", Comparator.LTE, 25),
                _make_condition("c2", "marks_percentage", Comparator.GTE, 75.0),
            ],
        )
        result = evaluate_eligibility({"age": 22, "marks_percentage": 80.0}, ast)
        assert result.overall == EvalStatus.PASS

    def test_and_one_fail(self):
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "age", Comparator.LTE, 25),
                _make_condition("c2", "marks_percentage", Comparator.GTE, 75.0),
            ],
        )
        result = evaluate_eligibility({"age": 30, "marks_percentage": 80.0}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_and_one_unknown(self):
        """AND with one UNKNOWN and all else PASS → UNKNOWN"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "age", Comparator.LTE, 25),
                _make_condition("c2", "marks_percentage", Comparator.GTE, 75.0),
            ],
        )
        result = evaluate_eligibility({"age": 22}, ast)  # marks missing
        assert result.overall == EvalStatus.UNKNOWN

    def test_and_fail_overrides_unknown(self):
        """AND: FAIL takes precedence over UNKNOWN"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "age", Comparator.LTE, 25),
                _make_condition("c2", "marks_percentage", Comparator.GTE, 75.0),
            ],
        )
        result = evaluate_eligibility({"age": 30}, ast)  # marks missing, age fails
        assert result.overall == EvalStatus.FAIL

    def test_or_one_pass(self):
        """OR with one PASS → PASS"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                _make_condition("c1", "category", Comparator.EQ, "SC"),
                _make_condition("c2", "category", Comparator.EQ, "ST"),
            ],
        )
        result = evaluate_eligibility({"category": "SC"}, ast)
        assert result.overall == EvalStatus.PASS

    def test_or_all_fail(self):
        """OR with all FAIL → FAIL"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                _make_condition("c1", "category", Comparator.EQ, "SC"),
                _make_condition("c2", "category", Comparator.EQ, "ST"),
            ],
        )
        result = evaluate_eligibility({"category": "OBC"}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_or_unknown_when_all_unknown(self):
        """OR with all UNKNOWN → UNKNOWN"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                _make_condition("c1", "category", Comparator.EQ, "SC"),
                _make_condition("c2", "category", Comparator.EQ, "ST"),
            ],
        )
        result = evaluate_eligibility({}, ast)  # category missing
        assert result.overall == EvalStatus.UNKNOWN

    def test_or_pass_overrides_unknown(self):
        """OR: PASS takes precedence even when some conditions are UNKNOWN"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                _make_condition("c1", "category", Comparator.EQ, "SC"),
                _make_condition("c2", "marks_percentage", Comparator.GTE, 75.0),
            ],
        )
        result = evaluate_eligibility({"category": "SC"}, ast)  # marks missing
        assert result.overall == EvalStatus.PASS


# ===========================================================================
# Nested AND/OR
# ===========================================================================

class TestNestedGroups:
    def test_nested_and_or(self):
        """
        B.Tech AND income <= 300000 AND (category SC OR ST)
        """
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "education_level", Comparator.EQ, "B.Tech"),
                _make_condition("c2", "annual_family_income_inr", Comparator.LTE, 300000.0),
                ConditionGroup(
                    operator="OR",
                    children=[
                        _make_condition("c3", "category", Comparator.EQ, "SC"),
                        _make_condition("c4", "category", Comparator.EQ, "ST"),
                    ],
                ),
            ],
        )
        profile = {
            "education_level": "B.Tech",
            "annual_family_income_inr": 250000,
            "category": "ST",
        }
        result = evaluate_eligibility(profile, ast)
        assert result.overall == EvalStatus.PASS

    def test_nested_and_or_fail_inner_or(self):
        """All conditions met except category is OBC → FAIL"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "education_level", Comparator.EQ, "B.Tech"),
                ConditionGroup(
                    operator="OR",
                    children=[
                        _make_condition("c3", "category", Comparator.EQ, "SC"),
                        _make_condition("c4", "category", Comparator.EQ, "ST"),
                    ],
                ),
            ],
        )
        result = evaluate_eligibility({"education_level": "B.Tech", "category": "OBC"}, ast)
        assert result.overall == EvalStatus.FAIL


# ===========================================================================
# IN / NOT_IN comparators
# ===========================================================================

class TestInComparator:
    def test_in_pass(self):
        """category IN [SC, ST, OBC] → PASS for OBC"""
        cond = _make_condition("c1", "category", Comparator.IN, ["SC", "ST", "OBC"])
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"category": "OBC"}, ast)
        assert result.overall == EvalStatus.PASS

    def test_in_fail(self):
        """category IN [SC, ST] → FAIL for General"""
        cond = _make_condition("c1", "category", Comparator.IN, ["SC", "ST"])
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"category": "General"}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_not_in_pass(self):
        """category NOT_IN [SC, ST] → PASS for General"""
        cond = _make_condition("c1", "category", Comparator.NOT_IN, ["SC", "ST"])
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"category": "General"}, ast)
        assert result.overall == EvalStatus.PASS


# ===========================================================================
# BETWEEN comparator
# ===========================================================================

class TestBetweenComparator:
    def test_between_pass(self):
        """marks_percentage BETWEEN [60, 75] → PASS for 70"""
        cond = _make_condition("c1", "marks_percentage", Comparator.BETWEEN, [60.0, 75.0])
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"marks_percentage": 70.0}, ast)
        assert result.overall == EvalStatus.PASS

    def test_between_fail_above(self):
        """marks_percentage BETWEEN [60, 75] → FAIL for 80"""
        cond = _make_condition("c1", "marks_percentage", Comparator.BETWEEN, [60.0, 75.0])
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"marks_percentage": 80.0}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_between_inclusive_boundaries(self):
        """BETWEEN boundaries are inclusive"""
        cond = _make_condition("c1", "marks_percentage", Comparator.BETWEEN, [60.0, 75.0])
        ast = ConditionGroup(operator="AND", children=[cond])
        assert evaluate_eligibility({"marks_percentage": 60.0}, ast).overall == EvalStatus.PASS
        assert evaluate_eligibility({"marks_percentage": 75.0}, ast).overall == EvalStatus.PASS


# ===========================================================================
# EXISTS / NOT_EXISTS
# ===========================================================================

class TestExistsComparator:
    def test_exists_pass(self):
        """disability_certificate EXISTS → PASS when present"""
        cond = _make_condition("c1", "disability_certificate", Comparator.EXISTS)
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"disability_certificate": "cert_123"}, ast)
        assert result.overall == EvalStatus.PASS

    def test_exists_fail_when_none(self):
        """disability_certificate EXISTS → FAIL when None"""
        cond = _make_condition("c1", "disability_certificate", Comparator.EXISTS)
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"disability_certificate": None}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_not_exists_pass_when_absent(self):
        """prior_scholarship NOT_EXISTS → PASS when not in profile"""
        cond = _make_condition("c1", "prior_scholarship", Comparator.NOT_EXISTS)
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"prior_scholarship": None}, ast)
        assert result.overall == EvalStatus.PASS


# ===========================================================================
# Negation (exemptions, exceptions)
# ===========================================================================

class TestNegation:
    def test_negated_condition(self):
        """NOT (category IN [SC, ST]) → PASS for General"""
        cond = _make_condition("c1", "category", Comparator.IN, ["SC", "ST"], negated=True)
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"category": "General"}, ast)
        assert result.overall == EvalStatus.PASS

    def test_negated_condition_fail(self):
        """NOT (category IN [SC, ST]) → FAIL for SC"""
        cond = _make_condition("c1", "category", Comparator.IN, ["SC", "ST"], negated=True)
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({"category": "SC"}, ast)
        assert result.overall == EvalStatus.FAIL

    def test_negation_does_not_change_unknown(self):
        """NOT (age <= 25) with missing age → UNKNOWN (negation doesn't resolve unknowns)"""
        cond = _make_condition("c1", "age", Comparator.LTE, 25, negated=True)
        ast = ConditionGroup(operator="AND", children=[cond])
        result = evaluate_eligibility({}, ast)
        assert result.overall == EvalStatus.UNKNOWN


# ===========================================================================
# None eligibility_ast
# ===========================================================================

class TestNullAST:
    def test_none_ast_returns_unknown(self):
        result = evaluate_eligibility({"age": 22}, None)
        assert result.overall == EvalStatus.UNKNOWN
        assert "No eligibility conditions" in result.conditions[0].reason


# ===========================================================================
# Result contains per-condition explanations
# ===========================================================================

class TestConditionResults:
    def test_per_condition_reasons(self):
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "age", Comparator.LTE, 25),
                _make_condition("c2", "marks_percentage", Comparator.GTE, 75.0),
            ],
        )
        profile = {"age": 22, "marks_percentage": 82.0}
        result = evaluate_eligibility(profile, ast)
        ids = {r.condition_id for r in result.conditions}
        assert "c1" in ids
        assert "c2" in ids
        for r in result.conditions:
            assert r.reason  # reason must be non-empty

    def test_unknown_reason_mentions_attribute(self):
        ast = ConditionGroup(
            operator="AND",
            children=[
                _make_condition("c1", "annual_family_income_inr", Comparator.LTE, 250000),
            ],
        )
        result = evaluate_eligibility({}, ast)
        assert result.overall == EvalStatus.UNKNOWN
        assert "annual_family_income_inr" in result.conditions[0].reason
