"""
Unit tests for NLP-0 data contracts (schemas).

These tests verify that the Pydantic models correctly represent all 10
examples required by the assignment specification, and that invalid data
is rejected.

Test categories:
  A. EvidenceSpan validation
  B. Document / DocumentPage / DocumentBlock
  C. TypedDate — roles, precision, ISO validation
  D. FeeItem — amount representation
  E. DocumentRequirement — mandatory/optional/conditional, alternatives
  F. Eligibility AST — all 10 required examples
  G. ActionNode — dependency chain
  H. NoticeAnalysis — top-level assembly
  I. Edge cases and rejection tests
"""

import pytest
from pydantic import ValidationError

from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.document import Document, DocumentPage, DocumentBlock
from indicnotice.schemas.dates import TypedDate, DateRole, DatePrecision
from indicnotice.schemas.fees import FeeItem
from indicnotice.schemas.benefits import BenefitItem
from indicnotice.schemas.documents_required import DocumentRequirement, RequirementType
from indicnotice.schemas.eligibility import (
    Comparator,
    Condition,
    ConditionGroup,
    EvalStatus,
)
from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.links import LinkItem
from indicnotice.schemas.notice import (
    AnalysisWarning,
    NoticeAnalysis,
    NoticeCategory,
    NoticeMetadata,
    ReviewState,
)


# ===========================================================================
# A. EvidenceSpan
# ===========================================================================

class TestEvidenceSpan:
    def test_minimal_creation(self):
        ev = EvidenceSpan(
            evidence_id="ev_001",
            document_id="doc_001",
            page_number=1,
            text="కుటుంబ వార్షిక ఆదాయం రూ.2.5 లక్షలు మించకూడదు",
            extraction_method="native_pdf",
        )
        assert ev.evidence_id == "ev_001"
        assert ev.confidence is None
        assert ev.bbox is None

    def test_with_all_fields(self):
        ev = EvidenceSpan(
            evidence_id="ev_002",
            document_id="doc_001",
            page_number=2,
            text="Age: not more than 25 years",
            original_ocr_text="Age : not more than 25 years",
            bbox=[10.0, 20.0, 200.0, 35.0],
            block_id="blk_003",
            char_start=100,
            char_end=128,
            extraction_method="ocr_tesseract",
            confidence=0.87,
        )
        assert ev.confidence == 0.87
        assert ev.bbox == [10.0, 20.0, 200.0, 35.0]

    def test_bbox_must_have_4_elements(self):
        with pytest.raises(ValidationError) as exc_info:
            EvidenceSpan(
                evidence_id="ev_bad",
                document_id="doc_001",
                page_number=1,
                text="test",
                bbox=[10.0, 20.0],  # only 2 elements
            )
        assert "bbox must have exactly 4 elements" in str(exc_info.value)

    def test_bbox_coordinate_order(self):
        with pytest.raises(ValidationError) as exc_info:
            EvidenceSpan(
                evidence_id="ev_bad2",
                document_id="doc_001",
                page_number=1,
                text="test",
                bbox=[200.0, 20.0, 10.0, 35.0],  # x0 > x2
            )
        assert "bbox must satisfy" in str(exc_info.value)

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            EvidenceSpan(
                evidence_id="ev_bad3",
                document_id="doc_001",
                page_number=1,
                text="test",
                confidence=1.5,  # > 1.0
            )

    def test_page_number_must_be_positive(self):
        with pytest.raises(ValidationError):
            EvidenceSpan(
                evidence_id="ev_bad4",
                document_id="doc_001",
                page_number=0,  # must be >= 1
                text="test",
            )


# ===========================================================================
# B. Document / DocumentPage / DocumentBlock
# ===========================================================================

class TestDocument:
    def test_document_creation(self):
        page = DocumentPage(
            page_number=1,
            full_text="జాతీయ స్కాలర్‌షిప్ పోర్టల్ — 2024-25",
            extraction_method="native_pdf",
        )
        doc = Document(
            document_id="doc_001",
            source_path="/tmp/notice.pdf",
            source_type="pdf",
            pages=[page],
            full_text="జాతీయ స్కాలర్‌షిప్ పోర్టల్ — 2024-25",
            page_count=1,
            detected_language="te",
            has_embedded_text=True,
        )
        assert doc.page_count == 1
        assert doc.detected_language == "te"
        assert len(doc.pages) == 1

    def test_document_block(self):
        block = DocumentBlock(
            block_id="blk_001",
            page_number=1,
            text="అర్హత: వయస్సు 25 సంవత్సరాలు మించకూడదు",
            bbox=[0.0, 50.0, 400.0, 70.0],
            block_type="paragraph",
            reading_order=2,
            confidence=0.95,
            language_hint="te",
        )
        assert block.confidence == 0.95
        assert block.language_hint == "te"


# ===========================================================================
# C. TypedDate
# ===========================================================================

class TestTypedDate:
    def test_example_9_application_open_vs_deadline(self):
        """Example 9: application start date vs application deadline"""
        open_date = TypedDate(
            date_type=DateRole.APPLICATION_OPEN,
            value="2024-09-01",
            precision=DatePrecision.DATE_ONLY,
            source_text="01-09-2024",
            evidence_ids=["ev_010"],
            confidence=0.98,
        )
        deadline = TypedDate(
            date_type=DateRole.APPLICATION_DEADLINE,
            value="2024-10-15",
            time="17:00",
            precision=DatePrecision.DATETIME,
            source_text="15-10-2024, 5:00 PM",
            evidence_ids=["ev_011"],
            confidence=0.99,
            mandatory=True,
        )
        assert open_date.date_type == DateRole.APPLICATION_OPEN
        assert deadline.time == "17:00"
        assert deadline.precision == DatePrecision.DATETIME
        # Application deadline must be after application open
        from datetime import date
        assert date.fromisoformat(deadline.value) > date.fromisoformat(open_date.value)

    def test_typed_date_no_time_invention(self):
        """Spec: do not infer end-of-day time when only a date is stated."""
        td = TypedDate(
            date_type=DateRole.EXAM_DATE,
            value="2024-11-20",
            precision=DatePrecision.DATE_ONLY,
            evidence_ids=[],
        )
        assert td.time is None, "Time must not be invented when not stated"

    def test_invalid_iso_date_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TypedDate(
                date_type=DateRole.APPLICATION_DEADLINE,
                value="15-10-2024",  # wrong format
                precision=DatePrecision.DATE_ONLY,
                evidence_ids=[],
            )
        assert "ISO 8601" in str(exc_info.value)

    def test_invalid_time_rejected(self):
        with pytest.raises(ValidationError):
            TypedDate(
                date_type=DateRole.APPLICATION_DEADLINE,
                value="2024-10-15",
                time="5:00 PM",  # wrong format (not 24h HH:MM)
                precision=DatePrecision.DATETIME,
                evidence_ids=[],
            )

    def test_all_date_roles_exist(self):
        roles = {r.value for r in DateRole}
        expected = {
            "publication_date", "application_open", "application_deadline",
            "fee_payment_deadline", "correction_deadline", "exam_date",
            "interview_date", "document_verification_date", "result_date", "other",
        }
        assert expected.issubset(roles)

    def test_month_only_precision(self):
        td = TypedDate(
            date_type=DateRole.EXAM_DATE,
            value=None,
            precision=DatePrecision.MONTH_ONLY,
            source_text="November 2024",
            evidence_ids=[],
        )
        assert td.value is None
        assert td.precision == DatePrecision.MONTH_ONLY


# ===========================================================================
# D. FeeItem
# ===========================================================================

class TestFeeItem:
    def test_fee_with_source_text_preserved(self):
        fee = FeeItem(
            fee_type="application_fee",
            amount_inr=500.0,
            source_text="₹500/-",
            applies_to_category="General",
            evidence_ids=["ev_020"],
        )
        assert fee.amount_inr == 500.0
        assert fee.source_text == "₹500/-"

    def test_fee_waiver(self):
        fee = FeeItem(
            fee_type="application_fee",
            amount_inr=0.0,
            source_text="No fee for SC/ST",
            applies_to_category="SC/ST",
            waived_for="SC/ST",
            evidence_ids=["ev_021"],
        )
        assert fee.waived_for == "SC/ST"


# ===========================================================================
# E. DocumentRequirement — mandatory/optional/conditional/alternatives
# ===========================================================================

class TestDocumentRequirement:
    def test_mandatory_document(self):
        doc = DocumentRequirement(
            doc_req_id="dr_001",
            canonical_name="income_certificate",
            source_name="ఆదాయ ధృవపత్రం",
            requirement_type=RequirementType.MANDATORY,
            evidence_ids=["ev_030"],
        )
        assert doc.requirement_type == RequirementType.MANDATORY
        assert doc.applies_when is None

    def test_example_6_document_alternatives(self):
        """Example 6: either Document A OR Document B is acceptable"""
        doc_a = DocumentRequirement(
            doc_req_id="dr_002",
            canonical_name="aadhar_card",
            source_name="ఆధార్ కార్డ్",
            requirement_type=RequirementType.MANDATORY,
            alternatives=["voter_id"],  # voter_id is also acceptable
            evidence_ids=["ev_031"],
        )
        assert "voter_id" in doc_a.alternatives

    def test_example_7_category_specific_document(self):
        """Example 7: a category-specific document requirement"""
        sc_condition = ConditionGroup(
            operator="OR",
            children=[
                Condition(
                    condition_id="c_cat",
                    attribute="category",
                    comparator=Comparator.IN,
                    value=["SC", "ST"],
                    evidence_ids=["ev_032"],
                ),
            ],
        )
        doc = DocumentRequirement(
            doc_req_id="dr_003",
            canonical_name="caste_certificate",
            source_name="కుల ధృవపత్రం",
            requirement_type=RequirementType.CONDITIONAL,
            applies_when=sc_condition,
            evidence_ids=["ev_033"],
        )
        assert doc.requirement_type == RequirementType.CONDITIONAL
        assert doc.applies_when is not None
        assert doc.applies_when.operator == "OR"


# ===========================================================================
# F. Eligibility AST — all 10 required examples
# ===========================================================================

class TestEligibilityAST:
    def test_example_1_age_lte_25(self):
        """Example 1: age <= 25"""
        cond = Condition(
            condition_id="c1",
            attribute="age",
            comparator=Comparator.LTE,
            value=25,
            unit="years",
            source_text="వయస్సు 25 సంవత్సరాలు మించకూడదు",
            evidence_ids=["ev_100"],
        )
        assert cond.attribute == "age"
        assert cond.comparator == Comparator.LTE
        assert cond.value == 25

    def test_example_2_marks_gte_75(self):
        """Example 2: marks >= 75"""
        cond = Condition(
            condition_id="c2",
            attribute="marks_percentage",
            comparator=Comparator.GTE,
            value=75.0,
            unit="%",
            source_text="75% or above in qualifying exam",
            evidence_ids=["ev_101"],
        )
        assert cond.comparator == Comparator.GTE
        assert cond.value == 75.0

    def test_example_3_income_lte_250000(self):
        """Example 3: annual income <= 250000"""
        cond = Condition(
            condition_id="c3",
            attribute="annual_family_income_inr",
            comparator=Comparator.LTE,
            value=250000.0,
            unit="INR",
            source_text="కుటుంబ వార్షిక ఆదాయం ₹2.5 లక్షలు మించకూడదు",
            evidence_ids=["ev_102"],
        )
        assert cond.value == 250000.0

    def test_example_4_category_sc_or_st(self):
        """Example 4: category is SC OR ST"""
        group = ConditionGroup(
            operator="OR",
            children=[
                Condition(
                    condition_id="c4a",
                    attribute="category",
                    comparator=Comparator.EQ,
                    value="SC",
                    evidence_ids=["ev_103"],
                ),
                Condition(
                    condition_id="c4b",
                    attribute="category",
                    comparator=Comparator.EQ,
                    value="ST",
                    evidence_ids=["ev_103"],
                ),
            ],
            evidence_ids=["ev_103"],
        )
        assert group.operator == "OR"
        assert len(group.children) == 2

        # Alternative using IN
        cond_in = Condition(
            condition_id="c4_alt",
            attribute="category",
            comparator=Comparator.IN,
            value=["SC", "ST"],
            evidence_ids=["ev_103"],
        )
        assert cond_in.comparator == Comparator.IN

    def test_example_5_btech_and_income(self):
        """Example 5: B.Tech AND income <= 300000"""
        group = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c5a",
                    attribute="education_level",
                    comparator=Comparator.EQ,
                    value="B.Tech",
                    evidence_ids=["ev_104"],
                ),
                Condition(
                    condition_id="c5b",
                    attribute="annual_family_income_inr",
                    comparator=Comparator.LTE,
                    value=300000.0,
                    unit="INR",
                    evidence_ids=["ev_104"],
                ),
            ],
        )
        assert group.operator == "AND"
        assert len(group.children) == 2

    def test_example_8_eligibility_exception(self):
        """Example 8: an eligibility exception/exemption (negated condition)"""
        # "All candidates except SC/ST must pay fee"
        # Represented as a negated condition used in context
        base_cond = Condition(
            condition_id="c6",
            attribute="category",
            comparator=Comparator.IN,
            value=["SC", "ST"],
            negated=True,  # NOT in [SC, ST] → exception/exemption
            exception_of=None,
            source_text="All categories except SC/ST",
            evidence_ids=["ev_105"],
        )
        assert base_cond.negated is True

        # More explicit: "SC/ST are exempt from age relaxation condition c1"
        exemption = Condition(
            condition_id="c7",
            attribute="category",
            comparator=Comparator.IN,
            value=["SC", "ST"],
            negated=False,
            exception_of="c1",  # this exempts from condition c1
            scope="age relaxation",
            evidence_ids=["ev_106"],
        )
        assert exemption.exception_of == "c1"

    def test_nested_ast_serializes_to_json(self):
        """Verify that a nested ConditionGroup round-trips to/from JSON."""
        root = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c_age",
                    attribute="age",
                    comparator=Comparator.LTE,
                    value=25,
                    evidence_ids=[],
                ),
                ConditionGroup(
                    operator="OR",
                    children=[
                        Condition(
                            condition_id="c_cat_sc",
                            attribute="category",
                            comparator=Comparator.EQ,
                            value="SC",
                            evidence_ids=[],
                        ),
                        Condition(
                            condition_id="c_cat_st",
                            attribute="category",
                            comparator=Comparator.EQ,
                            value="ST",
                            evidence_ids=[],
                        ),
                    ],
                ),
            ],
        )
        json_str = root.model_dump_json()
        restored = ConditionGroup.model_validate_json(json_str)
        assert restored.operator == "AND"
        assert len(restored.children) == 2
        # Second child is an OR group
        inner = restored.children[1]
        assert isinstance(inner, ConditionGroup)
        assert inner.operator == "OR"

    def test_all_comparators_exist(self):
        expected = {">", ">=", "<", "<=", "==", "!=", "IN", "NOT_IN", "EXISTS", "NOT_EXISTS", "BETWEEN"}
        actual = {c.value for c in Comparator}
        assert expected == actual

    def test_between_comparator(self):
        cond = Condition(
            condition_id="c_between",
            attribute="marks_percentage",
            comparator=Comparator.BETWEEN,
            value=[60.0, 75.0],
            evidence_ids=[],
        )
        assert cond.comparator == Comparator.BETWEEN

    def test_exists_comparator(self):
        cond = Condition(
            condition_id="c_exists",
            attribute="disability_certificate",
            comparator=Comparator.EXISTS,
            value=None,
            evidence_ids=[],
        )
        assert cond.value is None


# ===========================================================================
# G. ActionNode — dependency chain (Example 10)
# ===========================================================================

class TestActionNode:
    def test_example_10_action_dependency_chain(self):
        """
        Example 10: obtain certificate -> upload document -> submit application
        """
        a1 = ActionNode(
            action_id="a1",
            action_type=ActionType.OBTAIN_DOCUMENT,
            description="Obtain income certificate from revenue authorities",
            depends_on=[],
            required_document_refs=["dr_001"],
            deadline_ref=None,
            evidence_ids=["ev_200"],
        )
        a2 = ActionNode(
            action_id="a2",
            action_type=ActionType.UPLOAD_DOCUMENT,
            description="Upload income certificate on the scholarship portal",
            depends_on=["a1"],
            required_document_refs=["dr_001"],
            deadline_ref="application_deadline",
            evidence_ids=["ev_201"],
        )
        a3 = ActionNode(
            action_id="a3",
            action_type=ActionType.SUBMIT_APPLICATION,
            description="Submit the completed application before the deadline",
            depends_on=["a2"],
            required_document_refs=[],
            deadline_ref="application_deadline",
            evidence_ids=["ev_202"],
        )
        # Verify dependency chain
        assert a1.depends_on == []
        assert "a1" in a2.depends_on
        assert "a2" in a3.depends_on
        assert a3.action_type == ActionType.SUBMIT_APPLICATION

    def test_action_types_complete(self):
        types = {t.value for t in ActionType}
        assert "obtain_document" in types
        assert "submit_application" in types
        assert "pay_fee" in types
        assert "upload_document" in types


# ===========================================================================
# H. NoticeAnalysis — top-level assembly
# ===========================================================================

class TestNoticeAnalysis:
    def _make_evidence(self) -> list[EvidenceSpan]:
        return [
            EvidenceSpan(
                evidence_id="ev_001",
                document_id="doc_001",
                page_number=1,
                text="Age not more than 25 years as on 01-09-2024",
                extraction_method="native_pdf",
            ),
            EvidenceSpan(
                evidence_id="ev_002",
                document_id="doc_001",
                page_number=1,
                text="Marks 75% or above in qualifying examination",
                extraction_method="native_pdf",
            ),
        ]

    def test_minimal_notice_analysis(self):
        analysis = NoticeAnalysis(
            analysis_id="anlz_001",
            document_id="doc_001",
            source_language="te",
            category=NoticeCategory.SCHOLARSHIP,
            evidence=self._make_evidence(),
        )
        assert analysis.schema_version == "1.0"
        assert analysis.overall_review_state == ReviewState.AUTO_EXTRACTED
        assert len(analysis.evidence) == 2

    def test_schema_version_validation(self):
        analysis = NoticeAnalysis(
            analysis_id="anlz_v1",
            document_id="doc_001",
            schema_version="1.0",
            evidence=self._make_evidence(),
        )
        assert analysis.schema_version == "1.0"

        with pytest.raises(ValidationError):
            NoticeAnalysis(
                analysis_id="anlz_bad_v",
                document_id="doc_001",
                schema_version="",  # empty rejected
                evidence=[],
            )

    def test_get_evidence_lookup(self):
        analysis = NoticeAnalysis(
            analysis_id="anlz_002",
            document_id="doc_001",
            evidence=self._make_evidence(),
        )
        span = analysis.get_evidence("ev_001")
        assert span is not None
        assert span.evidence_id == "ev_001"
        assert analysis.get_evidence("nonexistent") is None

    def test_evidence_ids_set(self):
        analysis = NoticeAnalysis(
            analysis_id="anlz_003",
            document_id="doc_001",
            evidence=self._make_evidence(),
        )
        ids = analysis.evidence_ids()
        assert "ev_001" in ids
        assert "ev_002" in ids

    def test_notice_categories_complete(self):
        cats = {c.value for c in NoticeCategory}
        assert {"scholarship", "examination", "admission", "recruitment", "other"} == cats

    def test_analysis_warning(self):
        w = AnalysisWarning(
            code="missing_deadline",
            message="No application deadline found in the notice.",
            severity="warning",
        )
        assert w.severity == "warning"

    def test_full_assembly_with_all_sub_objects(self):
        """Assemble a complete NoticeAnalysis with all sub-schema types."""
        evidence = self._make_evidence()

        metadata = NoticeMetadata(
            title="2024-25 వర్సిటీ స్కాలర్‌షిప్ నోటీస్",
            issuing_authority="State Scholarship Board",
            notice_number="SSB/2024/001",
            publication_date="2024-09-01",
        )

        dates = [
            TypedDate(
                date_type=DateRole.APPLICATION_OPEN,
                value="2024-09-01",
                precision=DatePrecision.DATE_ONLY,
                evidence_ids=["ev_001"],
            ),
            TypedDate(
                date_type=DateRole.APPLICATION_DEADLINE,
                value="2024-10-15",
                time="17:00",
                precision=DatePrecision.DATETIME,
                mandatory=True,
                evidence_ids=["ev_002"],
            ),
        ]

        eligibility = ConditionGroup(
            operator="AND",
            children=[
                Condition(
                    condition_id="c1",
                    attribute="age",
                    comparator=Comparator.LTE,
                    value=25,
                    evidence_ids=["ev_001"],
                ),
                Condition(
                    condition_id="c2",
                    attribute="marks_percentage",
                    comparator=Comparator.GTE,
                    value=75.0,
                    evidence_ids=["ev_002"],
                ),
            ],
        )

        actions = [
            ActionNode(
                action_id="a1",
                action_type=ActionType.OBTAIN_DOCUMENT,
                description="Obtain income certificate",
                depends_on=[],
                evidence_ids=["ev_001"],
            ),
            ActionNode(
                action_id="a2",
                action_type=ActionType.SUBMIT_APPLICATION,
                description="Submit application",
                depends_on=["a1"],
                deadline_ref="application_deadline",
                evidence_ids=["ev_002"],
            ),
        ]

        analysis = NoticeAnalysis(
            analysis_id="anlz_full",
            document_id="doc_001",
            source_language="te",
            category=NoticeCategory.SCHOLARSHIP,
            metadata=metadata,
            dates=dates,
            eligibility=eligibility,
            actions=actions,
            evidence=evidence,
        )

        assert analysis.metadata.issuing_authority == "State Scholarship Board"
        assert len(analysis.dates) == 2
        assert analysis.eligibility is not None
        assert len(analysis.actions) == 2
        # Round-trip JSON serialization
        json_data = analysis.model_dump_json()
        restored = NoticeAnalysis.model_validate_json(json_data)
        assert restored.analysis_id == "anlz_full"
        assert len(restored.actions) == 2
