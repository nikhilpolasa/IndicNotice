"""
Top-level notice analysis schema for IndicNotice.

NoticeAnalysis is the canonical structured representation of a notice.
ALL downstream systems (eligibility checker, chatbot, reminders, Radar)
MUST consume this object rather than independently re-interpreting the PDF.

Schema version is stored on every analysis object so old objects can be
migrated when the schema evolves.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.dates import TypedDate
from indicnotice.schemas.fees import FeeItem
from indicnotice.schemas.benefits import BenefitItem
from indicnotice.schemas.documents_required import DocumentRequirement
from indicnotice.schemas.eligibility import ConditionGroup
from indicnotice.schemas.actions import ActionNode
from indicnotice.schemas.links import LinkItem
from indicnotice.schemas.common import ReviewState


CURRENT_SCHEMA_VERSION = "1.0"


class NoticeCategory(str, Enum):
    """Notice classification categories."""

    SCHOLARSHIP = "scholarship"
    EXAMINATION = "examination"
    ADMISSION = "admission"
    RECRUITMENT = "recruitment"
    OTHER = "other"


class NoticeMetadata(BaseModel):
    """
    Structured metadata about the issuing authority and notice identity.

    Every field is Optional because a notice may not state all of these
    values.  Missing information is represented as None — never invented.
    """

    title: str | None = Field(
        default=None,
        description="Full notice title as stated in the source.",
    )
    issuing_authority: str | None = Field(
        default=None,
        description="Name of the organization/department that issued the notice.",
    )
    notice_number: str | None = Field(
        default=None,
        description="Official notice/reference number, e.g. 'No. ABC/2024/001'.",
    )
    publication_date: str | None = Field(
        default=None,
        description=(
            "ISO 8601 date when the notice was published. "
            "Also represented as a TypedDate in the dates list."
        ),
    )
    source_url: str | None = Field(
        default=None,
        description="URL where this notice was originally found.",
    )
    academic_year: str | None = Field(
        default=None,
        description="Academic/financial year this notice pertains to, e.g. '2024-25'.",
    )
    issuing_authority_evidence_ids: list[str] = Field(default_factory=list)
    title_evidence_ids: list[str] = Field(default_factory=list)
    notice_number_evidence_ids: list[str] = Field(default_factory=list)
    publication_date_evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("publication_date")
    @classmethod
    def validate_publication_date(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("publication_date must be a valid ISO date") from exc
        return value


class AnalysisWarning(BaseModel):
    """A structured warning produced during extraction or validation."""

    code: str = Field(
        ...,
        description=(
            "Short machine-readable code, e.g. "
            "'missing_deadline', 'conflicting_dates', 'low_confidence_field'."
        ),
    )
    message: str = Field(
        ...,
        description="Human-readable warning message.",
    )
    severity: Literal["info", "warning", "error"] = Field(default="warning")
    field_path: str | None = Field(
        default=None,
        description="Dot-path to the field that triggered this warning.",
    )
    evidence_ids: list[str] = Field(default_factory=list)


class NoticeAnalysis(BaseModel):
    """
    The canonical top-level object representing a fully analyzed notice.

    This is the single source of truth that ALL downstream components consume.

    Lifecycle:
      1. Ingestion layer populates Document.
      2. Extraction layer populates NoticeAnalysis (this object).
      3. Validation layer adds AnalysisWarnings and updates review_state.
      4. Downstream systems (eligibility, chatbot, etc.) read this object.

    The `evidence` list holds all EvidenceSpan objects referenced by IDs
    throughout the rest of this object.  No inline evidence — always by ID.
    """

    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Schema version string for forward-compatibility.",
    )
    analysis_id: str = Field(
        ...,
        description="Unique ID for this analysis run.",
    )
    document_id: str = Field(
        ...,
        description="ID of the source Document this analysis was produced from.",
    )
    source_language: str | None = Field(
        default=None,
        description="Primary language code of the notice, e.g. 'te', 'hi', 'en'.",
    )
    category: NoticeCategory | None = Field(
        default=None,
        description="Classified notice category.",
    )
    category_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Classifier confidence for category.",
    )
    metadata: NoticeMetadata = Field(default_factory=NoticeMetadata)
    dates: list[TypedDate] = Field(
        default_factory=list,
        description="All typed dates extracted from the notice.",
    )
    fees: list[FeeItem] = Field(default_factory=list)
    benefits: list[BenefitItem] = Field(default_factory=list)
    required_documents: list[DocumentRequirement] = Field(default_factory=list)
    eligibility: ConditionGroup | None = Field(
        default=None,
        description=(
            "Root of the eligibility condition AST. "
            "None if no eligibility conditions were stated or could be parsed."
        ),
    )
    actions: list[ActionNode] = Field(
        default_factory=list,
        description="Ordered (by dependency) list of candidate actions.",
    )
    links: list[LinkItem] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description=(
            "All EvidenceSpan objects referenced by ID throughout this analysis. "
            "IDs in other fields must resolve to entries in this list."
        ),
    )
    warnings: list[AnalysisWarning] = Field(
        default_factory=list,
        description="Validation and extraction warnings.",
    )
    overall_review_state: ReviewState = Field(
        default=ReviewState.AUTO_EXTRACTED,
    )
    extractor_model: str | None = Field(
        default=None,
        description="Name/version of the model used for contextual extraction.",
    )
    extraction_timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp of when this analysis was produced.",
    )

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("schema_version must be a non-empty string.")
        normalized = v.strip()
        if normalized != CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version {normalized!r}; "
                f"expected {CURRENT_SCHEMA_VERSION!r}."
            )
        return normalized

    def get_evidence(self, evidence_id: str) -> EvidenceSpan | None:
        """Look up an EvidenceSpan by ID.  Returns None if not found."""
        for span in self.evidence:
            if span.evidence_id == evidence_id:
                return span
        return None

    def evidence_ids(self) -> set[str]:
        """Return all declared evidence IDs in this analysis."""
        return {span.evidence_id for span in self.evidence}


# Resolve all forward references (ConditionGroup inside DocumentRequirement,
# ActionNode, and directly on this model).
NoticeMetadata.model_rebuild()
NoticeAnalysis.model_rebuild()
