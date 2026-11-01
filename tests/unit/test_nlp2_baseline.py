from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from indicnotice.schemas import (
    Comparator,
    DatePrecision,
    DateRole,
    Document,
    DocumentBlock,
    DocumentPage,
    NoticeCategory,
    ReviewState,
)
from services.nlp.adapters.interfaces import StructuredExtractor
from services.nlp.evaluation.extraction_metrics import aggregate_reports, evaluate_extraction
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.extraction.baseline.evidence import evidence_from_document
from services.nlp.validation.validator import validate_analysis


def make_document(texts: list[str], *, language: str = "en", document_id: str = "doc-nlp2") -> Document:
    blocks = [
        DocumentBlock(block_id=f"b{index}", page_number=1, text=text, reading_order=index)
        for index, text in enumerate(texts)
    ]
    full_text = "\n".join(texts)
    return Document(
        document_id=document_id,
        pages=[DocumentPage(page_number=1, full_text=full_text, blocks=blocks, extraction_method="test")],
        full_text=full_text,
        page_count=1,
        detected_language=language,
        extraction_method="test",
    )


def leaves(analysis):
    if analysis.eligibility is None:
        return []
    pending = list(analysis.eligibility.children)
    result = []
    while pending:
        item = pending.pop(0)
        if hasattr(item, "children"):
            pending[0:0] = list(item.children)
        else:
            result.append(item)
    return result


def test_frozen_structured_extractor_interface_and_determinism():
    doc = make_document(["Government of India", "Recruitment Notification", "Notice No: ABC/2026/01"])
    extractor = RegexBaselineExtractor()
    assert isinstance(extractor, StructuredExtractor)
    first = extractor.extract(doc)
    second = extractor.extract(doc)
    assert first == second
    assert first.analysis_id == "nlp2:doc-nlp2"
    assert first.extractor_model == "regex-baseline-nlp2-v1"
    assert first.extraction_timestamp is None
    assert not [warning for warning in validate_analysis(first).warnings if warning.severity == "error"]


def test_metadata_identity_category_and_evidence_are_grounded():
    doc = make_document(
        [
            "Government of India, Ministry of Education",
            "Recruitment Notification for Project Staff",
            "Advertisement No. EDU/REC/2026-01",
        ]
    )
    result = RegexBaselineExtractor().extract_with_trace(doc, evidence_from_document(doc))
    analysis = result.analysis
    assert analysis.category == NoticeCategory.RECRUITMENT
    assert analysis.metadata.title == "Recruitment Notification for Project Staff"
    assert analysis.metadata.issuing_authority == "Government of India, Ministry of Education"
    assert analysis.metadata.notice_number == "EDU/REC/2026-01"
    assert analysis.metadata.title_evidence_ids
    assert {trace.rule_id for trace in result.traces} >= {
        "NLP2.CATEGORY.RECRUITMENT",
        "NLP2.METADATA.TITLE.CUE",
        "NLP2.METADATA.NOTICE_NUMBER",
    }


def test_typed_date_roles_time_and_publication_metadata():
    doc = make_document(
        [
            "Public Notice dated: 15/09/2025",
            "Online application start date: 20/09/2025",
            "Last date for application: 30/09/2025 at 17:30 hours",
            "Examination date: 12 October 2025",
        ]
    )
    analysis = RegexBaselineExtractor().extract(doc)
    by_role = {item.date_type: item for item in analysis.dates}
    assert by_role[DateRole.PUBLICATION_DATE].value == "2025-09-15"
    assert by_role[DateRole.APPLICATION_OPEN].value == "2025-09-20"
    assert by_role[DateRole.APPLICATION_DEADLINE].value == "2025-09-30"
    assert by_role[DateRole.APPLICATION_DEADLINE].time == "17:30"
    assert by_role[DateRole.APPLICATION_DEADLINE].precision == DatePrecision.DATETIME
    assert by_role[DateRole.EXAM_DATE].value == "2025-10-12"
    assert analysis.metadata.publication_date == "2025-09-15"


def test_ambiguous_numeric_date_is_not_silently_guessed():
    analysis = RegexBaselineExtractor().extract(
        make_document(["Last date for application: 03/04/2026"])
    )
    item = analysis.dates[0]
    assert item.value is None
    assert item.precision == DatePrecision.UNCERTAIN
    assert item.review_state == ReviewState.NEEDS_REVIEW
    assert any(warning.code == "ambiguous_numeric_date" for warning in analysis.warnings)


def test_application_window_assigns_open_and_deadline_by_position():
    analysis = RegexBaselineExtractor().extract(
        make_document(["Applications may be submitted from 13 March 2025 to 28 March 2025"])
    )
    assert [(item.date_type, item.value) for item in analysis.dates] == [
        (DateRole.APPLICATION_OPEN, "2025-03-13"),
        (DateRole.APPLICATION_DEADLINE, "2025-03-28"),
    ]


def test_fee_requires_local_fee_cue_and_rejects_salary_income_and_benefit():
    analysis = RegexBaselineExtractor().extract(
        make_document(
            [
                "Application fee: Rs. 500/-",
                "Monthly salary: Rs. 25,000/-",
                "Annual family income must not exceed Rs. 2,50,000/-",
                "Scholarship benefit: Rs. 12,000 per year",
            ]
        )
    )
    assert [(item.fee_type, item.amount_inr) for item in analysis.fees] == [("application_fee", 500.0)]
    assert [item.amount_inr for item in analysis.benefits] == [12000.0]


def test_explicit_no_fee_is_preserved_as_zero_not_missing():
    analysis = RegexBaselineExtractor().extract(make_document(["There is no fee for this examination."]))
    assert [(item.fee_type, item.amount_inr, item.source_text) for item in analysis.fees] == [
        ("application_fee", 0.0, "no fee")
    ]


def test_required_documents_need_requirement_context():
    analysis = RegexBaselineExtractor().extract(
        make_document(
            [
                "The office issued an income certificate last year.",
                "Required documents to upload:",
                "Income certificate, caste certificate and Aadhaar card",
            ]
        )
    )
    assert {item.canonical_name for item in analysis.required_documents} == {
        "income_certificate",
        "caste_certificate",
        "identity_proof",
    }


def test_document_requirements_capture_category_disability_and_selection_guards():
    analysis = RegexBaselineExtractor().extract(make_document([
        "SC/ST applicants must upload a caste certificate.",
        "PwD applicants must upload a disability certificate.",
        "Selected candidates must submit an income certificate.",
    ]))
    documents = {item.canonical_name: item for item in analysis.required_documents}
    assert all(item.requirement_type.value == "conditional" for item in documents.values())
    assert documents["caste_certificate"].applies_when.children[0].attribute == "category"
    assert documents["disability_certificate"].applies_when.children[0].attribute == "disability_status"
    assert documents["income_certificate"].applies_when.children[0].attribute == "selection_status"


def test_urls_support_http_and_www_but_not_email_fragments():
    analysis = RegexBaselineExtractor().extract(
        make_document(
            [
                "Apply at www.example.gov.in/apply.",
                "Read https://example.gov.in/notice?id=1.",
                "Help: officer@example.gov.in",
            ]
        )
    )
    assert [item.url for item in analysis.links] == [
        "https://www.example.gov.in/apply",
        "https://example.gov.in/notice?id=1",
    ]


def test_url_tokenization_stops_before_adjacent_indic_text_and_keeps_query():
    analysis = RegexBaselineExtractor().extract(
        make_document([
            "Apply at https://example.gov.inतथा continue.",
            "Details: https://example.gov.in/path?a=1&b=two.",
        ])
    )
    assert [item.url for item in analysis.links] == [
        "https://example.gov.in",
        "https://example.gov.in/path?a=1&b=two",
    ]


def test_title_ranking_deprioritizes_generic_notice_heading():
    analysis = RegexBaselineExtractor().extract(
        make_document([
            "NOTICE",
            "District Science Scholarship Examination Schedule",
            "Class VIII - 2026-2027",
            "This paragraph explains how applicants should submit a long application form online.",
        ])
    )
    assert analysis.metadata.title == "District Science Scholarship Examination Schedule Class VIII - 2026-2027"
    assert analysis.metadata.title_evidence_ids == ["ev:b1", "ev:b2"]


def test_eligibility_preserves_inclusive_and_strict_comparators_and_or_group():
    analysis = RegexBaselineExtractor().extract(
        make_document(
            [
                "Eligibility: age between 18 and 25 years.",
                "Annual family income must be less than Rs. 2.5 lakh.",
                "Minimum 55% marks are required.",
                "Qualification: B.Tech or B.E. degree.",
            ]
        )
    )
    items = leaves(analysis)
    values = {(item.attribute, item.comparator, repr(item.value)) for item in items}
    assert ("age", Comparator.BETWEEN, repr([18, 25])) in values
    assert ("annual_family_income_inr", Comparator.LT, repr(250000.0)) in values
    assert ("marks_percentage", Comparator.GTE, repr(55.0)) in values
    qualification_group = next(item for item in analysis.eligibility.children if hasattr(item, "children"))
    assert qualification_group.operator == "OR"
    assert {item.value for item in qualification_group.children} == {"B.Tech", "B.E."}


def test_eligibility_example_numbers_are_rejected():
    result = RegexBaselineExtractor().extract_with_trace(
        make_document(["Example: if a candidate is age 20 years, award 1 mark."]),
        evidence_from_document(make_document(["Example: if a candidate is age 20 years, award 1 mark."])),
    )
    assert result.analysis.eligibility is None
    assert any(trace.rule_id == "NLP2.ELIGIBILITY.EXAMPLE_GUARD" for trace in result.traces)


def test_actions_attach_resources_and_only_explicit_dependencies():
    analysis = RegexBaselineExtractor().extract(
        make_document(
            [
                "Required document: Aadhaar card must be uploaded.",
                "Upload the document at https://example.gov.in/apply",
                "After upload, submit the application online by 30 September 2025.",
            ]
        )
    )
    upload = next(item for item in analysis.actions if item.action_type.value == "upload_document")
    submit = next(item for item in analysis.actions if item.action_type.value == "submit_application")
    assert upload.required_document_refs
    assert submit.depends_on == [upload.action_id]
    assert submit.deadline_ref == "application_deadline"
    assert submit.url_ref == "https://example.gov.in/apply"


def test_multiple_same_type_upload_actions_remain_distinct_and_local():
    analysis = RegexBaselineExtractor().extract(
        make_document([
            "Applicants must upload the caste certificate.",
            "Applicants must upload the income certificate.",
        ])
    )
    uploads = [item for item in analysis.actions if item.action_type.value == "upload_document"]
    assert len(uploads) == 2
    assert len(uploads[0].required_document_refs) == 1
    assert len(uploads[1].required_document_refs) == 1
    assert uploads[0].required_document_refs != uploads[1].required_document_refs


def test_hindi_and_telugu_cues_are_supported():
    hindi = RegexBaselineExtractor().extract(
        make_document(
            [
                "भारत सरकार शिक्षा मंत्रालय",
                "छात्रवृत्ति आवेदन सूचना",
                "आवेदन की अंतिम तिथि 30 सितंबर 2025",
                "पात्रता: वार्षिक पारिवारिक आय 3.5 लाख रुपये से अधिक नहीं",
            ],
            language="hi",
            document_id="hi",
        )
    )
    telugu = RegexBaselineExtractor().extract(
        make_document(
            [
                "తెలంగాణ ప్రభుత్వం విద్యా శాఖ",
                "ప్రవేశ నోటిఫికేషన్",
                "దరఖాస్తు చివరి తేదీ 30 సెప్టెంబర్ 2025",
                "అర్హత: వయస్సు 18 నుండి 25 సంవత్సరాలు",
            ],
            language="te",
            document_id="te",
        )
    )
    assert hindi.category == NoticeCategory.SCHOLARSHIP
    assert any(item.date_type == DateRole.APPLICATION_DEADLINE for item in hindi.dates)
    assert any(item.attribute == "annual_family_income_inr" for item in leaves(hindi))
    assert telugu.category == NoticeCategory.ADMISSION
    assert any(item.date_type == DateRole.APPLICATION_DEADLINE for item in telugu.dates)
    assert any(item.attribute == "age" and item.comparator == Comparator.BETWEEN for item in leaves(telugu))


def test_evaluation_scores_only_verified_complete_fields_and_labels_errors():
    analysis = RegexBaselineExtractor().extract(
        make_document(
            [
                "Recruitment Notice",
                "Notice No. ABC/1",
                "Application deadline: 30 September 2025",
                "Eligibility: age not more than 25 years",
            ]
        )
    )
    annotation = {
        "document_id": analysis.document_id,
        "fields": {
            "notice_number": {"status": "verified_complete", "value": "ABC/1"},
            "dates": {
                "status": "verified_complete",
                "items": [{"date_type": "exam_date", "value": "2025-09-30", "time": None}],
            },
            "eligibility": {
                "status": "verified_complete",
                "items": [{"attribute": "age", "comparator": "<", "value": 25, "unit": "years"}],
            },
            "title": {"status": "verified_partial", "value": "Recruitment Notice"},
        },
    }
    report = evaluate_extraction(analysis, annotation)
    assert "title" in report.skipped_fields
    assert next(item for item in report.fields if item.field == "notice_number").exact_match == 1.0
    assert {error.error_type for error in report.errors} >= {"wrong_role", "wrong_operator"}
    corpus = aggregate_reports([report, report])
    assert corpus.document_count == 2
    assert next(item for item in corpus.fields if item.field == "notice_number").true_positives == 2


def test_empty_document_produces_schema_valid_empty_analysis():
    analysis = RegexBaselineExtractor().extract(make_document(["ordinary prose without any actionable field"]))
    assert analysis.category is None
    assert analysis.dates == []
    assert analysis.fees == []
    assert analysis.eligibility is None
    assert not [warning for warning in analysis.warnings if warning.severity == "error"]


def test_versioned_gold_registry_has_ten_real_hash_matched_fixtures():
    records = json.loads(Path("datasets/annotations/nlp2/v1/annotations.json").read_text(encoding="utf-8"))
    assert len(records) == 10
    assert {item["language"] for item in records} == {"hi", "te"}
    assert sum(item["language"] == "hi" for item in records) == 5
    assert sum(item["language"] == "te" for item in records) == 5
    for item in records:
        path = Path(item["fixture_path"])
        assert path.read_bytes().startswith(b"%PDF-")
        assert sha256(path.read_bytes()).hexdigest() == item["document_id"]
        for field in item["fields"].values():
            assert field["status"] in {
                "verified_complete", "verified_partial", "unverified", "template_only"
            }
