"""Citation and protected-value validation for grounded QA."""

from __future__ import annotations

import re
from typing import Sequence

from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.qa.types import Citation
from services.nlp.retrieval.types import RetrievedEvidence


_URL = re.compile(r"https?://[^\s<>'\"]+", re.I)
_NUMBER = re.compile(r"(?<![\w])(?:₹|rs\.?\s*)?\d[\d,]*(?:\.\d+)?(?:\s*(?:%|percent|lakh|lac|crore|years?))?", re.I)


class CitationValidationError(ValueError):
    pass


class UnsupportedAnswerError(ValueError):
    pass


def citations_from_ids(
    evidence_ids: Sequence[str],
    analysis: NoticeAnalysis,
    *,
    allowed_ids: set[str] | None = None,
) -> list[Citation]:
    evidence_map = {item.evidence_id: item for item in analysis.evidence}
    result: list[Citation] = []
    for evidence_id in dict.fromkeys(evidence_ids):
        if allowed_ids is not None and evidence_id not in allowed_ids:
            raise CitationValidationError(f"Citation {evidence_id!r} was not in retrieved context.")
        span = evidence_map.get(evidence_id)
        if span is None:
            raise CitationValidationError(f"Citation {evidence_id!r} does not exist.")
        if span.document_id != analysis.document_id:
            raise CitationValidationError(f"Citation {evidence_id!r} belongs to another document.")
        result.append(Citation(
            evidence_id=span.evidence_id,
            page_number=span.page_number,
            block_id=span.block_id,
            text=span.text,
        ))
    return result


def unsupported_critical_tokens(answer: str, cited_text: str) -> list[str]:
    """Return answer URLs/numeric facts that do not occur in cited evidence."""
    source = cited_text.casefold().replace(",", "")
    unsupported: list[str] = []
    for token in _URL.findall(answer):
        if token.casefold().rstrip(".,)") not in source:
            unsupported.append(token)
    for token in _NUMBER.findall(answer):
        normalized = " ".join(token.casefold().replace(",", "").split()).rstrip(".,)")
        if normalized and normalized not in source:
            unsupported.append(token)
    return list(dict.fromkeys(unsupported))


def validate_generated_answer(
    answer: str,
    citation_ids: Sequence[str],
    retrieved: Sequence[RetrievedEvidence],
    analysis: NoticeAnalysis,
) -> list[Citation]:
    allowed = {item.evidence_id for item in retrieved}
    citations = citations_from_ids(citation_ids, analysis, allowed_ids=allowed)
    if answer.strip() and not citations:
        raise CitationValidationError("A factual generated answer requires at least one citation.")
    cited_text = "\n".join(item.text for item in citations)
    unsupported = unsupported_critical_tokens(answer, cited_text)
    if unsupported:
        raise UnsupportedAnswerError(f"Unsupported critical values: {unsupported}")
    return citations
