"""Cross-language product QA over freshly parsed Hindi and Telugu fixtures."""
from pathlib import Path
import pytest
from demo.product import initial_analysis
from demo.questions import answer_notice
from services.nlp.qa import Answerability


@pytest.fixture(scope="module", params=[
    "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf",
    "datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf",
])
def real_notice(request):
    path = Path(request.param)
    return initial_analysis(path.read_bytes(), path.name)


@pytest.mark.parametrize("lang,question", [
    ("en", "What is the application deadline?"),
    ("hi", "आवेदन की अंतिम तिथि क्या है?"),
    ("te", "దరఖాస్తు చివరి తేదీ ఏమిటి?"),
])
def test_real_cross_language_deadline(real_notice, lang, question):
    answer = answer_notice(question, real_notice, language=lang)
    deadline = next(d for d in real_notice.analysis.dates if d.date_type.value == "application_deadline")
    assert deadline.value in answer.answer_text
    assert answer.answerability == Answerability.ANSWERABLE
    assert answer.answer_language == lang
    spans = {s.evidence_id: s for s in real_notice.analysis.evidence}
    assert answer.citations
    assert all(c.evidence_id in spans and c.page_number == spans[c.evidence_id].page_number for c in answer.citations)


@pytest.mark.parametrize("lang", ["en", "hi", "te"])
def test_real_missing_venue_abstains(real_notice, lang):
    answer = answer_notice("What is the interview venue?", real_notice, language=lang)
    assert answer.abstained and not answer.citations


@pytest.fixture(scope="module")
def real_kvs_notice():
    path = Path("datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf")
    return initial_analysis(path.read_bytes(), path.name)


@pytest.mark.parametrize("question,expected,page", [
    ("Is the application online or offline?", "online applications only", 1),
    ("Which classes are covered by this notice?", "Class I and Balvatika-III", 1),
    ("Which organization issued the notice?", "Kendriya Vidyalaya Sangathan (KVS)", 1),
    ("Which category includes children of State Government employees?", "Category III", 2),
    ("Who comes under Category V?", "all those not covered", 2),
    ("What determines preference in admission?", "number of transfers", 2),
    ("आवेदन ऑनलाइन होगा या ऑफलाइन?", "केवल ऑनलाइन", 1),
    ("దరఖాస్తు చేసుకోవడానికి చివరి తేదీ ఏమిటి?", "2025-03-21", 1),
])
def test_real_kvs_factual_qa_is_direct_localized_and_cited(real_kvs_notice, question, expected, page):
    answer = answer_notice(question, real_kvs_notice)
    assert expected.casefold() in answer.answer_text.casefold()
    assert answer.answerability == Answerability.ANSWERABLE
    assert not answer.abstained
    assert answer.citations and {item.page_number for item in answer.citations} == {page}
    assert answer.answer_language == ("hi" if any("\u0900" <= ch <= "\u097f" for ch in question) else "te" if any("\u0c00" <= ch <= "\u0c7f" for ch in question) else "en")
    assert "Relevant notice text:" not in answer.answer_text


@pytest.mark.parametrize("question", [
    "What is the application fee?",
    "What documents must I upload?",
    "What is the minimum age for Class I?",
    "How many seats are available?",
])
def test_real_kvs_unsupported_details_abstain_without_irrelevant_citations(real_kvs_notice, question):
    answer = answer_notice(question, real_kvs_notice)
    assert answer.answerability == Answerability.UNANSWERABLE
    assert answer.abstained and not answer.citations


@pytest.mark.parametrize("lang,question", [
    ("en", "What documents must I upload?"),
    ("te", "ఏ పత్రాలు సమర్పించాలి?"),
    ("hi", "कौन से दस्तावेज़ अपलोड करने हैं?"),
])
def test_real_kvs_missing_documents_abstain_in_question_language(real_kvs_notice, lang, question):
    answer = answer_notice(question, real_kvs_notice)
    expected = {
        "en": "This information is not stated in this notice.",
        "te": "ఈ సమాచారం ఈ నోటీసులో పేర్కొనబడలేదు.",
        "hi": "यह जानकारी इस सूचना में नहीं दी गई है।",
    }[lang]
    assert answer.answer_language == lang
    assert answer.answer_text == expected
    assert answer.abstained and not answer.citations


@pytest.mark.parametrize("lang,question", [
    ("en", "How many seats are available?"),
    ("te", "ఎన్ని సీట్లు అందుబాటులో ఉన్నాయి?"),
    ("hi", "कुल कितनी सीटें हैं?"),
])
def test_real_kvs_unstated_seat_count_abstains_in_question_language(real_kvs_notice, lang, question):
    answer = answer_notice(question, real_kvs_notice)
    assert answer.answer_language == lang
    assert answer.abstained and not answer.citations


def test_real_kvs_marks_question_qualifies_eligibility_and_cites_official_referral(real_kvs_notice):
    answer = answer_notice("Is 60% marks enough?", real_kvs_notice)
    assert answer.answerability == Answerability.PARTIAL
    assert not answer.abstained
    assert "cannot be determined" in answer.answer_text
    assert "official admission guidelines" in answer.answer_text
    assert {citation.page_number for citation in answer.citations} == {1}


def test_cross_lingual_telugu_deadline_question_on_real_hindi_notice():
    path = Path("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf")
    notice = initial_analysis(path.read_bytes(), path.name)
    answer = answer_notice("దరఖాస్తు చివరి తేదీ ఏమిటి?", notice)
    deadline = next(d for d in notice.analysis.dates if d.date_type.value == "application_deadline")
    assert answer.answer_language == "te"
    assert deadline.value in answer.answer_text
    assert answer.citations and all(citation.page_number == 1 for citation in answer.citations)


def test_cross_lingual_hindi_online_mode_question_on_real_telugu_notice(real_kvs_notice):
    answer = answer_notice("आवेदन ऑनलाइन होगा या ऑफलाइन?", real_kvs_notice)
    assert answer.answer_language == "hi"
    assert "केवल ऑनलाइन" in answer.answer_text
    assert answer.citations and all(citation.page_number == 1 for citation in answer.citations)


@pytest.mark.parametrize("question,expected,language", [
    ("राज्य सरकार के कर्मचारियों के बच्चों की श्रेणी कौन सी है?", "श्रेणी III:", "hi"),
    ("రాష్ట్ర ప్రభుత్వ ఉద్యోగుల పిల్లలు ఏ వర్గంలోకి వస్తారు?", "వర్గం III:", "te"),
    ("श्रेणी V में कौन आते हैं?", "श्रेणी V:", "hi"),
    ("వర్గం V లో ఎవరు వస్తారు?", "వర్గం V:", "te"),
])
def test_real_kvs_category_answers_are_localized_and_grounded(real_kvs_notice, question, expected, language):
    answer = answer_notice(question, real_kvs_notice)
    assert answer.answer_language == language
    assert answer.answer_text.startswith(expected)
    assert answer.citations and {item.page_number for item in answer.citations} == {2}


def test_real_profile_eligibility_is_not_confident_from_initial_subset(real_notice):
    response = answer_notice("Am I eligible?", real_notice,
                             {"marks_percentage": 60, "annual_family_income_inr": 300000})
    assert response.eligibility_result != "PASS"


def test_scert_eligibility_fields_are_stable_across_five_fresh_analyses():
    from demo.pipeline import profile_field_specs
    path = Path("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf")
    payload = path.read_bytes()
    snapshots = []
    for _ in range(5):
        result = initial_analysis(payload, path.name)
        specs = profile_field_specs(result.analysis.eligibility)
        snapshots.append({
            "document_id": result.analysis.document_id,
            "fields": [
                (attribute, spec["kind"], tuple(spec["options"]), spec["required"],
                 tuple(spec["source_texts"]), tuple(spec["evidence_ids"]))
                for attribute, spec in specs.items()
            ],
        })
    assert len({snapshot["document_id"] for snapshot in snapshots}) == 1
    assert all(snapshot == snapshots[0] for snapshot in snapshots[1:])
    assert [field[0] for field in snapshots[0]["fields"]] == sorted(field[0] for field in snapshots[0]["fields"])


def test_scert_partial_failing_and_all_extracted_rules_profiles_are_conservative():
    from demo.pipeline import eligibility_outcome
    from demo.product import eligibility_display_state
    from services.nlp.semantic.canonical import iter_conditions
    path = Path("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf")
    result = initial_analysis(path.read_bytes(), path.name)
    evidence_ids = {span.evidence_id for span in result.analysis.evidence}
    conditions = list(iter_conditions(result.analysis.eligibility))
    assert conditions and all(set(condition.evidence_ids) <= evidence_ids for condition in conditions)

    assert eligibility_outcome({}, result.analysis)[0] == "UNKNOWN"
    assert eligibility_outcome({"marks_percentage": 60}, result.analysis)[0] == "UNKNOWN"
    assert eligibility_outcome({"marks_percentage": 40}, result.analysis)[0] == "FAIL"

    complete_extracted_profile = {
        "marks_percentage": 60, "current_class": 8, "current_school_type": "government",
        "previous_class": 7, "previous_school_type": "government",
        "annual_family_income_inr": 300000, "attempt_count": 0,
    }
    status, explanation = eligibility_outcome(complete_extracted_profile, result.analysis)
    assert status == "PASS"
    assert all(entry.evidence_ids for entry in explanation.conditions)
    # The extracted AST has no completeness certificate, so user-facing result stays UNKNOWN.
    assert eligibility_display_state(status, result, complete_extracted_profile) == "UNKNOWN"


def test_switching_real_notices_discards_profile_and_rule_widget_state():
    state = {}
    hindi = Path("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf")
    telugu = Path("datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf")
    from demo.product import session_analysis
    first, hit, _ = session_analysis(state, hindi.read_bytes(), hindi.name)
    assert not hit and first.analysis.eligibility is not None
    state["candidate_profile"] = {"marks_percentage": 60}
    state["eligibility-widget-old-rule-value-marks_percentage"] = 60
    cached, hit, _ = session_analysis(state, hindi.read_bytes(), hindi.name)
    assert hit and cached is first
    assert state["candidate_profile"] == {"marks_percentage": 60}

    second, hit, _ = session_analysis(state, telugu.read_bytes(), telugu.name)
    assert not hit and second.analysis.document_id != first.analysis.document_id
    assert "candidate_profile" not in state
    assert not any(key.startswith("eligibility-widget-") for key in state)
