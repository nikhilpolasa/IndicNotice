"""Schema-first, deterministic and evidence-cited notice QA."""

from __future__ import annotations

import re
from typing import Any, Mapping

from indicnotice.schemas.actions import ActionType, get_action_execution_order
from indicnotice.schemas.dates import DateRole, TypedDate
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup, EvalStatus
from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.eligibility.evaluator import CandidateProfile, evaluate_eligibility
from services.nlp.eligibility.explanations import explain_eligibility
from services.nlp.qa.generation import GroundedGenerationError, GroundedGenerator
from services.nlp.qa.router import route_question
from services.nlp.qa.types import AnswerMode, Answerability, QAResponse, QuestionIntent, QuestionRoute
from services.nlp.qa.validation import (
    CitationValidationError,
    UnsupportedAnswerError,
    citations_from_ids,
    validate_generated_answer,
)
from services.nlp.retrieval import LexicalRetriever
from services.nlp.semantic.canonical import iter_conditions


_TEXT = {
    "not_stated": {
        "en": "This information is not stated in this notice.",
        "hi": "यह जानकारी इस सूचना में नहीं दी गई है।",
        "te": "ఈ సమాచారం ఈ నోటీసులో పేర్కొనబడలేదు.",
    },
    "missing": {
        "en": "Eligibility cannot yet be determined. Missing information: {items}.",
        "hi": "पात्रता अभी निर्धारित नहीं की जा सकती। आवश्यक जानकारी: {items}।",
        "te": "అర్హతను ఇంకా నిర్ణయించలేము. అవసరమైన సమాచారం: {items}.",
    },
    "pass": {
        "en": "Based on the conditions stated in this notice, you appear to meet the evaluated requirements.",
        "hi": "इस सूचना में दी गई शर्तों के आधार पर, आप मूल्यांकित आवश्यकताओं को पूरा करते प्रतीत होते हैं।",
        "te": "ఈ నోటీసులో పేర్కొన్న షరతుల ఆధారంగా, మీరు పరిశీలించిన అవసరాలను తీర్చినట్లు కనిపిస్తోంది.",
    },
    "fail": {
        "en": "Based on the information provided, you do not meet one or more stated conditions.",
        "hi": "दी गई जानकारी के आधार पर, आप एक या अधिक बताई गई शर्तों को पूरा नहीं करते।",
        "te": "అందించిన సమాచారం ఆధారంగా, మీరు పేర్కొన్న ఒకటి లేదా అంతకంటే ఎక్కువ షరతులను తీర్చడం లేదు.",
    },
    "na": {
        "en": "The evaluated condition does not apply to the current profile.",
        "hi": "मूल्यांकित शर्त वर्तमान प्रोफ़ाइल पर लागू नहीं होती।",
        "te": "పరిశీలించిన షరతు ప్రస్తుత ప్రొఫైల్‌కు వర్తించదు.",
    },
}


def _localized(key: str, language: str, **values: object) -> str:
    return _TEXT[key].get(language, _TEXT[key]["en"]).format(**values)


def _date_label(value: TypedDate) -> str:
    result = value.value or value.source_text or "unknown"
    if value.time:
        result += f" {value.time}"
    return result


def _format_amount(value: float | None) -> str:
    if value is None:
        return "amount not stated"
    return f"₹{value:,.2f}".replace(",", "_").replace(".", ".").replace("_", ",").removesuffix(".00")


def _response(
    route: QuestionRoute,
    answer: str,
    mode: AnswerMode,
    answerability: Answerability,
    **kwargs: Any,
) -> QAResponse:
    return QAResponse(
        answer_text=answer,
        answer_mode=mode,
        answerability=answerability,
        intent=route.intent,
        answer_language=route.language,
        **kwargs,
    )


def _not_stated(route: QuestionRoute, *, warning: str | None = None) -> QAResponse:
    return _response(
        route,
        _localized("not_stated", route.language),
        AnswerMode.NOT_STATED,
        Answerability.UNANSWERABLE,
        abstained=True,
        warnings=[warning] if warning else [],
    )


def _missing_for_group(group: ConditionGroup | None, profile: Mapping[str, Any]) -> set[str]:
    if group is None:
        return set()
    if group.applies_when is not None:
        status = evaluate_eligibility(dict(profile), group.applies_when).overall
        if status in {EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE}:
            return set()
        if status == EvalStatus.UNKNOWN:
            return _missing_for_group(group.applies_when, profile)
    missing: set[str] = set()
    for child in group.children:
        if isinstance(child, ConditionGroup):
            missing.update(_missing_for_group(child, profile))
            continue
        if child.applies_when is not None:
            status = evaluate_eligibility(dict(profile), child.applies_when).overall
            if status in {EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE}:
                continue
            if status == EvalStatus.UNKNOWN:
                missing.update(_missing_for_group(child.applies_when, profile))
                continue
        attribute = "date_of_birth" if child.attribute == "age" and child.reference_date else child.attribute
        if child.comparator not in {Comparator.EXISTS, Comparator.NOT_EXISTS} and profile.get(attribute) is None:
            missing.add(attribute)
    return missing


class GroundedQAService:
    """Single-turn QA over one canonical NoticeAnalysis."""

    method = "schema-first-grounded-qa-nlp5-v1"

    def __init__(
        self,
        *,
        retriever: LexicalRetriever | None = None,
        generator: GroundedGenerator | None = None,
    ) -> None:
        self.retriever = retriever or LexicalRetriever()
        self.generator = generator

    def answer(
        self,
        question: str,
        analysis: NoticeAnalysis,
        candidate_profile: CandidateProfile | None = None,
    ) -> QAResponse:
        if not question.strip():
            route = QuestionRoute(intent=QuestionIntent.OTHER_NOTICE_QUESTION, language="en")
            return _response(route, "Question is empty.", AnswerMode.ERROR, Answerability.ERROR, abstained=True)
        route = route_question(question)
        handlers = {
            QuestionIntent.TITLE: self._title,
            QuestionIntent.DEADLINE: self._deadline,
            QuestionIntent.DATE: self._date,
            QuestionIntent.FEE: self._fee,
            QuestionIntent.DOCUMENTS: self._documents,
            QuestionIntent.AUTHORITY: self._authority,
            QuestionIntent.URL: self._url,
            QuestionIntent.ELIGIBILITY: self._eligibility,
            QuestionIntent.QUALIFICATION: self._qualification,
            QuestionIntent.PROCEDURE: self._procedure,
            QuestionIntent.ACTION: self._procedure,
            QuestionIntent.BENEFIT: self._benefit,
            QuestionIntent.VENUE: self._venue,
        }
        handler = handlers.get(route.intent)
        if handler is not None:
            return handler(route, question, analysis, candidate_profile)
        return self._retrieval_answer(route, question, analysis)

    def _deadline(self, route, question, analysis, profile) -> QAResponse:
        item = next((item for item in analysis.dates if item.date_type == DateRole.APPLICATION_DEADLINE), None)
        if item is None:
            return _not_stated(route)
        answer = {
            "en": f"Application deadline: {_date_label(item)}.",
            "hi": f"आवेदन की अंतिम तिथि: {_date_label(item)}।",
            "te": f"దరఖాస్తు చివరి తేదీ: {_date_label(item)}.",
        }[route.language]
        return _response(route, answer, AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(item.evidence_ids, analysis), structured_source_field="dates.application_deadline")

    def _date(self, route, question, analysis, profile) -> QAResponse:
        if route.date_role is not None:
            role = DateRole(route.date_role)
        elif re.search(r"exam|परीक्षा|పరీక్ష", question, re.I):
            role = DateRole.EXAM_DATE
        elif re.search(r"interview|साक्षात्कार|ఇంటర్వ్యూ", question, re.I):
            role = DateRole.INTERVIEW_DATE
        else:
            role = DateRole.APPLICATION_DEADLINE
        item = next((item for item in analysis.dates if item.date_type == role), None)
        if item is None:
            return _not_stated(route)
        return _response(route, f"{role.value.replace('_', ' ').title()}: {_date_label(item)}.", AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(item.evidence_ids, analysis), structured_source_field=f"dates.{role.value}")

    def _fee(self, route, question, analysis, profile) -> QAResponse:
        if not analysis.fees:
            return _not_stated(route)
        lines = []
        ids: list[str] = []
        for item in analysis.fees:
            applicability = f" ({item.applies_to_category})" if item.applies_to_category else ""
            waiver = f"; waived for {item.waived_for}" if item.waived_for else ""
            lines.append(f"{item.fee_type.replace('_', ' ')}: {_format_amount(item.amount_inr)}{applicability}{waiver}")
            ids.extend(item.evidence_ids)
        return _response(route, "; ".join(lines) + ".", AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(ids, analysis), structured_source_field="fees")

    def _documents(self, route, question, analysis, profile) -> QAResponse:
        if not analysis.required_documents:
            return _not_stated(route)
        lines, ids = [], []
        supplied = dict(profile or {})
        for item in analysis.required_documents:
            guard_status = None
            if item.applies_when is not None and profile is not None:
                guard_status = evaluate_eligibility(supplied, item.applies_when).overall
                if guard_status in {EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE}:
                    continue
            label = item.source_name
            if item.requirement_type.value == "optional":
                label += " (optional)"
            elif item.requirement_type.value == "conditional" or item.applies_when is not None:
                label += " (conditional" + (": applicability unknown" if guard_status == EvalStatus.UNKNOWN else "") + ")"
            if item.alternatives:
                label += " (alternatives: " + " OR ".join(item.alternatives) + ")"
            lines.append(label)
            ids.extend(item.evidence_ids)
        if not lines:
            return _not_stated(route)
        prefix = {"en": "Documents: ", "hi": "दस्तावेज: ", "te": "పత్రాలు: "}[route.language]
        return _response(route, prefix + "; ".join(lines) + ".", AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(ids, analysis), structured_source_field="required_documents")

    def _title(self, route, question, analysis, profile) -> QAResponse:
        value = analysis.metadata.title
        if not value:
            return _not_stated(route)
        return _response(
            route,
            f"Notice title: {value}",
            AnswerMode.STRUCTURED_FACT,
            Answerability.ANSWERABLE,
            citations=citations_from_ids(analysis.metadata.title_evidence_ids, analysis),
            structured_source_field="metadata.title",
        )

    def _authority(self, route, question, analysis, profile) -> QAResponse:
        value = analysis.metadata.issuing_authority
        if not value:
            return _not_stated(route)
        return _response(route, f"Issuing authority: {value}.", AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(analysis.metadata.issuing_authority_evidence_ids, analysis), structured_source_field="metadata.issuing_authority")

    def _url(self, route, question, analysis, profile) -> QAResponse:
        application_actions = [
            item for item in analysis.actions
            if item.action_type in {ActionType.REGISTER, ActionType.SUBMIT_APPLICATION}
        ]
        candidates = [
            item for item in analysis.links
            if item.link_type in {"application_portal", "registration"}
            or any(action.url_ref == item.url for action in application_actions)
        ]
        if not candidates:
            candidates = [item for item in analysis.links if item.link_type == "other"]
        question_scope = None
        if re.search(r"\bbalvatika(?:[- ]?iii|[- ]?3)?\b", question, re.I):
            question_scope = "balvatika"
        elif re.search(r"\bclass\s*(?:i|1)\b", question, re.I):
            question_scope = "class-1"
        scoped = [
            item for item in candidates
            if question_scope is not None
            and item.description
            and (
                question_scope in item.description.casefold()
                or (question_scope == "class-1" and re.search(r"\bclass\s*[- ]?(?:i|1)\b", item.description, re.I))
            )
        ]
        if scoped:
            candidates = scoped
        channels = list(dict.fromkeys(
            item.channel for item in application_actions if item.channel
        ))
        deadline = next(
            (item for item in analysis.dates if item.date_type == DateRole.APPLICATION_DEADLINE),
            None,
        )
        if not candidates and not channels:
            return _not_stated(route)
        parts: list[str] = []
        ids: list[str] = []
        if route.asks_date:
            if deadline is not None:
                parts.append(f"Application deadline: {_date_label(deadline)}.")
                ids.extend(deadline.evidence_ids)
            else:
                parts.append("The application deadline is not stated in this notice.")
        if channels:
            parts.append("Application channel: " + ", ".join(value.replace("_", " ") for value in channels) + ".")
            ids.extend(eid for item in application_actions for eid in item.evidence_ids)
        if candidates:
            if len(candidates) == 1:
                parts.append(f"Application link: {candidates[0].url}")
            else:
                labelled = [f"{(item.description or 'programme-specific portal')}: {item.url}" for item in candidates]
                parts.append("Programme-specific application links: " + "; ".join(labelled))
            ids.extend(eid for item in candidates for eid in item.evidence_ids)
        answerability = Answerability.PARTIAL if route.asks_date and deadline is None else Answerability.ANSWERABLE
        mode = AnswerMode.PARTIALLY_DETERMINABLE if answerability == Answerability.PARTIAL else AnswerMode.STRUCTURED_FACT
        return _response(route, " ".join(parts), mode, answerability, citations=citations_from_ids(ids, analysis), structured_source_field="links")

    def _eligibility(self, route, question, analysis, profile) -> QAResponse:
        if analysis.eligibility is None:
            return _not_stated(route)
        supplied = dict(profile or {})
        explanation = explain_eligibility(supplied, analysis.eligibility, analysis.evidence)
        missing = (
            sorted(_missing_for_group(analysis.eligibility, supplied))
            if explanation.overall == EvalStatus.UNKNOWN
            else []
        )
        if explanation.overall == EvalStatus.PASS:
            answer = _localized("pass", route.language)
        elif explanation.overall == EvalStatus.FAIL:
            answer = _localized("fail", route.language)
        elif explanation.overall == EvalStatus.NOT_APPLICABLE:
            answer = _localized("na", route.language)
        elif missing:
            answer = _localized("missing", route.language, items=", ".join(missing))
        else:
            answer = _localized("not_stated", route.language)
        condition_items = [
            {
                "condition_id": item.condition_id,
                "requirement": item.requirement,
                "candidate_value": item.candidate_value,
                "computed_value": item.computed_value,
                "status": item.status.value,
                "reason": item.reason,
                "evidence_ids": list(item.evidence_ids),
                "source_pages": list(item.source_pages),
            }
            for item in explanation.conditions
        ]
        ids = [eid for item in explanation.conditions for eid in item.evidence_ids]
        answerability = Answerability.PARTIAL if explanation.overall == EvalStatus.UNKNOWN else Answerability.ANSWERABLE
        return _response(route, answer, AnswerMode.ELIGIBILITY_RESULT, answerability, citations=citations_from_ids(ids, analysis), structured_source_field="eligibility", eligibility_result=explanation.overall.value, condition_explanations=condition_items, missing_information=missing)

    def _qualification(self, route, question, analysis, profile) -> QAResponse:
        conditions = [item for item in iter_conditions(analysis.eligibility) if item.attribute in {"education_level", "course", "qualification"}]
        if not conditions:
            return _not_stated(route)
        values = [str(item.value) for item in conditions]
        ids = [eid for item in conditions for eid in item.evidence_ids]
        return _response(route, "Required qualification: " + " OR ".join(dict.fromkeys(values)) + ".", AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(ids, analysis), structured_source_field="eligibility.qualification")

    def _procedure(self, route, question, analysis, profile) -> QAResponse:
        if not analysis.actions:
            return _not_stated(route)
        try:
            ordered = get_action_execution_order(analysis.actions)
        except ValueError as exc:
            return _response(route, "The action sequence is invalid and requires review.", AnswerMode.ERROR, Answerability.ERROR, abstained=True, warnings=[str(exc)])
        application_question = bool(re.search(r"apply|application|आवेदन|దరఖాస్తు", question, re.I))
        if application_question:
            allowed = {
                ActionType.OBTAIN_DOCUMENT,
                ActionType.REGISTER,
                ActionType.PAY_FEE,
                ActionType.UPLOAD_DOCUMENT,
                ActionType.SUBMIT_APPLICATION,
            }
            ordered = [item for item in ordered if item.action_type in allowed]
        supplied = dict(profile or {})
        applicable = []
        for item in ordered:
            if item.applies_when is not None and profile is not None:
                status = evaluate_eligibility(supplied, item.applies_when).overall
                if status in {EvalStatus.FAIL, EvalStatus.NOT_APPLICABLE}:
                    continue
            applicable.append(item)
        if not applicable:
            return _not_stated(route)
        lines, ids = [], []
        for index, item in enumerate(applicable, 1):
            qualifiers = []
            if item.is_optional:
                qualifiers.append("optional")
            if item.applies_when is not None:
                qualifiers.append("conditional")
            suffix = f" ({', '.join(qualifiers)})" if qualifiers else ""
            lines.append(f"{index}. {item.description}{suffix}")
            ids.extend(item.evidence_ids)
        return _response(route, " ".join(lines), AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(ids, analysis), structured_source_field="actions")

    def _benefit(self, route, question, analysis, profile) -> QAResponse:
        if not analysis.benefits:
            return _not_stated(route)
        ids = [eid for item in analysis.benefits for eid in item.evidence_ids]
        answer = "; ".join(item.description or item.benefit_type for item in analysis.benefits)
        return _response(route, answer, AnswerMode.STRUCTURED_FACT, Answerability.ANSWERABLE, citations=citations_from_ids(ids, analysis), structured_source_field="benefits")

    def _venue(self, route, question, analysis, profile) -> QAResponse:
        date_item = None
        if re.search(r"exam|परीक्षा|పరీక్ష", question, re.I):
            date_item = next((item for item in analysis.dates if item.date_type == DateRole.EXAM_DATE), None)
        elif re.search(r"interview|साक्षात्कार|ఇంటర్వ్యూ", question, re.I):
            date_item = next((item for item in analysis.dates if item.date_type == DateRole.INTERVIEW_DATE), None)
        retrieved = self.retriever.retrieve(question, analysis.evidence, top_k=5)
        venue = next((item for item in retrieved if re.search(r"venue|स्थान|केंद्र|वేదిక|కేంద్రం", item.text, re.I)), None)
        if venue is not None:
            ids = [venue.evidence_id] + (date_item.evidence_ids if date_item else [])
            answer = (f"Date: {_date_label(date_item)}. " if date_item else "") + f"Venue information: {venue.text}"
            return _response(route, answer, AnswerMode.EVIDENCE_RETRIEVAL, Answerability.ANSWERABLE, citations=citations_from_ids(ids, analysis), retrieval_method=self.retriever.method)
        if date_item is not None:
            answer = f"Exam date: {_date_label(date_item)}. The venue is not stated in this notice."
            return _response(route, answer, AnswerMode.PARTIALLY_DETERMINABLE, Answerability.PARTIAL, citations=citations_from_ids(date_item.evidence_ids, analysis), structured_source_field=f"dates.{date_item.date_type.value}", abstained=False, retrieval_method=self.retriever.method)
        return _not_stated(route)

    def _retrieval_answer(self, route, question, analysis) -> QAResponse:
        retrieved = self.retriever.retrieve(question, analysis.evidence, top_k=5)
        if not retrieved:
            return _not_stated(route)
        if self.generator is None:
            selected = retrieved[:3]
            answer = "Relevant notice text: " + " ".join(item.text for item in selected)
            return _response(route, answer, AnswerMode.EVIDENCE_RETRIEVAL, Answerability.ANSWERABLE, citations=citations_from_ids([item.evidence_id for item in selected], analysis), retrieval_method=self.retriever.method)
        try:
            output = self.generator.generate(question, retrieved)
            if output.abstained or not output.answer_text.strip():
                return _not_stated(route)
            citations = validate_generated_answer(output.answer_text, output.citation_ids, retrieved, analysis)
        except (GroundedGenerationError, CitationValidationError, UnsupportedAnswerError) as exc:
            return _not_stated(route, warning=f"Grounded generation rejected: {exc}")
        return _response(route, output.answer_text, AnswerMode.EVIDENCE_RETRIEVAL, Answerability.ANSWERABLE, citations=citations, retrieval_method=f"{self.retriever.method}+{self.generator.prompt_version}")
