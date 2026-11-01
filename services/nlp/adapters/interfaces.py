"""
Model/backend adapter interfaces for IndicNotice.

Every model-dependent component must use one of these Protocol interfaces.
This allows backend models to be swapped without touching business logic.

IMPORTANT: An adapter is NOT considered functional until at least one
real inference smoke test has succeeded.  Mock adapters used for unit
testing must be clearly labelled as stubs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from indicnotice.schemas.document import Document
from indicnotice.schemas.notice import NoticeAnalysis


# ---------------------------------------------------------------------------
# OCR / Ingestion
# ---------------------------------------------------------------------------

@runtime_checkable
class OCRBackend(Protocol):
    """
    Adapter for document ingestion and text extraction.

    Implementations:
      - NativePDFBackend   (PyMuPDF, NLP-1)
      - IndicOCRBackend    (primary Indic OCR, NLP-1)
      - PaddleOCRBackend   (fallback, NLP-1)
      - TesseractBackend   (baseline, NLP-1)
      - StubOCRBackend     (unit-test stub only)
    """

    def extract(self, document_path: str) -> Document:
        """
        Extract text and layout from a document file.

        Parameters
        ----------
        document_path: path to a PDF or image file.

        Returns
        -------
        Document with populated pages, blocks, and full_text.
        """
        ...


# ---------------------------------------------------------------------------
# Language identification
# ---------------------------------------------------------------------------

@runtime_checkable
class LanguageDetector(Protocol):
    """
    Adapter for language/script detection.

    Implementations:
      - ScriptHeuristicDetector  (rule-based, NLP-1, CPU-only)
      - IndicLIDDetector         (IndicLID model, NLP-1, optional)
    """

    def detect(self, text: str) -> dict[str, float]:
        """
        Detect the language(s) of input text.

        Returns
        -------
        dict mapping language code to confidence score, e.g.:
          {"te": 0.92, "hi": 0.05, "en": 0.03}
        """
        ...

    def detect_primary(self, text: str) -> tuple[str, float]:
        """
        Return the single most likely language code and confidence.

        Returns
        -------
        (language_code, confidence), e.g. ("te", 0.92)
        """
        ...


# ---------------------------------------------------------------------------
# Structured extraction
# ---------------------------------------------------------------------------

@runtime_checkable
class StructuredExtractor(Protocol):
    """
    Adapter for semantic structured extraction.

    Implementations:
      - RegexBaselineExtractor  (deterministic, NLP-2)
      - LLMExtractor            (contextual, NLP-3, requires model config)
    """

    def extract(self, doc: Document) -> NoticeAnalysis:
        """
        Extract structured information from a parsed document.

        The returned NoticeAnalysis must be schema-valid.
        The extractor must NOT invent values — use None/[] for missing fields.
        """
        ...


# ---------------------------------------------------------------------------
# Embedding / Retrieval
# ---------------------------------------------------------------------------

@runtime_checkable
class EmbeddingBackend(Protocol):
    """
    Adapter for text embedding (used in retrieval-augmented QA, NLP-5).

    Implementations:
      - BGEM3Backend          (BGE-M3, preferred)
      - MultilingualE5Backend (fallback)
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors, one per input text."""
        ...


# ---------------------------------------------------------------------------
# Question answering
# ---------------------------------------------------------------------------

@runtime_checkable
class QAProvider(Protocol):
    """
    Adapter for grounded question answering (NLP-5).

    The QA provider must answer ONLY from the canonical NoticeAnalysis
    and/or retrieved evidence spans — never from model world knowledge.
    """

    def answer(self, question: str, analysis: NoticeAnalysis) -> dict:
        """
        Answer a question grounded in the given analysis.

        Must return a dict conforming to the QAResponse schema.
        """
        ...


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

@runtime_checkable
class Translator(Protocol):
    """
    Adapter for Indic translation (NLP-7, after core is evaluated).

    The translator must NOT alter canonical normalized values:
    dates, fees, percentages, age limits, URLs, reference numbers.
    """

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Translate text, preserving all canonical values."""
        ...
