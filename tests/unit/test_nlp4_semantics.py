from __future__ import annotations

from datetime import date

import pytest

from indicnotice.schemas.actions import ActionNode, ActionType, get_action_execution_order
from indicnotice.schemas.document import Document, DocumentBlock, DocumentPage
from indicnotice.schemas.documents_required import DocumentRequirement, RequirementType
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup, EvalStatus
from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.eligibility.explanations import explain_eligibility
from services.nlp.evaluation.semantic_metrics import evaluate_action_semantics, evaluate_eligibility_semantics
from services.nlp.ingestion.types import IngestionResult
from services.nlp.semantic.canonical import canonical_document, canonical_group, iter_conditions
from services.nlp.semantic.extractor import EvidenceGatedSemanticExtractor
from services.nlp.semantic.relaxations import DeltaRelaxation, apply_age_exemption, resolve_age_delta
from services.nlp.semantic.rules import SemanticRuleExtractor
from services.nlp.semantic.support import action_support, condition_support, document_support
from services.nlp.semantic.types import RejectionReason


def ev(text: str, eid: str = "ev1", language: str = "en") -> EvidenceSpan:
    return EvidenceSpan(evidence_id=eid, document_id="doc", page_number=2, text=text, block_id="b1", language=language)


def cond(attribute: str, comparator: Comparator, value: object, **kwargs) -> Condition:
    return Condition(condition_id=kwargs.pop("condition_id", "c1"), attribute=attribute, comparator=comparator, value=value, **kwargs)


def group(*children, operator: str = "AND") -> ConditionGroup:
    return ConditionGroup(group_id="g", operator=operator, children=list(children))


@pytest.mark.parametrize(
    ("comparator", "threshold", "values", "statuses"),
    [
        (Comparator.GTE, 75, [74.99, 75, 75.01], [EvalStatus.FAIL, EvalStatus.PASS, EvalStatus.PASS]),
        (Comparator.LT, 250000, [249999, 250000], [EvalStatus.PASS, EvalStatus.FAIL]),
        (Comparator.LTE, 250000, [250000], [EvalStatus.PASS]),
    ],
)
def test_numeric_operator_boundaries(comparator, threshold, values, statuses):
    ast = group(cond("marks_percentage" if threshold == 75 else "annual_family_income_inr", comparator, threshold))
    attribute = ast.children[0].attribute
    assert [evaluate_eligibility({attribute: value}, ast).overall for value in values] == statuses


def test_cutoff_age_uses_calendar_not_supplied_current_age():
    ast = group(cond("age", Comparator.LTE, 30, reference_date="2026-07-01", unit="years"))
    assert evaluate_eligibility({"date_of_birth": "1996-07-01", "age": 99}, ast).overall == EvalStatus.PASS
    assert evaluate_eligibility({"date_of_birth": "1996-06-30"}, ast).overall == EvalStatus.PASS
    assert evaluate_eligibility({"date_of_birth": "1995-06-30"}, ast).overall == EvalStatus.FAIL


def test_delta_relaxation_is_mutually_exclusive_and_unknown_category_stays_unknown():
    base = cond("age", Comparator.LTE, 30, evidence_ids=["base"])
    ast, error = resolve_age_delta(base, DeltaRelaxation(("SC", "ST"), 5, "relaxable by 5 years for SC/ST", ("relax",)))
    assert error is None and ast is not None
    assert evaluate_eligibility({"age": 33, "category": "SC"}, ast).overall == EvalStatus.PASS
    assert evaluate_eligibility({"age": 33, "category": "GENERAL"}, ast).overall == EvalStatus.FAIL
    assert evaluate_eligibility({"age": 33}, ast).overall == EvalStatus.UNKNOWN


def test_unresolved_delta_does_not_invent_limit():
    ast, error = resolve_age_delta(None, DeltaRelaxation(("SC",), 5, "relaxable", ("e",)))
    assert ast is None and "no supported base" in error


def test_age_exemption_becomes_not_applicable_for_exempt_profile():
    ast = apply_age_exemption(cond("age", Comparator.LTE, 30), attribute="disability_status", exempt_value="PwD", evidence_ids=["e"])
    assert evaluate_eligibility({"age": 40, "disability_status": "PwD"}, ast).overall == EvalStatus.NOT_APPLICABLE
    assert evaluate_eligibility({"age": 40, "disability_status": "NONE"}, ast).overall == EvalStatus.FAIL


def test_nested_ast_is_not_flattened_but_sibling_order_is_commutative():
    a = cond("age", Comparator.GTE, 18, condition_id="a")
    b = cond("category", Comparator.EQ, "SC", condition_id="b")
    c = cond("marks_percentage", Comparator.GTE, 85, condition_id="c")
    left = group(a, group(b, c, operator="OR"))
    equivalent = group(group(c, b, operator="OR"), a)
    different = group(group(a, b), c, operator="OR")
    assert canonical_group(left) == canonical_group(equivalent)
    assert canonical_group(left) != canonical_group(different)


def test_qualification_alternatives_are_or():
    result = SemanticRuleExtractor().extract([ev("Essential qualification: candidate must possess B.Tech or B.E. degree")])
    assert result.eligibility is not None
    alternatives = [item for item in result.eligibility.children if isinstance(item, ConditionGroup)]
    assert alternatives and alternatives[0].operator == "OR"
    assert evaluate_eligibility({"education_level": "B.E."}, result.eligibility).overall == EvalStatus.PASS


@pytest.mark.parametrize("word", ["Preference will be given to candidates with experience", "Experience is desirable"])
def test_preference_and_desirable_are_not_mandatory(word):
    result = SemanticRuleExtractor().extract([ev(word)])
    assert result.eligibility is None
    assert result.unresolved


def test_preference_clause_does_not_suppress_separate_mandatory_clause():
    result = SemanticRuleExtractor().extract([
        ev("Preference will be given to candidates with experience; B.Tech degree is required.")
    ])
    conditions = list(iter_conditions(result.eligibility))
    assert [(item.attribute, item.value) for item in conditions] == [("education_level", "B.Tech")]


def test_condition_support_checks_value_operator_and_concept():
    evidence = {"e": ev("Annual family income must be below ₹2.5 lakh", "e")}
    good = cond("annual_family_income_inr", Comparator.LT, 250000, evidence_ids=["e"], source_text=evidence["e"].text)
    wrong_value = good.model_copy(update={"value": 300000})
    wrong_operator = good.model_copy(update={"comparator": Comparator.LTE})
    assert condition_support(good, evidence).supported
    assert condition_support(wrong_value, evidence).reason == RejectionReason.UNSUPPORTED_VALUE
    assert condition_support(wrong_operator, evidence).reason == RejectionReason.UNSUPPORTED_OPERATOR


@pytest.mark.parametrize(
    "text",
    [
        "Visit the website for details regarding required documents.",
        "The prospectus is available online.",
    ],
)
def test_document_support_rejects_mentions_without_requirement_relation(text):
    item = DocumentRequirement(
        doc_req_id="d",
        canonical_name="document",
        source_name="documents" if "documents" in text else "prospectus",
        requirement_type=RequirementType.MANDATORY,
        evidence_ids=["e"],
    )
    decision = document_support(item, {"e": ev(text, "e")})
    assert not decision.supported


def test_document_support_accepts_conditional_upload_with_guard():
    text = "SC/ST applicants must upload a caste certificate."
    guard = ConditionGroup(
        group_id="guard",
        operator="AND",
        children=[Condition(
            condition_id="category",
            attribute="category",
            comparator=Comparator.IN,
            value=["SC", "ST"],
            source_text=text,
            evidence_ids=["e"],
        )],
        evidence_ids=["e"],
    )
    item = DocumentRequirement(
        doc_req_id="d",
        canonical_name="caste_certificate",
        source_name="caste certificate",
        requirement_type=RequirementType.CONDITIONAL,
        applies_when=guard,
        evidence_ids=["e"],
    )
    assert document_support(item, {"e": ev(text, "e")}).supported


def test_rule_parser_preserves_exact_operator_phrases():
    spans = [
        ev("Marks must be at least 75%", "m"),
        ev("Annual family income must be below ₹2.5 lakh", "i"),
        ev("Maximum age is 25 years", "a"),
    ]
    conditions = list(iter_conditions(SemanticRuleExtractor().extract(spans).eligibility))
    values = {(item.attribute, item.comparator, item.value) for item in conditions}
    assert ("marks_percentage", Comparator.GTE, 75.0) in values
    assert ("annual_family_income_inr", Comparator.LT, 250000.0) in values
    assert ("age", Comparator.LTE, 25) in values


def test_controlled_school_class_attempt_and_exclusion_vocabulary_is_executable():
    result = SemanticRuleExtractor().extract([
        ev("The student must be currently studying in a government or government-aided school.", "current"),
        ev("The student must have passed Class VII from a government or government-aided school.", "previous"),
        ev("A student may sit for this examination only once.", "attempt"),
        ev("Students of private, Kendriya Vidyalaya, Jawahar Navodaya Vidyalaya, KGBV or residential schools cannot apply.", "excluded"),
    ])
    conditions = list(iter_conditions(result.eligibility))
    semantic = {(item.attribute, item.comparator.value, repr(item.value)) for item in conditions}
    assert ("previous_class", "==", repr(7)) in semantic
    assert ("attempt_count", "<=", repr(1)) in semantic
    allowed_current = next(item for item in conditions if item.attribute == "current_school_type" and item.comparator == Comparator.IN)
    allowed_previous = next(item for item in conditions if item.attribute == "previous_school_type")
    assert set(allowed_current.value) == {"government", "government_aided"}
    assert set(allowed_previous.value) == {"government", "government_aided"}
    exclusion = next(item for item in conditions if item.comparator == Comparator.NOT_IN)
    assert set(exclusion.value) >= {"private", "kendriya_vidyalaya", "jawahar_navodaya_vidyalaya", "kgbv", "residential"}
    exclusion_evidence = {
        "attempt": ev("A student may sit for this examination only once.", "attempt"),
        "excluded": ev("Students of private, Kendriya Vidyalaya, Jawahar Navodaya Vidyalaya, KGBV or residential schools cannot apply.", "excluded"),
    }
    assert condition_support(exclusion, exclusion_evidence).supported
    assert evaluate_eligibility(
        {
            "current_school_type": "government",
            "previous_class": 7,
            "previous_school_type": "government_aided",
            "attempt_count": 1,
        },
        result.eligibility,
    ).overall == EvalStatus.PASS
    assert evaluate_eligibility(
        {
            "current_school_type": "private",
            "previous_class": 7,
            "previous_school_type": "government",
            "attempt_count": 1,
        },
        result.eligibility,
    ).overall == EvalStatus.FAIL
    assert evaluate_eligibility(
        {"previous_class": 7, "previous_school_type": "government", "attempt_count": 1},
        result.eligibility,
    ).overall == EvalStatus.UNKNOWN


def test_rule_parser_cutoff_and_birth_window():
    result = SemanticRuleExtractor().extract([
        ev("Maximum age is 30 years as on 01.07.2026", "age"),
        ev("Candidate must be born between 02.07.1996 and 01.07.2006", "dob"),
    ])
    conditions = list(iter_conditions(result.eligibility))
    assert any(item.reference_date == "2026-07-01" for item in conditions)
    assert any(item.attribute == "date_of_birth" and item.comparator == Comparator.BETWEEN for item in conditions)


def test_parallel_actions_have_no_fake_edge_and_then_chain_has_edges():
    result = SemanticRuleExtractor().extract([
        ev("Obtain income certificate and obtain caste certificate", "parallel"),
        ev("Register online, then upload documents and then submit the application", "chain"),
    ])
    obtains = [item for item in result.actions if item.action_type == ActionType.OBTAIN_DOCUMENT]
    chain = [item for item in result.actions if item.evidence_ids == ["chain"]]
    assert len(obtains) == 2 and all(not item.depends_on for item in obtains)
    upload = next(item for item in chain if item.action_type == ActionType.UPLOAD_DOCUMENT)
    submit = next(item for item in chain if item.action_type == ActionType.SUBMIT_APPLICATION)
    register = next(item for item in chain if item.action_type == ActionType.REGISTER)
    assert upload.depends_on == [register.action_id]
    assert submit.depends_on == [upload.action_id]


def test_optional_action_is_preserved():
    result = SemanticRuleExtractor().extract([ev("Candidates may download a copy for their records.")])
    assert len(result.actions) == 1 and result.actions[0].is_optional


def test_action_support_rejects_optional_promoted_as_mandatory():
    evidence = {"e": ev("Candidates may download a copy for their records.", "e")}
    action = ActionNode(action_id="a", action_type=ActionType.DOWNLOAD, description=evidence["e"].text, evidence_ids=["e"])
    assert action_support(action, evidence).reason == RejectionReason.UNSUPPORTED_OPERATOR


def test_optional_and_conditional_documents_require_explicit_cues():
    optional_evidence = {"o": ev("Aadhaar copy is optional if available", "o")}
    optional = DocumentRequirement(
        doc_req_id="d1", canonical_name="identity_proof", source_name="Aadhaar copy",
        requirement_type=RequirementType.OPTIONAL, evidence_ids=["o"],
    )
    conditional_evidence = {"c": ev("Only for SC/ST candidates, caste certificate is required", "c")}
    guard = group(cond("category", Comparator.IN, ["SC", "ST"], evidence_ids=["c"], source_text=conditional_evidence["c"].text))
    conditional = DocumentRequirement(
        doc_req_id="d2", canonical_name="caste_certificate", source_name="caste certificate",
        requirement_type=RequirementType.CONDITIONAL, applies_when=guard, evidence_ids=["c"],
    )
    assert document_support(optional, optional_evidence).supported
    assert document_support(conditional, conditional_evidence).supported


def test_action_cycle_is_rejected_by_execution_order():
    a = ActionNode(action_id="a", action_type=ActionType.REGISTER, description="register", depends_on=["b"])
    b = ActionNode(action_id="b", action_type=ActionType.SUBMIT_APPLICATION, description="submit", depends_on=["a"])
    with pytest.raises(ValueError, match="Cyclic"):
        get_action_execution_order([a, b])


def test_deterministic_explanation_is_evidence_linked():
    evidence = ev("Annual family income must be up to ₹3 lakh", "income")
    ast = group(cond("annual_family_income_inr", Comparator.LTE, 300000, evidence_ids=["income"]))
    explanation = explain_eligibility({"annual_family_income_inr": 250000}, ast, [evidence])
    assert explanation.overall == EvalStatus.PASS
    assert explanation.user_facing_summary.startswith("Appears eligible")
    assert explanation.conditions[0].source_pages == (2,)
    assert explanation.conditions[0].candidate_value == 250000


def _ingestion(texts: list[str]) -> IngestionResult:
    blocks = [DocumentBlock(block_id=f"b{i}", page_number=1, text=text, reading_order=i) for i, text in enumerate(texts)]
    page = DocumentPage(page_number=1, full_text="\n".join(texts), blocks=blocks, extraction_method="test")
    document = Document(document_id="doc", pages=[page], full_text=page.full_text, page_count=1, detected_language="en")
    evidence = tuple(ev(text, f"e{i}") .model_copy(update={"page_number": 1, "block_id": f"b{i}"}) for i, text in enumerate(texts))
    return IngestionResult(document, evidence, "hash", "application/pdf")


def test_hybrid_rejects_unsupported_contextual_claim():
    ingestion = _ingestion(["Marks must be at least 75%"])
    contextual = NoticeAnalysis(
        analysis_id="ctx", document_id="doc", evidence=list(ingestion.evidence),
        eligibility=group(cond("marks_percentage", Comparator.GTE, 90, evidence_ids=["e0"], source_text=ingestion.evidence[0].text)),
    )
    result = EvidenceGatedSemanticExtractor().extract_ingestion(ingestion, contextual)
    assert any(item.reason == RejectionReason.UNSUPPORTED_VALUE for item in result.diagnostics.decisions)
    assert all(item.value != 90 for item in iter_conditions(result.analysis.eligibility))


def test_hybrid_surfaces_supported_conflict_without_overwrite():
    ingestion = _ingestion(["Minimum marks are 75%; another table states minimum marks are 80%"])
    contextual = NoticeAnalysis(
        analysis_id="ctx", document_id="doc", evidence=list(ingestion.evidence),
        eligibility=group(cond("marks_percentage", Comparator.GTE, 80, evidence_ids=["e0"], source_text=ingestion.evidence[0].text)),
    )
    result = EvidenceGatedSemanticExtractor().extract_ingestion(ingestion, contextual)
    assert result.diagnostics.conflicts
    assert any(item.reason == RejectionReason.CONFLICT for item in result.diagnostics.decisions)


def test_hybrid_promotes_supported_novel_contextual_condition():
    ingestion = _ingestion(["Maximum age is 30 years", "Only women candidates are eligible"])
    contextual = NoticeAnalysis(
        analysis_id="ctx", document_id="doc", evidence=list(ingestion.evidence),
        eligibility=group(cond("gender", Comparator.EQ, "women", evidence_ids=["e1"], source_text=ingestion.evidence[1].text)),
    )
    result = EvidenceGatedSemanticExtractor().extract_ingestion(ingestion, contextual)
    assert any(item.promoted and item.origin.value == "contextual" for item in result.diagnostics.decisions)
    assert any(item.attribute == "gender" for item in iter_conditions(result.analysis.eligibility))


def test_hybrid_reconciles_duplicate_and_supported_novel_conditions_individually():
    ingestion = _ingestion([
        "Minimum marks are 55%.",
        "Eligible school types are government or government-aided schools.",
    ])
    contextual = NoticeAnalysis(
        analysis_id="ctx",
        document_id="doc",
        evidence=list(ingestion.evidence),
        eligibility=group(
            cond(
                "marks_percentage", Comparator.GTE, 55,
                condition_id="duplicate", evidence_ids=["e0"], source_text=ingestion.evidence[0].text,
            ),
            cond(
                "current_school_type", Comparator.IN, ["government", "government_aided"],
                condition_id="novel", evidence_ids=["e1"], source_text=ingestion.evidence[1].text,
            ),
        ),
    )
    result = EvidenceGatedSemanticExtractor().extract_ingestion(ingestion, contextual)
    conditions = list(iter_conditions(result.analysis.eligibility))
    assert sum(item.attribute == "marks_percentage" for item in conditions) == 1
    assert any(item.attribute == "current_school_type" for item in conditions)
    contextual_decisions = [item for item in result.diagnostics.decisions if item.origin.value == "contextual"]
    assert any(item.reason == RejectionReason.DUPLICATE for item in contextual_decisions)
    assert any(item.promoted for item in contextual_decisions)


def test_end_to_end_extracted_rule_to_candidate_decisions():
    ingestion = _ingestion(["Marks must be at least 75%", "Annual family income must be up to ₹3 lakh"])
    ast = EvidenceGatedSemanticExtractor().extract_ingestion(ingestion).analysis.eligibility
    assert evaluate_eligibility({"marks_percentage": 75, "annual_family_income_inr": 300000}, ast).overall == EvalStatus.PASS
    assert evaluate_eligibility({"marks_percentage": 74.99, "annual_family_income_inr": 200000}, ast).overall == EvalStatus.FAIL
    assert evaluate_eligibility({"marks_percentage": 80}, ast).overall == EvalStatus.UNKNOWN


def test_semantic_metrics_are_separate():
    expected = group(cond("marks_percentage", Comparator.GTE, 75))
    predicted = group(cond("marks_percentage", Comparator.GT, 75))
    report = evaluate_eligibility_semantics(predicted, expected)
    assert report.attribute_accuracy == 1.0
    assert report.operator_accuracy == 0.0
    assert report.conditions.f1 == 0.0


def test_eligibility_metrics_align_conditions_before_component_scoring():
    expected = group(
        cond("age", Comparator.LTE, 25, condition_id="age"),
        cond("annual_family_income_inr", Comparator.LT, 300000, condition_id="income"),
    )
    predicted = group(
        cond("age", Comparator.LT, 300000, condition_id="age-wrong"),
        cond("annual_family_income_inr", Comparator.LTE, 25, condition_id="income-wrong"),
    )
    report = evaluate_eligibility_semantics(predicted, expected)
    assert report.attribute_accuracy == 1.0
    assert report.operator_accuracy == 0.0
    assert report.value_accuracy == 0.0


def test_action_metrics_score_edges_and_optionality():
    expected = NoticeAnalysis(analysis_id="g", document_id="doc", actions=[
        ActionNode(action_id="r", action_type=ActionType.REGISTER, description="register"),
        ActionNode(action_id="s", action_type=ActionType.SUBMIT_APPLICATION, description="submit", depends_on=["r"]),
    ])
    predicted = expected.model_copy(deep=True)
    report = evaluate_action_semantics(predicted, expected)
    assert report.actions.f1 == 1.0 and report.dependency_edges.f1 == 1.0
    assert report.optional_accuracy == 1.0


def test_action_metrics_keep_multiple_same_type_instances():
    expected = NoticeAnalysis(analysis_id="g", document_id="doc", actions=[
        ActionNode(action_id="u1", action_type=ActionType.UPLOAD_DOCUMENT, description="upload caste", required_document_refs=["caste"]),
        ActionNode(action_id="u2", action_type=ActionType.UPLOAD_DOCUMENT, description="upload income", required_document_refs=["income"]),
    ])
    predicted = expected.model_copy(update={"actions": [expected.actions[0]]})
    report = evaluate_action_semantics(predicted, expected)
    assert report.actions.true_positive == 1
    assert report.actions.predicted == 1
    assert report.actions.expected == 2
    assert report.actions.recall == 0.5


def test_document_identity_preserves_distinct_applicability_but_merges_source_variants():
    sc_guard = group(cond("category", Comparator.IN, ["SC"], condition_id="sc"))
    selected_guard = group(cond("selection_status", Comparator.EQ, "selected", condition_id="selected"))
    first = DocumentRequirement(
        canonical_name="income_certificate", source_name="income certificate",
        requirement_type=RequirementType.CONDITIONAL, applies_when=sc_guard, evidence_ids=["e1"],
    )
    source_variant = first.model_copy(update={"source_name": "आय प्रमाण-पत्र", "evidence_ids": ["e2"]})
    other_stage = first.model_copy(update={"applies_when": selected_guard})
    assert canonical_document(first) == canonical_document(source_variant)
    assert canonical_document(first) != canonical_document(other_stage)
