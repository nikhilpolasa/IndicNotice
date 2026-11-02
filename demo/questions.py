"""Localized product answers over the unchanged, evidence-cited QA service."""
from demo.i18n import tr
from demo.product import eligibility_display_state
from services.nlp.qa import GroundedQAService
from services.nlp.qa.router import route_question
from services.nlp.qa.types import Answerability, QuestionIntent
from services.nlp.eligibility.evaluator import evaluate_eligibility
from indicnotice.schemas.eligibility import EvalStatus


def answer_notice(question, result, profile=None, *, language=None):
    response = GroundedQAService().answer(question, result.analysis, profile)
    lang = language or route_question(question).language
    response.answer_language = lang
    if response.abstained or not response.citations:
        response.answer_text = tr("not_stated_answer", lang)
        response.answerability = Answerability.UNANSWERABLE
        response.abstained = True
        return response
    field = response.structured_source_field or ""
    a = result.analysis
    if field.startswith("dates."):
        role = field.split(".", 1)[1]
        dates = [d for d in a.dates if d.date_type.value == role]
        response.answer_text = "\n".join(f'{tr(role, lang)}: {d.value or d.source_text or tr("missing", lang)}' + (f" {d.time}" if d.time else "") for d in dates)
        from services.nlp.qa.validation import citations_from_ids
        response.citations = citations_from_ids([eid for d in dates for eid in d.evidence_ids], a)
        if len(dates) > 1:
            response.answerability = Answerability.PARTIAL
            response.answer_text += "\n" + tr("source_answer", lang)
        if response.intent == QuestionIntent.VENUE:
            response.answer_text += f'\n{tr("venue", lang)}: {tr("missing", lang)}'
    elif field == "fees":
        lines = []
        for fee in a.fees:
            amount = tr("missing", lang) if fee.amount_inr is None else f"₹{fee.amount_inr:,.2f}"
            line = f"{tr(fee.fee_type, lang)}: {amount}"
            if fee.applies_to_category:
                line += f' · {tr("applies", lang)}: {fee.applies_to_category}'
            if fee.waived_for:
                line += f' · {tr("waived", lang)}: {fee.waived_for}'
            lines.append(line)
        response.answer_text = "\n".join(lines)
    elif field == "metadata.title":
        response.answer_text = f'{tr("title", lang)}: {a.metadata.title}'
    elif field == "metadata.issuing_authority":
        response.answer_text = f'{tr("authority", lang)}: {a.metadata.issuing_authority}'
    elif field == "required_documents":
        lines = []
        for document in a.required_documents:
            if document.applies_when is not None and profile is not None:
                status = evaluate_eligibility(profile, document.applies_when).overall
                if status in {EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE}:
                    continue
            label = tr(document.canonical_name, lang)
            line = f'{label} ({document.source_name}) · {tr(document.requirement_type.value, lang)}'
            if document.applies_when is not None and document.requirement_type.value != "conditional":
                line += f' · {tr("conditional", lang)}'
            if document.alternatives:
                line += f' · {tr("alternatives", lang)}: ' + ", ".join(tr(name, lang) for name in document.alternatives)
            lines.append(line)
        response.answer_text = tr("documents", lang) + ":\n" + "\n".join(lines)
    elif field == "links":
        # Preserve the QA service's programme-specific selection through citations.
        ids = {c.evidence_id for c in response.citations}
        links = [item.url for item in a.links if ids.intersection(item.evidence_ids) and item.url in response.answer_text]
        lines = [tr("link", lang) + ": " + ", ".join(links)] if links else []
        channels = list(dict.fromkeys(item.channel for item in a.actions
                                     if item.channel and ids.intersection(item.evidence_ids)))
        if channels:
            lines.append(tr("channel", lang) + ": " + ", ".join(tr(channel, lang) for channel in channels))
        if route_question(question).asks_date:
            deadlines = [d for d in a.dates if d.date_type.value == "application_deadline"]
            lines.append(tr("application_deadline", lang) + ": " + (
                ", ".join(d.value or d.source_text or tr("missing", lang) for d in deadlines)
                if deadlines else tr("missing", lang)))
        response.answer_text = "\n".join(lines) if lines else tr("source_answer", lang) + "\n" + "\n".join(c.text for c in response.citations)
    elif field == "eligibility" and a.eligibility is None:
        # Keep the explicit, source-grounded explanation that the notice refers
        # applicants to a separate guideline; there is no local rule set to score.
        return response
    elif field == "eligibility":
        state = eligibility_display_state(response.eligibility_result, result, dict(profile or {}))
        response.eligibility_result = state
        response.answer_text = tr(state, lang)
        if state == "UNKNOWN":
            response.answerability = Answerability.PARTIAL
            response.answer_text += "\n" + tr("partial", lang)
        if response.missing_information:
            response.answer_text += "\n" + ", ".join(tr(k, lang) for k in response.missing_information)
    elif field in {"application.mode", "admission.programme_scope", "admission.categories", "admission.preference"}:
        # These deterministic answers are already localized and supported by
        # the citations selected for the exact fact. Do not replace them with
        # unrelated nearby excerpts.
        return response
    else:
        # Free text remains a quotation. Do not pretend a passage is a translated,
        # fully supported answer to an arbitrary question.
        response.answer_text = tr("source_answer", lang) + "\n\n" + "\n\n".join(c.text for c in response.citations)
        response.answerability = Answerability.PARTIAL
    return response
