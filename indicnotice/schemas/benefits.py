"""
Benefit schema for IndicNotice (scholarships, stipends, seat allotments, etc.).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from indicnotice.schemas.common import ReviewState


class BenefitItem(BaseModel):
    """A single benefit offered by the notice (e.g. scholarship amount)."""

    benefit_id: str = Field(
        default="",
        description="Unique identifier for this benefit item, e.g. 'ben_01'.",
    )
    benefit_type: str = Field(
        ...,
        description=(
            "Controlled type: 'scholarship_amount', 'stipend', "
            "'seat_allotment', 'fee_reimbursement', 'other'."
        ),
    )
    amount_inr: float | None = Field(default=None, ge=0.0)
    description: str | None = Field(default=None)
    source_text: str | None = Field(default=None)
    applies_to: str | None = Field(
        default=None,
        description="Scope of this benefit, e.g. 'SC/ST students'.",
    )
    frequency: str | None = Field(
        default=None,
        description="'annual', 'monthly', 'one_time', etc.",
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_state: ReviewState = Field(default=ReviewState.AUTO_EXTRACTED)
