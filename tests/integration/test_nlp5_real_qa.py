"""Fast real-document QA integration over recorded canonical NLP-4 analyses."""

import json
from pathlib import Path

from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.qa import AnswerMode, GroundedQAService


def _analyses():
    payload = json.loads(Path("reports/nlp4_real_evaluation.json").read_text(encoding="utf-8"))
    return {
        item["language"]: NoticeAnalysis.model_validate(item["nlp4_analysis"])
        for item in payload["documents"]
    }


def test_real_hindi_structured_eligibility_and_abstention():
    hindi = _analyses()["hi"]
    service = GroundedQAService()
    deadline = service.answer("आवेदन की अंतिम तिथि क्या है?", hindi)
    eligibility = service.answer(
        "Am I eligible?", hindi,
        {"marks_percentage": 60, "annual_family_income_inr": 300000},
    )
    missing = service.answer("What is the interview venue?", hindi)
    assert deadline.answer_mode == AnswerMode.STRUCTURED_FACT and deadline.citations
    assert eligibility.eligibility_result == "PASS" and eligibility.citations
    assert missing.answer_mode == AnswerMode.NOT_STATED and missing.abstained


def test_real_telugu_structured_retrieval_and_abstention():
    telugu = _analyses()["te"]
    service = GroundedQAService()
    deadline = service.answer("దరఖాస్తు చివరి తేదీ ఏమిటి?", telugu)
    retrieval = service.answer("What is admission preference based on?", telugu)
    missing = service.answer("పరీక్ష వేదిక ఎక్కడ ఉంది?", telugu)
    assert deadline.answer_mode == AnswerMode.STRUCTURED_FACT and deadline.citations
    assert retrieval.answer_mode == AnswerMode.EVIDENCE_RETRIEVAL and retrieval.citations
    assert missing.answer_mode == AnswerMode.NOT_STATED and missing.abstained
