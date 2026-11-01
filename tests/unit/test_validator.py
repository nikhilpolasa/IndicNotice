"""
Unit tests for the NoticeAnalysis validation layer.

Tests cover:
  - dangling evidence references
  - invalid date formats
  - date ordering violations
  - duplicate date roles
  - cyclic action dependency detection
  - dangling action references
  - implausible eligibility thresholds
"""

import pytest

from indicnotice.schemas.dates import TypedDate, DateRole, DatePrecision
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.notice import NoticeAnalysis, NoticeMetadata
from services.nlp.validation.validator import validate_analysis


def _ev(eid: str, doc_id: str = "doc_001", page: int = 1) -> EvidenceSpan:
    return EvidenceSpan(
        evidence_id=eid,
        document_id=doc_id,
        page_number=page,
        text=f"Evidence text for {eid}",
        extraction_method="native_pdf",
    )


def _base_analysis(**kwargs) -> NoticeAnalysis:
    """Build a minimal valid analysis for testing."""
    defaults = dict(
        analysis_id="anlz_test",
        document_id="doc_001",
        evidence=[_ev("ev_001"), _ev("ev_002")],
    )
    defaults.update(kwargs)
    return NoticeAnalysis(**defaults)


class TestEvidenceRefs:
    def test_valid_refs_no_warnings(self):
        analysis = _base_analysis(
            dates=[
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-15",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_001"],
                )
            ]
        )
        result = validate_analysis(analysis)
        dangling = [w for w in result.warnings if w.code == "dangling_evidence_ref"]
        assert len(dangling) == 0

    def test_dangling_evidence_ref_creates_error(self):
        analysis = _base_analysis(
            dates=[
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-15",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_nonexistent"],  # not in evidence list
                )
            ]
        )
        result = validate_analysis(analysis)
        dangling = [w for w in result.warnings if w.code == "dangling_evidence_ref"]
        assert len(dangling) == 1
        assert "ev_nonexistent" in dangling[0].message


class TestDateValidation:
    def test_valid_date_no_warning(self):
        analysis = _base_analysis(
            dates=[
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-15",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_001"],
                )
            ]
        )
        result = validate_analysis(analysis)
        date_errors = [w for w in result.warnings if w.code == "invalid_date_format"]
        assert len(date_errors) == 0

    def test_date_ordering_violation(self):
        """application_open AFTER application_deadline → warning"""
        analysis = _base_analysis(
            dates=[
                TypedDate(
                    date_type=DateRole.APPLICATION_OPEN,
                    value="2024-11-01",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_001"],
                ),
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-15",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_002"],
                ),
            ]
        )
        result = validate_analysis(analysis)
        ordering_warns = [w for w in result.warnings if w.code == "unexpected_date_order"]
        assert len(ordering_warns) >= 1

    def test_duplicate_date_role_warning(self):
        analysis = _base_analysis(
            dates=[
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-15",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_001"],
                ),
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-20",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_002"],
                ),
            ]
        )
        result = validate_analysis(analysis)
        dup_warns = [w for w in result.warnings if w.code == "duplicate_date_role"]
        assert len(dup_warns) == 1


class TestActionGraphValidation:
    def test_acyclic_graph_no_warning(self):
        analysis = _base_analysis(
            actions=[
                ActionNode(
                    action_id="a1",
                    action_type=ActionType.OBTAIN_DOCUMENT,
                    description="Obtain certificate",
                    depends_on=[],
                    evidence_ids=["ev_001"],
                ),
                ActionNode(
                    action_id="a2",
                    action_type=ActionType.SUBMIT_APPLICATION,
                    description="Submit application",
                    depends_on=["a1"],
                    evidence_ids=["ev_002"],
                ),
            ]
        )
        result = validate_analysis(analysis)
        cycle_errors = [w for w in result.warnings if w.code == "cyclic_action_dependency"]
        assert len(cycle_errors) == 0

    def test_cyclic_graph_detected(self):
        """a1 -> a2 -> a1 (cycle)"""
        analysis = _base_analysis(
            actions=[
                ActionNode(
                    action_id="a1",
                    action_type=ActionType.OBTAIN_DOCUMENT,
                    description="Step 1",
                    depends_on=["a2"],  # cycle: a1 depends on a2 and vice versa
                    evidence_ids=["ev_001"],
                ),
                ActionNode(
                    action_id="a2",
                    action_type=ActionType.SUBMIT_APPLICATION,
                    description="Step 2",
                    depends_on=["a1"],
                    evidence_ids=["ev_002"],
                ),
            ]
        )
        result = validate_analysis(analysis)
        cycle_errors = [w for w in result.warnings if w.code == "cyclic_action_dependency"]
        assert len(cycle_errors) >= 1

    def test_dangling_action_ref(self):
        """a2 depends on a3 which doesn't exist"""
        analysis = _base_analysis(
            actions=[
                ActionNode(
                    action_id="a1",
                    action_type=ActionType.OBTAIN_DOCUMENT,
                    description="Step 1",
                    depends_on=[],
                    evidence_ids=["ev_001"],
                ),
                ActionNode(
                    action_id="a2",
                    action_type=ActionType.SUBMIT_APPLICATION,
                    description="Step 2",
                    depends_on=["a3"],  # a3 doesn't exist
                    evidence_ids=["ev_002"],
                ),
            ]
        )
        result = validate_analysis(analysis)
        dangle_errors = [w for w in result.warnings if w.code == "dangling_action_ref"]
        assert len(dangle_errors) == 1


class TestEligibilityRangeChecks:
    def test_implausible_percentage_threshold(self):
        analysis = _base_analysis(
            eligibility=ConditionGroup(
                operator="AND",
                children=[
                    Condition(
                        condition_id="c1",
                        attribute="marks_percentage",
                        comparator=Comparator.GTE,
                        value=150.0,  # implausible
                        evidence_ids=["ev_001"],
                    )
                ],
            )
        )
        result = validate_analysis(analysis)
        pct_warns = [w for w in result.warnings if w.code == "implausible_percentage"]
        assert len(pct_warns) == 1

    def test_valid_percentage_threshold_no_warning(self):
        analysis = _base_analysis(
            eligibility=ConditionGroup(
                operator="AND",
                children=[
                    Condition(
                        condition_id="c1",
                        attribute="marks_percentage",
                        comparator=Comparator.GTE,
                        value=75.0,
                        evidence_ids=["ev_001"],
                    )
                ],
            )
        )
        result = validate_analysis(analysis)
        pct_warns = [w for w in result.warnings if w.code == "implausible_percentage"]
        assert len(pct_warns) == 0

    def test_implausible_age_threshold(self):
        analysis = _base_analysis(
            eligibility=ConditionGroup(
                operator="AND",
                children=[
                    Condition(
                        condition_id="c1",
                        attribute="age",
                        comparator=Comparator.LTE,
                        value=200,  # implausible
                        evidence_ids=["ev_001"],
                    )
                ],
            )
        )
        result = validate_analysis(analysis)
        age_warns = [w for w in result.warnings if w.code == "implausible_age"]
        assert len(age_warns) == 1


class TestReviewState:
    def test_errors_set_needs_review(self):
        """Dangling refs (error severity) should set needs_review"""
        analysis = _base_analysis(
            dates=[
                TypedDate(
                    date_type=DateRole.APPLICATION_DEADLINE,
                    value="2024-10-15",
                    precision=DatePrecision.DATE_ONLY,
                    evidence_ids=["ev_bad"],  # dangling
                )
            ]
        )
        result = validate_analysis(analysis)
        from indicnotice.schemas.notice import ReviewState
        assert result.overall_review_state == ReviewState.NEEDS_REVIEW
