"""
Deep validation tests for core contracts and evaluator primitives.

Covers:
  1. Date-based eligibility (date of birth ranges)
  2. Automatic age calculation from date_of_birth as on reference_date
  3. Guarded conditions via applies_when (category-specific relaxations)
  4. NOT_APPLICABLE evaluation state handling
  5. Multi-value profile attributes (e.g. candidate has multiple degrees)
  6. Case-insensitive categorical comparison
  7. Thousand multiplier normalization (Telugu 'వేలు', Hindi 'हजार')
  8. Action graph topological execution order and cycle detection
  9. Table and section provenance in EvidenceSpan
  10. Multi-day windows / date ranges in TypedDate (end_value)
"""

import pytest

from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.dates import TypedDate, DateRole, DatePrecision
from indicnotice.schemas.actions import ActionNode, ActionType, get_action_execution_order
from indicnotice.schemas.eligibility import (
    Comparator,
    Condition,
    ConditionGroup,
    EvalStatus,
)
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.validation.normalizers import normalize_inr


# ===========================================================================
# 1. Date-based eligibility & Age from Date of Birth
# ===========================================================================

class TestDateAndAgeSemantics:
    def test_dob_between_dates_pass(self):
        """Born between 1999-07-02 and 2006-07-01 -> PASS for 2001-05-15"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_dob",
                    attribute="date_of_birth",
                    comparator=Comparator.BETWEEN,
                    value=["1999-07-02", "2006-07-01"],
                    evidence_ids=[],
                )
            ],
        )
        profile = {"date_of_birth": "2001-05-15"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS

    def test_dob_between_dates_fail_too_old(self):
        """Born 1998-01-01 -> FAIL (born before 1999-07-02)"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_dob",
                    attribute="date_of_birth",
                    comparator=Comparator.BETWEEN,
                    value=["1999-07-02", "2006-07-01"],
                    evidence_ids=[],
                )
            ],
        )
        res = evaluate_eligibility({"date_of_birth": "1998-01-01"}, ast)
        assert res.overall == EvalStatus.FAIL

    def test_age_calculated_from_dob_with_reference_date(self):
        """
        Rule: age <= 25 as on 2024-07-01
        Candidate provides date_of_birth = 2000-01-01
        On 2024-07-01, candidate age is 24 -> PASS
        """
        ast = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_age_ref",
                    attribute="age",
                    comparator=Comparator.LTE,
                    value=25,
                    reference_date="2024-07-01",
                    evidence_ids=[],
                )
            ],
        )
        profile = {"date_of_birth": "2000-01-01"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS

    def test_age_calculated_from_dob_fail_exceeded(self):
        """
        Rule: age <= 25 as on 2024-07-01
        Candidate provides date_of_birth = 1998-05-10
        On 2024-07-01, candidate age is 26 -> FAIL
        """
        ast = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_age_ref",
                    attribute="age",
                    comparator=Comparator.LTE,
                    value=25,
                    reference_date="2024-07-01",
                    evidence_ids=[],
                )
            ],
        )
        profile = {"date_of_birth": "1998-05-10"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.FAIL


# ===========================================================================
# 2. Guarded Conditions & Category Relaxations
# ===========================================================================

class TestGuardedConditionsAndRelaxations:
    def _build_sc_st_relaxation_ast(self) -> ConditionGroup:
        """
        Notice specifies:
        - General: age <= 30
        - SC/ST relaxation: age <= 35
        """
        general_branch = Condition(
            condition_id="c_gen_age",
            attribute="age",
            comparator=Comparator.LTE,
            value=30,
            applies_when=ConditionGroup(
                operator="AND",
                children=[
                    Condition(
                        condition_id="g_gen",
                        attribute="category",
                        comparator=Comparator.NOT_IN,
                        value=["SC", "ST"],
                        evidence_ids=[],
                    )
                ],
            ),
            evidence_ids=[],
        )
        sc_st_branch = Condition(
            condition_id="c_sc_age",
            attribute="age",
            comparator=Comparator.LTE,
            value=35,
            applies_when=ConditionGroup(
                operator="AND",
                children=[
                    Condition(
                        condition_id="g_sc",
                        attribute="category",
                        comparator=Comparator.IN,
                        value=["SC", "ST"],
                        evidence_ids=[],
                    )
                ],
            ),
            evidence_ids=[],
        )
        return ConditionGroup(operator="OR", children=[general_branch, sc_st_branch])

    def test_sc_candidate_passes_with_relaxation(self):
        ast = self._build_sc_st_relaxation_ast()
        # SC candidate, age 33 (exceeds General limit 30, but within SC limit 35)
        profile = {"category": "SC", "age": 33}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS
        # General branch was NOT_APPLICABLE
        gen_res = [c for c in res.conditions if c.condition_id == "c_gen_age"][0]
        assert gen_res.status == EvalStatus.NOT_APPLICABLE

    def test_general_candidate_fails_beyond_general_limit(self):
        ast = self._build_sc_st_relaxation_ast()
        # General candidate, age 33
        profile = {"category": "General", "age": 33}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.FAIL
        # SC branch was NOT_APPLICABLE
        sc_res = [c for c in res.conditions if c.condition_id == "c_sc_age"][0]
        assert sc_res.status == EvalStatus.NOT_APPLICABLE


# ===========================================================================
# 3. Collection Attributes & Categorical Matching
# ===========================================================================

class TestCollectionAndCategoricalMatching:
    def test_candidate_with_multiple_degrees(self):
        """Candidate has list of degrees; rule requires B.Tech"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_deg",
                    attribute="education_level",
                    comparator=Comparator.EQ,
                    value="B.Tech",
                    evidence_ids=[],
                )
            ],
        )
        profile = {"education_level": ["10th", "12th", "B.Tech"]}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS

    def test_case_insensitive_matching(self):
        """Candidate category 'sc' matches rule threshold 'SC'"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_cat",
                    attribute="category",
                    comparator=Comparator.IN,
                    value=["SC", "ST"],
                    evidence_ids=[],
                )
            ],
        )
        profile = {"category": "sc"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS


# ===========================================================================
# 4. Normalization of Thousand Multipliers (Telugu & Hindi)
# ===========================================================================

class TestThousandNormalizers:
    def test_telugu_velu(self):
        assert normalize_inr("50 వేలు") == 50000.0

    def test_hindi_hazaar(self):
        assert normalize_inr("10 हजार") == 10000.0

    def test_english_thousand(self):
        assert normalize_inr("25 thousand") == 25000.0


# ===========================================================================
# 5. Action Graph Topological Sorting
# ===========================================================================

class TestActionExecutionOrder:
    def test_linear_action_chain_sorting(self):
        a3 = ActionNode(
            action_id="a3",
            action_type=ActionType.SUBMIT_APPLICATION,
            description="Submit",
            depends_on=["a2"],
        )
        a1 = ActionNode(
            action_id="a1",
            action_type=ActionType.OBTAIN_DOCUMENT,
            description="Obtain certificate",
            depends_on=[],
        )
        a2 = ActionNode(
            action_id="a2",
            action_type=ActionType.UPLOAD_DOCUMENT,
            description="Upload certificate",
            depends_on=["a1"],
        )
        # Passed out of order: [a3, a1, a2]
        ordered = get_action_execution_order([a3, a1, a2])
        assert [a.action_id for a in ordered] == ["a1", "a2", "a3"]

    def test_action_cycle_detection(self):
        a1 = ActionNode(
            action_id="a1",
            action_type=ActionType.REGISTER,
            description="Step 1",
            depends_on=["a2"],
        )
        a2 = ActionNode(
            action_id="a2",
            action_type=ActionType.PAY_FEE,
            description="Step 2",
            depends_on=["a1"],
        )
        with pytest.raises(ValueError) as exc:
            get_action_execution_order([a1, a2])
        assert "Cyclic dependency" in str(exc.value)


# ===========================================================================
# 6. Tabular Provenance & Date Ranges
# ===========================================================================

class TestAdvancedSchemaFields:
    def test_evidence_span_with_table_cell(self):
        ev = EvidenceSpan(
            evidence_id="ev_tbl_01",
            document_id="doc_001",
            page_number=3,
            text="18 - 42 years",
            table_id="table_vacancies",
            row_index=2,
            col_index=3,
            header_text="Age Limit",
            section_heading="Annexure-I: Post Specifications",
            extraction_method="native_pdf",
        )
        assert ev.table_id == "table_vacancies"
        assert ev.row_index == 2
        assert ev.header_text == "Age Limit"

    def test_typed_date_with_window(self):
        td = TypedDate(
            date_id="d_exam_window",
            date_type=DateRole.EXAM_DATE,
            value="2024-11-15",
            end_value="2024-11-22",
            precision=DatePrecision.DATE_ONLY,
            is_tentative=True,
            evidence_ids=["ev_tbl_01"],
        )
        assert td.date_id == "d_exam_window"
        assert td.end_value == "2024-11-22"
        assert td.is_tentative is True

    def test_evidence_span_full_provenance_including_language(self):
        """Verify EvidenceSpan retains all 9 required provenance dimensions."""
        span = EvidenceSpan(
            evidence_id="ev_full_prov",
            document_id="doc_telugu_recruitment_2024",
            page_number=4,
            text="అభ్యర్థుల వయస్సు 18 నుండి 34 సంవత్సరాల మధ్య ఉండాలి.",
            original_ocr_text="అభ్యర్థుల వయస్సు 18 నుండి 34 సంవత్సరాల మధ్య ఉండాలి.",
            bbox=[72.0, 144.0, 520.0, 168.0],
            block_id="block_p4_b2",
            char_start=240,
            char_end=310,
            table_id="table_age_relaxations",
            row_index=1,
            col_index=2,
            header_text="వయస్సు పరిమితి",
            section_heading="విభాగం 3: వయోపరిమితి మరియు సడలింపులు",
            extraction_method="ocr_indicocr",
            confidence=0.96,
            language="te",
        )
        assert span.document_id == "doc_telugu_recruitment_2024"
        assert span.page_number == 4
        assert span.bbox == [72.0, 144.0, 520.0, 168.0]
        assert span.block_id == "block_p4_b2"
        assert span.table_id == "table_age_relaxations"
        assert span.section_heading == "విభాగం 3: వయోపరిమితి మరియు సడలింపులు"
        assert span.confidence == 0.96
        assert span.language == "te"


# ===========================================================================
# 7. Four-State Logic Semantics (PASS / FAIL / UNKNOWN / NOT_APPLICABLE)
# ===========================================================================

class TestFourStateLogicTruthTable:
    """
    Exhaustively verifies operator dominance and neutrality of NOT_APPLICABLE.
    - AND: FAIL dominates, then UNKNOWN, otherwise PASS (ignoring N/A)
    - OR: PASS dominates, then UNKNOWN, otherwise FAIL (ignoring N/A)
    - if all children are NOT_APPLICABLE, the group remains NOT_APPLICABLE.
    """

    def _make_condition(self, cid: str, attr: str, comp: Comparator, val: any, guard_val: any = None) -> Condition:
        applies_when = None
        if guard_val is not None:
            # Applies only if guard_attr == guard_val
            applies_when = ConditionGroup(
                operator="AND",
                children=[Condition(
                    condition_id=f"g_{cid}",
                    attribute="guard_attr",
                    comparator=Comparator.EQ,
                    value=guard_val,
                    evidence_ids=[],
                )],
            )
        return Condition(
            condition_id=cid,
            attribute=attr,
            comparator=comp,
            value=val,
            applies_when=applies_when,
            evidence_ids=[],
        )

    def test_and_pass_with_na(self):
        """AND: [PASS, NOT_APPLICABLE] -> PASS"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # PASS
                self._make_condition("c2", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 75, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS

    def test_and_fail_dominates_na(self):
        """AND: [FAIL, NOT_APPLICABLE] -> FAIL"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # FAIL (30 < 50)
                self._make_condition("c2", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 30, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.FAIL

    def test_and_unknown_dominates_pass_with_na(self):
        """AND: [UNKNOWN, NOT_APPLICABLE] -> UNKNOWN"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                self._make_condition("c1", "missing_score", Comparator.GTE, 50),  # UNKNOWN
                self._make_condition("c2", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.UNKNOWN

    def test_and_fail_dominates_unknown_and_na(self):
        """AND: [FAIL, UNKNOWN, NOT_APPLICABLE] -> FAIL (FAIL dominates over UNKNOWN)"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # FAIL (20 < 50)
                self._make_condition("c2", "missing_score", Comparator.GTE, 50),  # UNKNOWN
                self._make_condition("c3", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 20, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.FAIL

    def test_and_all_na_remains_na(self):
        """AND: [NOT_APPLICABLE, NOT_APPLICABLE] -> NOT_APPLICABLE"""
        ast = ConditionGroup(
            operator="AND",
            children=[
                self._make_condition("c1", "score_a", Comparator.GTE, 50, guard_val="group_a"),  # N/A
                self._make_condition("c2", "score_b", Comparator.GTE, 50, guard_val="group_b"),  # N/A
            ],
        )
        profile = {"guard_attr": "group_c"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.NOT_APPLICABLE

    def test_or_pass_dominates_na(self):
        """OR: [PASS, NOT_APPLICABLE] -> PASS"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # PASS (70 >= 50)
                self._make_condition("c2", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 70, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS

    def test_or_fail_with_na(self):
        """OR: [FAIL, NOT_APPLICABLE] -> FAIL (no pass, only fail and N/A)"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # FAIL (30 < 50)
                self._make_condition("c2", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 30, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.FAIL

    def test_or_unknown_with_na(self):
        """OR: [UNKNOWN, NOT_APPLICABLE] -> UNKNOWN"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c1", "missing_score", Comparator.GTE, 50),  # UNKNOWN
                self._make_condition("c2", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.UNKNOWN

    def test_or_pass_dominates_unknown_and_na(self):
        """OR: [PASS, UNKNOWN, NOT_APPLICABLE] -> PASS (PASS dominates over UNKNOWN)"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # PASS (80 >= 50)
                self._make_condition("c2", "missing_score", Comparator.GTE, 50),  # UNKNOWN
                self._make_condition("c3", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 80, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.PASS

    def test_or_unknown_dominates_fail_and_na(self):
        """OR: [FAIL, UNKNOWN, NOT_APPLICABLE] -> UNKNOWN (UNKNOWN dominates over FAIL in OR)"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c1", "score", Comparator.GTE, 50),  # FAIL (10 < 50)
                self._make_condition("c2", "missing_score", Comparator.GTE, 50),  # UNKNOWN
                self._make_condition("c3", "special_score", Comparator.GTE, 90, guard_val="special_group"),  # N/A
            ],
        )
        profile = {"score": 10, "guard_attr": "regular_group"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.UNKNOWN

    def test_or_all_na_remains_na(self):
        """OR: [NOT_APPLICABLE, NOT_APPLICABLE] -> NOT_APPLICABLE"""
        ast = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c1", "score_a", Comparator.GTE, 50, guard_val="group_a"),  # N/A
                self._make_condition("c2", "score_b", Comparator.GTE, 50, guard_val="group_b"),  # N/A
            ],
        )
        profile = {"guard_attr": "group_c"}
        res = evaluate_eligibility(profile, ast)
        assert res.overall == EvalStatus.NOT_APPLICABLE

    def test_nested_and_or_na_propagation(self):
        """
        Nested group:
        AND(
            score >= 60 [PASS],
            OR(
                special_group_a >= 90 [N/A],
                special_group_b >= 90 [N/A]
            ) [N/A]
        ) -> PASS (the inner OR is N/A, which is neutral in AND)
        """
        inner_or = ConditionGroup(
            operator="OR",
            children=[
                self._make_condition("c_inner1", "score_a", Comparator.GTE, 90, guard_val="group_a"),
                self._make_condition("c_inner2", "score_b", Comparator.GTE, 90, guard_val="group_b"),
            ],
        )
        outer_and = ConditionGroup(
            operator="AND",
            children=[
                self._make_condition("c_main", "score", Comparator.GTE, 60),
                inner_or,
            ],
        )
        profile = {"score": 75, "guard_attr": "neither_group"}
        res = evaluate_eligibility(profile, outer_and)
        assert res.overall == EvalStatus.PASS


# ===========================================================================
# 8. Recursion Guard & Depth Protection
# ===========================================================================

class TestRecursionGuardProtection:
    def test_deep_ast_evaluates_without_stack_overflow(self):
        """
        Construct an excessively nested chain of 25 groups.
        Defensive depth limit (20) must trigger cleanly and return UNKNOWN
        rather than raising RecursionError.
        """
        current = Condition(
            condition_id="c_deep",
            attribute="age",
            comparator=Comparator.LTE,
            value=30,
            evidence_ids=[],
        )
        for i in range(25):
            current = ConditionGroup(
                operator="AND",
                children=[current],
                evidence_ids=[],
            )

        profile = {"age": 25}
        res = evaluate_eligibility(profile, current)
        # Should gracefully return UNKNOWN due to depth guard
        assert res.overall == EvalStatus.UNKNOWN
