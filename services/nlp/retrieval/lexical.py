"""Interpretable in-memory BM25 retrieval over canonical EvidenceSpan units."""

from __future__ import annotations

from collections import Counter
import math
import unicodedata
from typing import Sequence

from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.retrieval.types import RetrievedEvidence


_STOPWORDS = {
    "a", "an", "the", "is", "are", "what", "which", "does", "do", "of", "to", "in", "for", "my",
    "क्या", "है", "की", "का", "के", "में", "कौन", "ఏమిటి", "ఏది", "లో", "కి", "యొక్క",
}
_CONCEPTS = (
    {"document", "documents", "certificate", "certificates", "दस्तावेज", "दस्तावेज़", "कागजात", "प्रमाण", "పత్రాలు", "పత్రాల", "సర్టిఫికెట్", "సర్టిఫికెట్లు"},
    {"income", "आय", "ఆదాయం", "ఆదాయ", "aay", "aadayam"},
    {"preference", "priority", "वरीयता", "प्राथमिकता", "ప్రాథమికత", "ప్రాధాన్యత"},
    {"application", "apply", "आवेदन", "दరఖాస్తు", "దరఖాస్తు"},
    {"deadline", "last", "closing", "अंतिम", "చివరి", "గడువు"},
    {"fee", "fees", "शुल्क", "फीस", "ఫీజు", "రుసుము"},
    {"document", "documents", "certificate", "दस्तावेज", "प्रमाण", "పత్రాలు", "సర్టిఫికెట్"},
    {"exam", "examination", "परीक्षा", "పరీక్ష"},
    {"interview", "साक्षात्कार", "ఇంటర్వ్యూ"},
    {"venue", "place", "location", "स्थान", "केंद्र", "వేదిక", "కేంద్రం"},
    {"eligibility", "eligible", "पात्रता", "योग्यता", "అర్హత"},
    {"income", "आय", "ఆదాయం"},
    {"marks", "percentage", "अंक", "प्रतिशत", "మార్కులు", "శాతం"},
    {"register", "registration", "पंजीकरण", "నమోదు"},
    {"preference", "priority", "वरीयता", "प्राथमिकता", "ప్రాధాన్యత"},
    {"admission", "प्रवेश", "ప్రవేశం", "అడ్మిషన్"},
    {"website", "portal", "link", "वेबसाइट", "लिंक", "వెబ్", "లింక్"},
)


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text).casefold()
    tokens: list[str] = []
    current: list[str] = []
    for character in normalized:
        if unicodedata.category(character)[0] in {"L", "M", "N"}:
            current.append(character)
        elif current:
            token = "".join(current)
            if token not in _STOPWORDS:
                tokens.append(token)
            current = []
    if current:
        token = "".join(current)
        if token not in _STOPWORDS:
            tokens.append(token)
    return tokens


def _expand(tokens: list[str]) -> set[str]:
    result = set(tokens)
    for concept in _CONCEPTS:
        if result & concept:
            result.update(concept)
    return result


class LexicalRetriever:
    method = "unicode-bm25-nlp5-v1"

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def retrieve(
        self,
        question: str,
        evidence: Sequence[EvidenceSpan],
        *,
        top_k: int = 5,
    ) -> list[RetrievedEvidence]:
        if top_k < 1 or not evidence:
            return []
        query = _expand(tokenize(question))
        if not query:
            return []
        documents = [tokenize(item.text) for item in evidence]
        average_length = sum(len(item) for item in documents) / max(len(documents), 1)
        document_frequency = {
            token: sum(token in set(document) for document in documents)
            for token in query
        }
        results: list[RetrievedEvidence] = []
        for span, tokens in zip(evidence, documents, strict=True):
            frequencies = Counter(tokens)
            score = 0.0
            for token in query:
                frequency = frequencies[token]
                if not frequency:
                    continue
                df = document_frequency[token]
                inverse_frequency = math.log(1.0 + (len(documents) - df + 0.5) / (df + 0.5))
                length_norm = 1.0 - self.b + self.b * len(tokens) / max(average_length, 1.0)
                score += inverse_frequency * (frequency * (self.k1 + 1.0)) / (frequency + self.k1 * length_norm)
            if score > 0.0:
                results.append(RetrievedEvidence(
                    evidence_id=span.evidence_id,
                    document_id=span.document_id,
                    page_number=span.page_number,
                    block_id=span.block_id,
                    text=span.text,
                    retrieval_score=score,
                    retrieval_method=self.method,
                ))
        results.sort(key=lambda item: (-item.retrieval_score, item.page_number, item.evidence_id))
        return results[:top_k]
