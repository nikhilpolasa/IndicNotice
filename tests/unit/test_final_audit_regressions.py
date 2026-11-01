"""Regression tests for issues found by the independent NLP-0 audit."""

import math

import pytest
from pydantic import ValidationError

from indicnotice.schemas import (
    ActionNode,
    ActionType,
    Comparator,
    Condition,
    ConditionGroup,
    DatePrecision,
    DateRole,
    DocumentRequirement,
    EvidenceSpan,
    FeeItem,
    LinkItem,
    NoticeAnalysis,
    TypedDate,
)
from indicnotice.schemas.actions import get_action_execution_order
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.validation.normalizers import (
    normalize_cgpa,
    normalize_inr,
    normalize_percentage,
)
from services.nlp.validation.validator import validate_analysis


def _evidence(evidence_id: str = "ev_1", document_id: str = "doc_1") -> EvidenceSpan:
    return EvidenceSpan(
        evidence_id=evidence_id,
        document_id=document_id,
        page_number=1,
        text="source",
    )


class TestCutoffAgeCorrectness:
    def test_reference_date_uses_dob_not_supplied_current_age(self):
        ast = ConditionGroup(
            operator="AND",
            children=[Condition(
                condition_id="age",
                attribute="age",
                comparator=Comparator.LTE,
                value=25,
                reference_date="2024-07-01",
            )],
        )
        result = evaluate_eligibility(
            {"age": 20, "date_of_birth": "1990-01-01"}, ast
        )
        assert result.overall.value == "FAIL"

    def test_reference_date_without_dob_is_unknown(self):
        ast = ConditionGroup(
            operator="AND",
            children=[Condition(
                condition_id="age",
                attribute="age",
                comparator=Comparator.LTE,
                value=25,
                reference_date="2024-07-01",
            )],
        )
        assert evaluate_eligibility({"age": 20}, ast).overall.value == "UNKNOWN"

    def test_invalid_reference_date_rejected(self):
        with pytest.raises(ValidationError):
            Condition(
                condition_id="age",
                attribute="age",
                comparator=Comparator.LTE,
                value=25,
                reference_date="2024-02-31",
            )


class TestGuardSemantics:
    def test_unknown_category_preserves_unknown_relaxation_result(self):
        general = Condition(
            condition_id="general",
            attribute="age",
            comparator=Comparator.LTE,
            value=30,
            applies_when=ConditionGroup(
                operator="AND",
                children=[Condition(
                    condition_id="general_guard",
                    attribute="category",
                    comparator=Comparator.NOT_IN,
                    value=["SC", "ST"],
                )],
            ),
        )
        relaxed = Condition(
            condition_id="relaxed",
            attribute="age",
            comparator=Comparator.LTE,
            value=35,
            applies_when=ConditionGroup(
                operator="AND",
                children=[Condition(
                    condition_id="relaxed_guard",
                    attribute="category",
                    comparator=Comparator.IN,
                    value=["SC", "ST"],
                )],
            ),
        )
        ast = ConditionGroup(operator="OR", children=[general, relaxed])
        assert evaluate_eligibility({"age": 33}, ast).overall.value == "UNKNOWN"

    def test_not_applicable_nested_guard_does_not_evaluate_target(self):
        nested_guard = ConditionGroup(
            operator="AND",
            applies_when=ConditionGroup(
                operator="AND",
                children=[Condition(
                    condition_id="outer_guard",
                    attribute="category",
                    comparator=Comparator.EQ,
                    value="SC",
                )],
            ),
            children=[Condition(
                condition_id="inner_guard",
                attribute="district",
                comparator=Comparator.EQ,
                value="Hyderabad",
            )],
        )
        target = Condition(
            condition_id="target",
            attribute="marks_percentage",
            comparator=Comparator.GTE,
            value=75,
            applies_when=nested_guard,
        )
        ast = ConditionGroup(operator="AND", children=[target])
        result = evaluate_eligibility(
            {"category": "General", "marks_percentage": 90}, ast
        )
        assert result.overall.value == "NOT_APPLICABLE"


class TestEvidenceIntegrity:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"char_start": -1},
            {"char_start": 5, "char_end": 4},
            {"row_index": -1},
            {"col_index": -1},
            {"bbox": [0.0, 0.0, math.nan, 1.0]},
        ],
    )
    def test_malformed_evidence_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            EvidenceSpan(
                evidence_id="ev",
                document_id="doc",
                page_number=1,
                text="source",
                **kwargs,
            )

    def test_nested_and_metadata_evidence_are_validated(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            metadata={
                "title_evidence_ids": ["missing_title"],
                "notice_number_evidence_ids": ["missing_number"],
                "publication_date_evidence_ids": ["missing_publication"],
            },
            eligibility=ConditionGroup(
                operator="AND",
                children=[Condition(
                    condition_id="c1",
                    attribute="age",
                    comparator=Comparator.LTE,
                    value=25,
                    evidence_ids=["missing_condition"],
                )],
            ),
        )
        codes = [warning.code for warning in validate_analysis(analysis).warnings]
        assert codes.count("dangling_evidence_ref") == 4

    def test_duplicate_and_cross_document_evidence_are_errors(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            evidence=[_evidence("same", "other"), _evidence("same", "other")],
        )
        result = validate_analysis(analysis)
        assert "duplicate_id" in {warning.code for warning in result.warnings}
        assert "evidence_document_mismatch" in {warning.code for warning in result.warnings}


class TestDateIntegrity:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"value": "2024-02-31"},
            {"value": "2024-01-01", "time": "99:99", "precision": DatePrecision.DATETIME},
            {"value": "2024-01-02", "end_value": "2024-01-01"},
            {"value": None, "end_value": "2024-01-01"},
            {"value": "2024-01-01", "time": "10:00", "precision": DatePrecision.DATE_ONLY},
        ],
    )
    def test_invalid_date_contracts_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            TypedDate(date_type=DateRole.EXAM_DATE, **kwargs)

    def test_correction_window_has_start_role(self):
        assert DateRole.CORRECTION_START_DATE.value == "correction_start_date"


class TestCanonicalReferenceIntegrity:
    def test_unsupported_schema_version_rejected(self):
        with pytest.raises(ValidationError):
            NoticeAnalysis(
                schema_version="2.0",
                analysis_id="analysis",
                document_id="doc_1",
            )

    def test_validator_is_idempotent(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            dates=[TypedDate(
                date_type=DateRole.EXAM_DATE,
                value="2024-01-01",
                evidence_ids=["missing"],
            )],
        )
        once = validate_analysis(analysis)
        twice = validate_analysis(once)
        assert twice.warnings == once.warnings

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"comparator": Comparator.IN, "value": "SC"},
            {"comparator": Comparator.BETWEEN, "value": [1]},
            {"comparator": Comparator.EXISTS, "value": "unexpected"},
        ],
    )
    def test_malformed_comparator_values_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            Condition(condition_id="c", attribute="category", **kwargs)

    def test_invalid_group_operator_rejected(self):
        with pytest.raises(ValidationError):
            ConditionGroup(operator="XOR")

    def test_conflicting_publication_date_rejected_by_validator(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            metadata={"publication_date": "2024-01-01"},
            dates=[TypedDate(
                date_type=DateRole.PUBLICATION_DATE,
                value="2024-01-02",
            )],
        )
        assert "metadata_date_conflict" in {
            warning.code for warning in validate_analysis(analysis).warnings
        }

    def test_all_action_resource_refs_are_checked(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            actions=[ActionNode(
                action_id="a1",
                action_type=ActionType.SUBMIT_APPLICATION,
                description="Submit",
                required_document_refs=["missing_doc"],
                fee_ref="missing_fee",
                deadline_ref="missing_date",
                url_ref="https://missing.example",
            )],
        )
        codes = {warning.code for warning in validate_analysis(analysis).warnings}
        assert {
            "dangling_doc_ref",
            "dangling_fee_ref",
            "dangling_deadline_ref",
            "dangling_url_ref",
        } <= codes

    def test_duplicate_action_ids_rejected_by_ordering(self):
        actions = [
            ActionNode(action_id="a", action_type=ActionType.OTHER, description="one"),
            ActionNode(action_id="a", action_type=ActionType.OTHER, description="two"),
        ]
        with pytest.raises(ValueError, match="Duplicate action_id"):
            get_action_execution_order(actions)

    def test_missing_dependency_rejected_by_ordering(self):
        action = ActionNode(
            action_id="a",
            action_type=ActionType.OTHER,
            description="one",
            depends_on=["missing"],
        )
        with pytest.raises(ValueError, match="missing action"):
            get_action_execution_order([action])

    def test_optional_action_round_trip(self):
        action = ActionNode(
            action_id="a",
            action_type=ActionType.OTHER,
            description="Optional help-desk visit",
            is_optional=True,
        )
        restored = ActionNode.model_validate_json(action.model_dump_json())
        assert restored.is_optional is True

    def test_parallel_actions_with_multiple_dependencies_are_deterministic(self):
        actions = [
            ActionNode(action_id="submit", action_type=ActionType.SUBMIT_APPLICATION,
                       description="Submit", depends_on=["upload", "pay"]),
            ActionNode(action_id="pay", action_type=ActionType.PAY_FEE,
                       description="Pay"),
            ActionNode(action_id="upload", action_type=ActionType.UPLOAD_DOCUMENT,
                       description="Upload"),
        ]
        assert [item.action_id for item in get_action_execution_order(actions)] == [
            "pay", "upload", "submit"
        ]

    def test_invalid_review_state_rejected(self):
        with pytest.raises(ValidationError):
            FeeItem(
                fee_id="fee",
                fee_type="application_fee",
                review_state="invented_state",
            )

    def test_new_backend_name_does_not_require_schema_change(self):
        evidence = EvidenceSpan(
            evidence_id="ev",
            document_id="doc",
            page_number=1,
            text="source",
            extraction_method="ocr_future_provider_v1",
        )
        assert evidence.extraction_method == "ocr_future_provider_v1"

    @pytest.mark.parametrize("url", ["example.org", "javascript:alert(1)", "https://bad url.test"])
    def test_invalid_links_rejected(self, url):
        with pytest.raises(ValidationError):
            LinkItem(url=url)

    def test_empty_group_is_explicitly_unknown(self):
        result = evaluate_eligibility({}, ConditionGroup(operator="AND"))
        assert result.overall.value == "UNKNOWN"


class TestNumericNormalization:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("2 lakh 50 thousand", 250_000.0),
            ("2 लाख 50 हजार", 250_000.0),
            ("2 లక్షలు 50 వేలు", 250_000.0),
        ],
    )
    def test_compound_indian_amounts(self, text, expected):
        assert normalize_inr(text) == expected

    def test_ambiguous_amount_range_is_not_summed(self):
        assert normalize_inr("2 lakh to 3 lakh") is None

    @pytest.mark.parametrize("text", ["75 percent", "75 प्रतिशत", "75 శాతం"])
    def test_percentage_words(self, text):
        assert normalize_percentage(text) == 75.0

    def test_implausible_cgpa_rejected(self):
        assert normalize_cgpa("75 CGPA") is None


class TestValidatorCoverage:
    def test_contradictory_fee_amounts_flagged(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            fees=[
                FeeItem(fee_id="f1", fee_type="application_fee", amount_inr=100),
                FeeItem(fee_id="f2", fee_type="application_fee", amount_inr=200),
            ],
        )
        assert "contradictory_fee_amount" in {
            warning.code for warning in validate_analysis(analysis).warnings
        }

    def test_valid_action_references_are_accepted(self):
        analysis = NoticeAnalysis(
            analysis_id="analysis",
            document_id="doc_1",
            evidence=[_evidence()],
            required_documents=[DocumentRequirement(
                doc_req_id="doc_req",
                canonical_name="aadhaar",
                source_name="Aadhaar",
            )],
            fees=[FeeItem(fee_id="fee", fee_type="application_fee", amount_inr=100)],
            dates=[TypedDate(
                date_id="date",
                date_type=DateRole.APPLICATION_DEADLINE,
                value="2024-01-01",
            )],
            links=[LinkItem(url="https://example.org")],
            actions=[ActionNode(
                action_id="action",
                action_type=ActionType.SUBMIT_APPLICATION,
                description="Submit",
                required_document_refs=["doc_req"],
                fee_ref="fee",
                deadline_ref="date",
                url_ref="https://example.org",
            )],
        )
        assert not {
            warning.code for warning in validate_analysis(analysis).warnings
        } & {
            "dangling_doc_ref",
            "dangling_fee_ref",
            "dangling_deadline_ref",
            "dangling_url_ref",
        }
