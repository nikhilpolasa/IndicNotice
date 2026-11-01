"""
Typed date schemas for IndicNotice.

The master plan explicitly requires distinguishing date roles rather than
using a single generic "deadline" field.

Design decisions:
- `value` is always ISO 8601 date string (YYYY-MM-DD) when present.
- `time` is HH:MM or HH:MM:SS in 24h format, stored separately.
  We never infer end-of-day time when only a date is stated (per spec).
- `precision` records what the source actually specifies.
- `review_state` uses the shared ReviewState literals.
"""

from __future__ import annotations

from datetime import date, time
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator
import re

from indicnotice.schemas.common import ReviewState


class DateRole(str, Enum):
    """Controlled vocabulary of date roles supported by the system."""

    PUBLICATION_DATE = "publication_date"
    APPLICATION_OPEN = "application_open"
    APPLICATION_DEADLINE = "application_deadline"
    FEE_PAYMENT_DEADLINE = "fee_payment_deadline"
    CORRECTION_START_DATE = "correction_start_date"
    CORRECTION_DEADLINE = "correction_deadline"
    ADMIT_CARD_DATE = "admit_card_date"
    EXAM_DATE = "exam_date"
    INTERVIEW_DATE = "interview_date"
    DOCUMENT_VERIFICATION_DATE = "document_verification_date"
    COUNSELING_DATE = "counseling_date"
    ELIGIBILITY_CUTOFF_DATE = "eligibility_cutoff_date"
    RESULT_DATE = "result_date"
    OTHER = "other"


class DatePrecision(str, Enum):
    """How precisely the date is stated in the source."""

    DATE_ONLY = "date_only"
    DATETIME = "datetime"  # date + confirmed time
    MONTH_ONLY = "month_only"
    YEAR_ONLY = "year_only"
    UNCERTAIN = "uncertain"


_ISO_DATE_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}(?::\d{2})?$")


class TypedDate(BaseModel):
    """
    A single date extracted from a notice, typed by its functional role.

    Multiple dates of different roles are stored in a list on NoticeAnalysis.
    If the source specifies both a date and a confirmed time, both are stored;
    `precision` will be DATETIME.  When only a date is given, `time` is None
    and `precision` is DATE_ONLY.

    Examples:
        publication_date: "2024-09-01"
        application_deadline: "2024-10-15", time: "17:00" (if stated)
        exam_date: "2024-11-20"
    """

    date_id: str = Field(
        default="",
        description="Unique identifier for this date entry, e.g. 'd1', 'd_app_deadline'.",
    )
    date_type: DateRole = Field(..., description="Functional role of this date.")
    value: str | None = Field(
        default=None,
        description="ISO 8601 date string (YYYY-MM-DD). None if not parseable.",
    )
    end_value: str | None = Field(
        default=None,
        description="ISO 8601 end date string (YYYY-MM-DD) for multi-day windows or ranges.",
    )
    time: str | None = Field(
        default=None,
        description=(
            "Confirmed time in HH:MM or HH:MM:SS (24h). "
            "MUST be None when the source does not state a time."
        ),
    )
    timezone: str | None = Field(
        default=None,
        description="IANA timezone name or offset, e.g. 'Asia/Kolkata', '+05:30'. None if not stated.",
    )
    source_text: str | None = Field(
        default=None,
        description="Verbatim date text from the notice, e.g. '15 అక్టోబర్ 2024'.",
    )
    precision: DatePrecision = Field(
        default=DatePrecision.UNCERTAIN,
        description="What level of precision the source provides.",
    )
    is_tentative: bool = Field(
        default=False,
        description="True if the notice marks this date as tentative or subject to change.",
    )
    mandatory: bool | None = Field(
        default=None,
        description="True if missing this deadline has a stated consequence.",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of EvidenceSpan objects supporting this date.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0–1).",
    )
    review_state: ReviewState = Field(
        default=ReviewState.AUTO_EXTRACTED,
        description="Review state: auto_extracted | needs_review | verified | rejected.",
    )

    @field_validator("value", "end_value")
    @classmethod
    def validate_iso_date(cls, v: str | None) -> str | None:
        if v is not None:
            if not _ISO_DATE_RE.match(v):
                raise ValueError(
                    f"value must be an ISO 8601 date (YYYY-MM-DD), got: {v!r}"
                )
            try:
                date.fromisoformat(v)
            except ValueError as exc:
                raise ValueError(f"value must be a valid calendar date, got: {v!r}") from exc
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str | None) -> str | None:
        if v is not None:
            if not _TIME_RE.match(v):
                raise ValueError(
                    f"time must be HH:MM or HH:MM:SS (24h), got: {v!r}"
                )
            try:
                time.fromisoformat(v)
            except ValueError as exc:
                raise ValueError(f"time must be a valid 24-hour time, got: {v!r}") from exc
        return v

    @model_validator(mode="after")
    def validate_range_and_precision(self) -> "TypedDate":
        if self.end_value is not None and self.value is None:
            raise ValueError("end_value requires a start value")
        if self.value is not None and self.end_value is not None:
            if date.fromisoformat(self.end_value) < date.fromisoformat(self.value):
                raise ValueError("end_value must not be earlier than value")
        if self.time is not None and self.value is None:
            raise ValueError("time requires a date value")
        if self.time is not None and self.precision != DatePrecision.DATETIME:
            raise ValueError("a stated time requires precision='datetime'")
        if self.precision == DatePrecision.DATETIME and self.time is None:
            raise ValueError("precision='datetime' requires a stated time")
        return self
