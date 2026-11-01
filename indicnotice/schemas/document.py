"""
Document and page-level schemas for IndicNotice.

These represent the output of the ingestion/OCR layer — a structured
view of the source PDF or image BEFORE any semantic extraction.

Downstream extractors receive a Document (or OCRDocument) as their
primary input and create EvidenceSpan references back into it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentBlock(BaseModel):
    """
    A layout block within a page — e.g. a paragraph, table cell, heading,
    or standalone text region returned by an OCR/layout backend.
    """

    block_id: str = Field(..., description="Unique block ID within the document.")
    page_number: int = Field(..., ge=1, description="1-indexed page number.")
    text: str = Field(..., description="Unicode-normalized text of this block.")
    original_ocr_text: str | None = Field(
        default=None,
        description="Raw OCR text before normalization. None for native-PDF.",
    )
    bbox: list[float] | None = Field(
        default=None,
        description="Bounding box [x0, y0, x1, y1] in page coordinates.",
    )
    block_type: str | None = Field(
        default=None,
        description="Layout type hint, e.g. 'paragraph', 'heading', 'table', 'list_item'.",
    )
    reading_order: int | None = Field(
        default=None,
        description="0-indexed reading order within the page.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Block-level OCR confidence (0–1).",
    )
    language_hint: str | None = Field(
        default=None,
        description="Detected script/language for this block, e.g. 'te', 'hi', 'en'.",
    )


class DocumentPage(BaseModel):
    """
    A single page within a document.

    `full_text` is the page-level concatenation of block texts in reading
    order and is the primary surface for regex/heuristic extraction.
    Individual EvidenceSpan objects reference character offsets into this
    string.
    """

    page_number: int = Field(..., ge=1)
    full_text: str = Field(
        ...,
        description="Full page text, blocks joined in reading order.",
    )
    blocks: list[DocumentBlock] = Field(default_factory=list)
    width_pt: float | None = Field(
        default=None,
        description="Page width in points (PDF) or pixels (image).",
    )
    height_pt: float | None = Field(
        default=None,
        description="Page height in points (PDF) or pixels (image).",
    )
    extraction_method: str = Field(
        default="unknown",
        description="How this page was extracted.",
    )
    avg_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mean block confidence for this page.",
    )


class Document(BaseModel):
    """
    The canonical in-memory representation of a source document as
    produced by the ingestion layer.

    This is the input to all downstream NLP components.
    A Document is immutable after ingestion — NLP components read it
    and produce separate NoticeAnalysis objects.
    """

    document_id: str = Field(..., description="Stable UUID or hash for this document.")
    source_path: str | None = Field(
        default=None,
        description="Original file path or URL. Redacted if sensitive.",
    )
    source_type: str = Field(
        default="unknown",
        description="'pdf', 'image', 'html', etc.",
    )
    pages: list[DocumentPage] = Field(default_factory=list)
    full_text: str = Field(
        default="",
        description="Full document text: pages joined with double newline.",
    )
    page_count: int = Field(default=0, ge=0)
    detected_language: str | None = Field(
        default=None,
        description="Primary detected language code, e.g. 'te', 'hi', 'en'.",
    )
    language_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    has_embedded_text: bool = Field(
        default=False,
        description="True if the PDF contained embedded Unicode text (not OCR needed).",
    )
    extraction_method: str = Field(default="unknown")
    ingestion_warnings: list[str] = Field(default_factory=list)


# Alias for the OCR-specific output — same structure, different label
OCRDocument = Document
