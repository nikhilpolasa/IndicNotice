"""Verified-only QA, citation, abstention and retrieval metrics for NLP-5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
import unicodedata
from typing import Mapping, Sequence

from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.qa.types import Answerability, QAResponse, QuestionIntent
from services.nlp.qa.validation import unsupported_critical_tokens
from services.nlp.retrieval.types import RetrievedEvidence


def _tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", value).casefold()
    return re.findall(r"[^\W_]+", normalized, re.UNICODE)


def normalized_answer(value: str) -> str:
    return " ".join(_tokens(value))


_DATE_PATTERN = re.compile(
    r"(?<!\d)(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4})(?!\d)"
)


def normalized_exact_match(predicted: str, expected: str) -> float:
    if normalized_answer(predicted) == normalized_answer(expected):
        return 1.0
    predicted_date = normalize_date_answer(predicted)
    expected_date = normalize_date_answer(expected)
    if predicted_date is None or predicted_date != expected_date:
        return 0.0
    return float(
        normalized_answer(_DATE_PATTERN.sub(" date ", predicted))
        == normalized_answer(_DATE_PATTERN.sub(" date ", expected))
    )


def token_f1(predicted: str, expected: str) -> float:
    from collections import Counter

    pred, gold = Counter(_tokens(predicted)), Counter(_tokens(expected))
    if not pred and not gold:
        return 1.0
    overlap = sum((pred & gold).values())
    precision = overlap / sum(pred.values()) if pred else 0.0
    recall = overlap / sum(gold.values()) if gold else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def normalize_date_answer(value: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)", value)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return None
    match = re.search(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)", value)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()
        except ValueError:
            return None
    return None


def citation_validity(response: QAResponse, analysis: NoticeAnalysis) -> float:
    if not response.citations:
        return 1.0 if response.abstained else 0.0
    valid = {
        item.evidence_id
        for item in analysis.evidence
        if item.document_id == analysis.document_id
    }
    return sum(item.evidence_id in valid for item in response.citations) / len(response.citations)


def citation_semantic_support(response: QAResponse, analysis: NoticeAnalysis) -> float:
    """Check answer-to-evidence semantics separately from reference validity."""
    if not response.citations:
        return 1.0 if response.abstained else 0.0
    cited_text = "\n".join(item.text for item in response.citations)
    if unsupported_critical_tokens(response.answer_text, cited_text):
        return 0.0
    if response.intent == QuestionIntent.URL:
        urls = re.findall(r"https?://[^\s<>'\"]+", response.answer_text, re.I)
        relation = re.search(r"apply|application|registration|portal|आवेदन|पंजीकरण|దరఖాస్తు|నమోదు", cited_text, re.I)
        return float(bool(urls) and bool(relation))
    if response.intent == QuestionIntent.DOCUMENTS:
        relation = re.search(r"must|required|attach|upload|submit|अनिवार्य|आवश्यक|अपलोड|जमा|తప్పనిసరి|అప్.?లోడ్|సమర్పించ", cited_text, re.I)
        concrete = any(item.source_name.casefold() in cited_text.casefold() for item in analysis.required_documents)
        return float(bool(relation) and concrete)
    if response.intent == QuestionIntent.FEE:
        return float(bool(re.search(r"fee|charge|शुल्क|फीस|ఫీజు|రుసుము", cited_text, re.I)))
    if response.intent == QuestionIntent.TITLE:
        return float(bool(analysis.metadata.title and analysis.metadata.title.casefold() in cited_text.casefold()))
    return 1.0


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    recall_at_k: float
    reciprocal_rank: float


def evaluate_retrieval(
    retrieved: Sequence[RetrievedEvidence] | Sequence[str],
    relevant_evidence_ids: set[str],
    *,
    k: int = 5,
) -> RetrievalMetrics:
    ids = [item if isinstance(item, str) else item.evidence_id for item in retrieved[:k]]
    if not relevant_evidence_ids:
        return RetrievalMetrics(1.0 if not ids else 0.0, 0.0)
    recall = len(set(ids) & relevant_evidence_ids) / len(relevant_evidence_ids)
    first = next((index for index, item in enumerate(ids, 1) if item in relevant_evidence_ids), None)
    return RetrievalMetrics(recall, 1.0 / first if first else 0.0)


@dataclass(frozen=True, slots=True)
class QAMetrics:
    verified_items: int
    answerability_accuracy: float | None
    exact_match: float | None
    token_f1: float | None
    citation_validity: float | None
    citation_support_accuracy: float | None
    unsupported_answer_rate: float | None
    abstention_accuracy: float | None
    eligibility_decision_accuracy: float | None
    missing_information_accuracy: float | None


def evaluate_qa(
    predictions: Mapping[str, QAResponse],
    annotations: Sequence[dict],
    analyses: Mapping[str, NoticeAnalysis],
) -> QAMetrics:
    verified = [item for item in annotations if item.get("verification_state") == "VERIFIED"]
    if not verified:
        return QAMetrics(0, None, None, None, None, None, None, None, None, None)
    answerability, exact, f1, validity, support = [], [], [], [], []
    unsupported, abstention, eligibility, missing = [], [], [], []
    for item in verified:
        prediction = predictions[item["qa_id"]]
        expected_answerability = item["expected_answerability"]
        answerability.append(prediction.answerability.value == expected_answerability)
        expected_text = item.get("expected_answer_text", item.get("candidate_answer"))
        if expected_text is not None:
            exact.append(normalized_exact_match(prediction.answer_text, expected_text))
            f1.append(token_f1(prediction.answer_text, expected_text))
        analysis = analyses[item["document_id"]]
        validity.append(citation_validity(prediction, analysis))
        expected_citations = set(item.get("expected_evidence_ids", []))
        acceptable_groups = [set(group) for group in item.get("acceptable_evidence_groups", [])]
        if expected_citations and not acceptable_groups:
            acceptable_groups = [expected_citations]
        if acceptable_groups:
            predicted_citations = {citation.evidence_id for citation in prediction.citations}
            support.append(float(bool(predicted_citations) and any(predicted_citations <= group for group in acceptable_groups)))
        is_unanswerable = expected_answerability == Answerability.UNANSWERABLE.value
        if is_unanswerable:
            unsupported.append(float(not prediction.abstained))
            abstention.append(float(prediction.abstained))
        elif acceptable_groups and prediction.answer_mode.value == "EVIDENCE_RETRIEVAL":
            predicted_citations = {citation.evidence_id for citation in prediction.citations}
            unsupported.append(float(not predicted_citations or not any(predicted_citations <= group for group in acceptable_groups)))
        expected_eligibility = item.get("expected_eligibility_result")
        if expected_eligibility is not None:
            eligibility.append(float(prediction.eligibility_result == expected_eligibility))
        expected_missing = item.get("expected_missing_information")
        if expected_missing is not None:
            missing.append(float(set(prediction.missing_information) == set(expected_missing)))

    mean = lambda values: sum(values) / len(values) if values else None
    return QAMetrics(
        verified_items=len(verified),
        answerability_accuracy=mean(answerability),
        exact_match=mean(exact),
        token_f1=mean(f1),
        citation_validity=mean(validity),
        citation_support_accuracy=mean(support),
        unsupported_answer_rate=mean(unsupported),
        abstention_accuracy=mean(abstention),
        eligibility_decision_accuracy=mean(eligibility),
        missing_information_accuracy=mean(missing),
    )
