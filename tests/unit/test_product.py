"""Product workflow regressions using actual PDF parsing and extraction."""
from dataclasses import replace
from pathlib import Path
import time

import pymupdf
import pytest

from demo import product
from demo import product_app
from demo.i18n import COPY, LANGUAGES, tr
from demo.questions import answer_notice
from services.nlp.qa import QuestionIntent, route_question, Answerability
from services.nlp.retrieval import LexicalRetriever
from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.documents_required import RequirementType
from demo.pipeline import eligibility_outcome


def pdf_bytes(text="Admission Notice\nApplications must be submitted by 15 October 2026.\nNo application fee is required."):
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), text)
        return document.tobytes()


@pytest.fixture
def result():
    return product.initial_analysis(pdf_bytes(), "notice.pdf")


def test_initial_upload_is_real_native_and_has_cited_facts(result):
    assert result.mode == product.FAST_MODE
    assert all(route.method == "native_pdf" for route in result.ingestion.routes)
    assert result.analysis.dates[0].value == "2026-10-15"
    assert result.analysis.fees[0].amount_inr == 0
    assert result.analysis.dates[0].evidence_ids
    assert not Path(result.ingestion.document.source_path).exists()


def test_initial_analysis_does_not_depend_on_optional_model(monkeypatch):
    def unavailable(*args, **kwargs):
        pytest.fail("initial analysis must not call the optional model")
    monkeypatch.setattr(product.HTTPChatProvider, "complete", unavailable)
    actual = product.initial_analysis(pdf_bytes(), "no-model.pdf")
    assert actual.mode == product.FAST_MODE
    assert actual.analysis.dates and actual.analysis.dates[0].evidence_ids


def test_content_cache_and_session_isolation():
    first, second = {}, {}
    payload = pdf_bytes()
    result, hit, _ = product.session_analysis(first, payload, "one.pdf")
    assert not hit
    first["candidate_profile"] = {"age": 42}
    cached, hit, _ = product.session_analysis(first, payload, "renamed.pdf")
    assert hit and cached is result
    isolated, hit, _ = product.session_analysis(second, payload, "one.pdf")
    assert not hit and isolated is not result
    assert "candidate_profile" not in second
    product.session_analysis(first, pdf_bytes("Another notice with sufficient embedded native text."), "one.pdf")
    assert "candidate_profile" not in first


def test_analysis_cache_is_bound_to_the_fixed_pipeline_configuration(monkeypatch):
    payload = pdf_bytes()
    state = {}
    first, hit, _ = product.session_analysis(state, payload, "notice.pdf")
    assert not hit
    second, hit, _ = product.session_analysis(state, payload, "notice.pdf")
    assert hit and second is first
    monkeypatch.setattr(product, "INITIAL_ANALYSIS_CONFIG", "test-config-change")
    third, hit, _ = product.session_analysis(state, payload, "notice.pdf")
    assert not hit and third is not first


def test_invalid_upload_clears_previous_document(result):
    state = {"demo_result": result, "upload_digest": "old", "candidate_profile": {"age": 18}, "value-age": 18}
    with pytest.raises(ValueError):
        product.session_analysis(state, b"bad", "bad.pdf")
    assert not state


@pytest.mark.parametrize("question,intent", [
    ("Deadline kya hai?", QuestionIntent.DEADLINE),
    ("ఆఖరి deadline ఎప్పుడు?", QuestionIntent.DEADLINE),
    ("आखिरी तारीख क्या है?", QuestionIntent.DEADLINE),
    ("chivari tedi enti?", QuestionIntent.DEADLINE),
    ("fees kitni hai?", QuestionIntent.FEE),
    ("ఫీజు ఎంత?", QuestionIntent.FEE),
    ("कौन से दस्तावेज़ चाहिए?", QuestionIntent.DOCUMENTS),
    ("ఏ పత్రాలు కావాలి?", QuestionIntent.DOCUMENTS),
    ("शैक्षिक योग्यता क्या है?", QuestionIntent.QUALIFICATION),
])
def test_code_mixed_and_multilingual_intents(question, intent):
    assert route_question(question).intent == intent


@pytest.mark.parametrize("language,question", [
    ("en", "What is the application deadline?"),
    ("hi", "आवेदन की अंतिम तिथि क्या है?"),
    ("te", "దరఖాస్తు చివరి తేదీ ఏమిటి?"),
])
def test_cross_language_answers_over_english_pdf(result, language, question):
    answer = answer_notice(question, result, language=language)
    assert answer.answer_language == language
    assert "2026-10-15" in answer.answer_text
    assert tr("application_deadline", language) in answer.answer_text
    assert answer.citations and all(c.page_number == 1 for c in answer.citations)
    assert answer.answerability == Answerability.ANSWERABLE
    missing = answer_notice("What is the interview venue?", result, language=language)
    assert missing.abstained and not missing.citations
    assert missing.answer_text == tr("not_stated_answer", language)


@pytest.mark.parametrize("query,text", [
    ("ఆదాయం", "Annual family income must be below the stated limit."),
    ("income", "वार्षिक आय सीमा लागू है।"),
    ("प्राथमिकता", "Admission preference is based on transfer count."),
    ("documents", "అవసరమైన పత్రాలు సమర్పించాలి."),
])
def test_cross_lingual_evidence_retrieval(query, text):
    spans = [EvidenceSpan(evidence_id="e", document_id="d", page_number=2, text=text)]
    matches = LexicalRetriever().retrieve(query, spans)
    assert matches and matches[0].page_number == 2


@pytest.mark.parametrize("language", ["en", "hi", "te"])
def test_fee_answers_are_localized(result, language):
    answer = answer_notice("What is the fee?", result, language=language)
    assert tr("application_fee", language) in answer.answer_text
    assert "₹0.00" in answer.answer_text and answer.citations


def test_eligibility_preserves_failure_unknown_and_incomplete_pass(result):
    rule = Condition(condition_id="age", attribute="age", comparator=Comparator.GTE, value=18,
                     evidence_ids=result.analysis.dates[0].evidence_ids)
    analysis = result.analysis.model_copy(update={"eligibility": ConditionGroup(operator="AND", children=[rule])})
    result = replace(result, analysis=analysis)
    assert eligibility_outcome({}, analysis)[0] == "UNKNOWN"
    assert eligibility_outcome({"age": 12}, analysis)[0] == "FAIL"
    assert eligibility_outcome({"age": 25}, analysis)[0] == "PASS"
    response = answer_notice("Am I eligible?", result, {"age": 25})
    assert response.eligibility_result == "UNKNOWN"
    assert product.eligibility_display_state("PASS", result) == "UNKNOWN"


def test_positive_profile_result_never_claims_notice_wide_eligibility(result):
    tree = ConditionGroup(operator="AND", children=[
        Condition(condition_id="age", attribute="age", comparator=Comparator.GTE, value=18,
                  evidence_ids=result.analysis.dates[0].evidence_ids)
    ])
    advanced = replace(result, mode=product.ADVANCED_MODE,
                       analysis=result.analysis.model_copy(update={"eligibility": tree, "warnings": []}))
    assert eligibility_outcome({"age": 25}, advanced.analysis)[0] == "PASS"
    assert product.eligibility_display_state("PASS", advanced, {"age": 25}) == "UNKNOWN"


def test_advanced_failure_preserves_initial_result(result, monkeypatch):
    def failed(*args, **kwargs):
        raise RuntimeError("private internal provider failure")
    monkeypatch.setattr(product.HTTPChatProvider, "complete", failed)
    state = {"demo_result": result}
    with pytest.raises(RuntimeError):
        product.advanced_analysis(result)
    assert state["demo_result"] is result


def test_language_copy_and_no_public_debug_widgets():
    assert len(LANGUAGES) == 3
    assert all(len(values) == 3 and all(values) for values in COPY.values())
    source = Path("demo/product_app.py").read_text(encoding="utf-8")
    assert "st.json(" not in source and "st.code(" not in source
    assert "st.exception(" not in source


def test_native_initial_analysis_latency(result):
    started = time.perf_counter()
    product.initial_analysis(pdf_bytes(), "notice.pdf")
    assert time.perf_counter() - started < 10


@pytest.mark.parametrize("language", list(LANGUAGES))
def test_welcome_ui_renders_and_localizes(language, monkeypatch):
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    account = {"account_id": "test-account", "email": "student@example.test", "preferred_language": "en"}

    class Store:
        def get_profile(self, account_id):
            return {}

        def update_language(self, account_id, value):
            account["preferred_language"] = value

        def is_admin(self, account_id):
            return False

    monkeypatch.setattr(product_app, "_authenticated_account", lambda _st: account)
    monkeypatch.setattr(product_app, "_auth_store", Store)
    class Notifications:
        def __init__(self, _store):
            pass

        def unread_count(self, _account_id):
            return 0

    monkeypatch.setattr(product_app, "NotificationService", Notifications)
    app = AppTest.from_file(str(Path("demo/app.py").resolve())).run()
    app.selectbox[0].select(language).run()
    assert not app.exception
    assert app.header[0].value == tr("welcome", LANGUAGES[language])


def test_real_scanned_upload_uses_ocr_and_removes_page_images(monkeypatch):
    import io
    from PIL import Image, ImageDraw, ImageFont
    from services.nlp.ocr.tesseract import TesseractBackend
    from services.nlp.ingestion.errors import OCRBackendUnavailableError, OCRLanguageUnavailableError
    try:
        backend = TesseractBackend()
        backend._require_languages()
    except (OCRBackendUnavailableError, OCRLanguageUnavailableError) as error:
        pytest.skip(str(error))
    image = Image.new("RGB", (1800, 550), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except OSError:
        font = ImageFont.load_default(size=44)
    draw.multiline_text((80, 70), "Admission Notice\nApplication deadline: 15 October 2026\nNo application fee is required.", font=font, fill="black", spacing=28)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=900, height=275)
        page.insert_image(page.rect, stream=stream.getvalue())
        payload = pdf.tobytes()
    paths = []
    original = TesseractBackend.extract_page
    def track(self, image_path, *args, **kwargs):
        paths.append(Path(image_path))
        return original(self, image_path, *args, **kwargs)
    monkeypatch.setattr(TesseractBackend, "extract_page", track)
    result = product.initial_analysis(payload, "scanned.pdf")
    assert result.ingestion.routes[0].method == "tesseract"
    assert "2026" in result.ingestion.document.full_text
    assert result.analysis.dates and result.analysis.dates[0].evidence_ids
    assert paths and all(not p.exists() for p in paths)


def test_no_ocr_is_called_for_native_upload(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("OCR was called for a native-text PDF")
    monkeypatch.setattr(product.TesseractBackend, "extract_page", unexpected)
    product.initial_analysis(pdf_bytes(), "native.pdf")


@pytest.mark.parametrize("lang", ["en", "hi", "te"])
def test_document_answers_preserve_optional_and_conditional_rules(result, lang):
    from tests.unit.test_nlp5_qa import analysis
    result = replace(result, analysis=analysis())
    response = answer_notice("Which documents are required?", result, language=lang)
    assert tr("documents", lang) in response.answer_text
    assert tr("optional", lang) in response.answer_text
    assert "Aadhaar" in response.answer_text
    assert response.citations


def test_conditional_document_answer_does_not_repeat_its_requirement_label(result):
    from tests.unit.test_nlp5_qa import analysis
    notice = analysis()
    source_document = notice.required_documents[0].model_copy(update={
        "requirement_type": RequirementType.CONDITIONAL,
        "applies_when": ConditionGroup(
            group_id="conditional-doc-guard",
            operator="AND",
            children=[Condition(condition_id="is-sc", attribute="category", comparator=Comparator.EQ, value="SC")],
        ),
    })
    notice = notice.model_copy(update={"required_documents": [source_document]})
    response = answer_notice("What documents are required?", replace(result, analysis=notice), language="en")
    assert "Identity proof (Aadhaar) · Conditional" in response.answer_text
    assert "Conditional · Conditional" not in response.answer_text


def test_retrieval_is_presented_as_partial_source_text(result):
    from tests.unit.test_nlp5_qa import analysis
    result = replace(result, analysis=analysis())
    response = answer_notice("What is selection based on?", result, language="hi")
    assert response.answerability == Answerability.PARTIAL
    assert tr("source_answer", "hi") in response.answer_text
    assert response.citations


def test_expired_advanced_budget_never_sends_another_request(monkeypatch):
    from services.nlp.extraction.contextual.errors import ProviderTimeout
    from services.nlp.extraction.contextual.types import ModelRequest
    def unexpected(*args):
        pytest.fail("request made after deadline")
    provider = product.HTTPChatProvider(base_url="http://127.0.0.1:8080", model_id="local")
    monkeypatch.setattr(provider, "complete", unexpected)
    budget = product._BudgetProvider(provider, -1)
    with pytest.raises(ProviderTimeout):
        budget.complete(ModelRequest(({'role':'system','content':'test'},), {}, 5))


def test_background_review_is_session_owned_and_clear_discards_it(result, monkeypatch):
    from threading import Event
    started, release = Event(), Event()
    def review(notice):
        started.set()
        assert release.wait(3)
        return notice
    monkeypatch.setattr(product, "advanced_analysis", review)
    job = product.start_advanced(result)
    try:
        assert started.wait(1) and not job.done()
        state = {"demo_result": result, "advanced_job": job, "candidate_profile": {"age": 18}}
        product.clear_notice(state)
        assert not state
    finally:
        release.set()
    assert job.result(timeout=2) is result


@pytest.mark.parametrize("question,role", [
    ("What is the fee payment deadline?", "fee_payment_deadline"),
    ("ఫీజు చెల్లింపు గడువు ఎప్పుడు?", "fee_payment_deadline"),
    ("शुल्क की अंतिम तिथि क्या है?", "fee_payment_deadline"),
    ("When do applications open?", "application_open"),
    ("आवेदन कब शुरू होगा?", "application_open"),
])
def test_specific_date_questions_do_not_return_application_closing_date(question, role, result):
    assert route_question(question).date_role == role
    # These roles are absent from this upload: abstain rather than borrowing its deadline.
    response = answer_notice(question, result)
    assert response.abstained and "2026-10-15" not in response.answer_text


def test_production_skips_model_repairs_but_keeps_strict_evidence_gates():
    from tests.unit.test_nlp3_contextual import make_document, FakeProvider, encoded, empty_output
    from services.nlp.extraction.contextual import ContextualStructuredExtractor
    from services.nlp.extraction.contextual.context import evidence_from_document
    doc = make_document(["Recruitment Notice"])
    output = empty_output(category="recruitment", category_evidence_ids=["invented"])
    provider = FakeProvider([encoded(output)])
    result = ContextualStructuredExtractor(provider, max_repair_attempts=0).extract_with_evidence(doc, evidence_from_document(doc))
    assert len(provider.requests) == 1 and result.diagnostics.repair_count == 0
    assert result.analysis.category is None
    assert result.diagnostics.rejected_claims == 1
    assert any(w.code == "unsupported_model_claims_rejected" for w in result.analysis.warnings)


def test_compact_context_removes_only_redundant_block_ids_and_keeps_all_evidence():
    from tests.unit.test_nlp3_contextual import make_document
    from services.nlp.extraction.contextual.context import build_chunks, evidence_from_document
    doc = make_document(["Applications close on the stated date.", "Income certificate is required."])
    spans = evidence_from_document(doc)
    full = build_chunks(doc, spans, max_chars=5000)
    compact = build_chunks(doc, spans, max_chars=5000, compact=True)
    assert compact[0].evidence_aliases == full[0].evidence_aliases
    assert compact[0].evidence_ids == full[0].evidence_ids
    assert all(span.text in compact[0].text for span in spans)
    assert 'page="1"' in compact[0].text
    assert 'block=' not in compact[0].text
    assert len(compact[0].text) < len(full[0].text)


def test_production_output_limits_leave_research_schema_unchanged():
    from services.nlp.extraction.contextual.schema import response_schema
    research = response_schema()
    bounded = product.production_schema(research)
    assert bounded["properties"]["category_evidence_ids"]["maxItems"] == 0
    assert "maxItems" not in research["properties"]["category_evidence_ids"]
    assert bounded["properties"]["dates"]["items"]["properties"]["source_text"]["maxLength"] == 320
    assert "maxLength" not in research["properties"]["dates"]["items"]["properties"]["source_text"]
    assert bounded["properties"]["dates"]["maxItems"] == 0
    assert "maxItems" not in bounded["properties"]["required_documents"]
    assert "maxItems" not in bounded["properties"]["required_documents"]["items"]["properties"]["evidence_ids"]


def test_production_prompt_formats_and_applies_review_scope(result, monkeypatch):
    import json
    from tests.unit.test_nlp3_contextual import empty_output
    from services.nlp.extraction.contextual.types import ModelResponse
    requests = []
    def capture(self, request):
        requests.append(request)
        return ModelResponse(json.dumps(empty_output()), 0.01, 10, 10, "stop")
    monkeypatch.setattr(product.HTTPChatProvider, "complete", capture)
    reviewed = product.advanced_analysis(result)
    assert len(requests) == 1
    assert "Review only eligibility" in requests[0].messages[1]["content"]
    assert "15 October 2026" in requests[0].messages[1]["content"]
    assert requests[0].response_schema["properties"]["dates"]["maxItems"] == 0
    assert reviewed.contextual_diagnostics.prompt_version == "indicnotice-production-requirements-v1"


def test_explicit_english_applications_close_on_is_a_cited_deadline():
    result = product.initial_analysis(pdf_bytes("Admission Notice\nApplications close on 15 October 2026."), "notice.pdf")
    response = answer_notice("What is the deadline?", result)
    assert "2026-10-15" in response.answer_text and response.citations


@pytest.mark.parametrize("comparator", [Comparator.EXISTS, Comparator.NOT_EXISTS])
def test_unanswered_presence_is_unknown_and_explicit_absence_is_distinct(result, comparator):
    from demo.pipeline import profile_field_specs
    rule = Condition(condition_id="presence", attribute="prior_award", comparator=comparator,
                     value=None, evidence_ids=result.analysis.dates[0].evidence_ids)
    tree = ConditionGroup(operator="AND", children=[rule])
    result = replace(result, mode=product.ADVANCED_MODE,
                     analysis=result.analysis.model_copy(update={"eligibility":tree, "warnings":[]}))
    assert profile_field_specs(tree)["prior_award"]["kind"] == "presence"
    missing = answer_notice("Am I eligible?", result, {})
    assert missing.eligibility_result == "UNKNOWN"
    absent = answer_notice("Am I eligible?", result, {"prior_award":None})
    expected_rule_result = "PASS" if comparator == Comparator.NOT_EXISTS else "FAIL"
    assert eligibility_outcome({"prior_award": None}, result.analysis)[0] == expected_rule_result
    assert absent.eligibility_result == ("UNKNOWN" if expected_rule_result == "PASS" else "FAIL")


def test_presence_rule_does_not_replace_a_numeric_profile_field():
    from demo.pipeline import profile_field_specs
    tree = ConditionGroup(operator="AND", children=[
        Condition(condition_id="age", attribute="age", comparator=Comparator.GTE, value=18),
        Condition(condition_id="present", attribute="age", comparator=Comparator.EXISTS),
    ])
    assert profile_field_specs(tree)["age"]["kind"] == "number"
