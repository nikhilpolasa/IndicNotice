"""
Required-document schemas for IndicNotice.

The master plan requires the system to distinguish:
  - mandatory vs optional documents
  - category-specific documents
  - alternatives ("A or B")
  - documents for a sub-group only

The `applies_when` field links to the same ConditionGroup AST used for
eligibility, so document conditionality is expressed consistently.

Forward reference to ConditionGroup is resolved at the bottom of this module
via model_rebuild().
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from indicnotice.schemas.eligibility import ConditionGroup  # runtime import for model_rebuild
from indicnotice.schemas.common import ReviewState


class RequirementType(str, Enum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"  # applies_when clause is present


class DocumentRequirement(BaseModel):
    """
    A single document that a candidate may need to supply.

    `canonical_name` uses stable English identifiers, e.g.:
        income_certificate
        caste_certificate
        marksheet_10th
        passport_photo

    `source_name` is the verbatim name from the notice (may be in Telugu/Hindi).
    """

    doc_req_id: str = Field(
        default="",
        description="Unique ID for this requirement within the notice analysis.",
    )
    canonical_name: str = Field(
        ...,
        description="Normalized English identifier for this document type.",
    )
    source_name: str = Field(
        ...,
        description="Verbatim document name as found in the notice.",
    )
    requirement_type: RequirementType = Field(
        default=RequirementType.MANDATORY,
    )
    applies_when: "ConditionGroup | None" = Field(
        default=None,
        description=(
            "Condition under which this document is required. "
            "None means always required (for mandatory) or never (for optional with no condition)."
        ),
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description=(
            "List of canonical_names of documents that are acceptable alternatives "
            "to this one (e.g. 'A or B is acceptable'). Empty means no alternatives."
        ),
    )
    notes: str | None = Field(
        default=None,
        description="Additional note about format, attestation requirements, etc.",
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_state: ReviewState = Field(default=ReviewState.AUTO_EXTRACTED)

    model_config = {"arbitrary_types_allowed": True}


# Resolve forward references now that ConditionGroup is imported at runtime.
DocumentRequirement.model_rebuild()
