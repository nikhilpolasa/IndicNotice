"""
Evidence model for IndicNotice.

Every critical extracted value (dates, fees, eligibility conditions,
required documents, authority, action requirements) MUST reference one
or more EvidenceSpan IDs so it can be traced back to its original
location in the source document.

Design decisions:
- `bbox` uses PDF/image coordinate convention: [x0, y0, x1, y1]
- `char_start` / `char_end` are Unicode character offsets within page-level text,
  not the full-document text, so they are always small and unambiguous.
- `confidence` is 0.0–1.0; None means the backend did not report it.
- `extraction_method` is a controlled string, not an enum, so new OCR
  backends can be added without touching this schema.
"""

from __future__ import annotations

import math
from pydantic import BaseModel, Field, field_validator, model_validator


ExtractionMethod = str


class EvidenceSpan(BaseModel):
    """
    A single evidence reference pointing to a specific text region inside
    the source document.

    An EvidenceSpan is the unit of provenance for every critical extracted
    value.  When multiple spans together support a single extracted field,
    the field carries a list of evidence_ids that resolve to multiple
    EvidenceSpan objects.
    """

    evidence_id: str = Field(
        ...,
        description="Unique identifier for this evidence span, e.g. 'ev_001'.",
    )
    document_id: str = Field(
        ...,
        description="ID of the parent Document this span belongs to.",
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="1-indexed page number within the document.",
    )
    text: str = Field(
        ...,
        description="The verbatim source text of this span (Unicode-normalized).",
    )
    original_ocr_text: str | None = Field(
        default=None,
        description=(
            "Raw OCR text before any post-processing/normalization. "
            "None for native-PDF extraction."
        ),
    )
    bbox: list[float] | None = Field(
        default=None,
        description=(
            "Bounding box [x0, y0, x1, y1] in page-coordinate units "
            "(points for PDF, pixels for images). None if unavailable."
        ),
    )
    block_id: str | None = Field(
        default=None,
        description="Layout block identifier assigned by the OCR/extraction backend.",
    )
    char_start: int | None = Field(
        default=None,
        ge=0,
        description="Character offset of span start within the page-level extracted text.",
    )
    char_end: int | None = Field(
        default=None,
        ge=0,
        description="Character offset of span end (exclusive) within the page-level text.",
    )
    section_heading: str | None = Field(
        default=None,
        description="Heading or title of the section containing this span, e.g. 'Para 4: Educational Qualifications'.",
    )
    table_id: str | None = Field(
        default=None,
        description="Identifier of the table containing this span, if extracted from tabular layout.",
    )
    row_index: int | None = Field(
        default=None,
        ge=0,
        description="0-indexed row index if extracted from a table cell.",
    )
    col_index: int | None = Field(
        default=None,
        ge=0,
        description="0-indexed column index if extracted from a table cell.",
    )
    header_text: str | None = Field(
        default=None,
        description="Associated column/row header text if extracted from a table cell.",
    )
    language: str | None = Field(
        default=None,
        description="Language code if detected or known for this span, e.g. 'te', 'hi', 'en'.",
    )
    extraction_method: ExtractionMethod = Field(
        default="unknown",
        description="How this text was obtained.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="OCR or extraction confidence score (0–1). None if not reported.",
    )

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: list[float] | None) -> list[float] | None:
        if v is not None:
            if len(v) != 4:
                raise ValueError("bbox must have exactly 4 elements [x0, y0, x1, y1]")
            if not all(math.isfinite(coordinate) for coordinate in v):
                raise ValueError("bbox coordinates must be finite numbers")
            if v[0] > v[2] or v[1] > v[3]:
                raise ValueError(
                    "bbox must satisfy x0 <= x2 and y0 <= y3 "
                    f"(got {v})"
                )
        return v

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceSpan":
        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end < self.char_start
        ):
            raise ValueError("char_end must be greater than or equal to char_start")
        return self
