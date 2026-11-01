"""
Fee schema for IndicNotice.

Amounts are stored both as a normalized float (INR) and as the original
source text to preserve evidence without destroying the verbatim value.

Design decision: we normalize amounts to float INR internally for the
eligibility evaluator, but always keep source_text so downstream systems
can display the verbatim figure.

Indian numeric formats supported by the normalization utilities:
  "₹2.5 lakh"  -> 250000.0
  "₹2,50,000"  -> 250000.0
  "250000"     -> 250000.0
  "Rs. 500/-"  -> 500.0
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from indicnotice.schemas.common import ReviewState


class FeeItem(BaseModel):
    """A single fee line item extracted from a notice."""

    fee_id: str = Field(
        default="",
        description="Unique identifier for this fee item, e.g. 'fee_01'.",
    )
    fee_type: str = Field(
        ...,
        description=(
            "Controlled type: 'application_fee', 'examination_fee', "
            "'late_fee', 'processing_fee', 'other'."
        ),
    )
    amount_inr: float | None = Field(
        default=None,
        ge=0.0,
        description="Normalized fee amount in INR (Indian Rupees).",
    )
    source_text: str | None = Field(
        default=None,
        description="Verbatim fee text from the notice, e.g. '₹500/-'.",
    )
    applies_to_category: str | None = Field(
        default=None,
        description=(
            "Category this fee applies to, e.g. 'SC/ST', 'General', "
            "'OBC'. None means all candidates."
        ),
    )
    waived_for: str | None = Field(
        default=None,
        description="Category/group for which this fee is waived, if stated.",
    )
    payment_mode: str | None = Field(
        default=None,
        description="Mode of payment, e.g. 'online_netbanking', 'challan', 'demand_draft'.",
    )
    is_refundable: bool = Field(
        default=False,
        description="True if stated as refundable in the notice.",
    )
    payment_deadline_ref: str | None = Field(
        default=None,
        description="ID of the TypedDate with role fee_payment_deadline.",
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_state: ReviewState = Field(default=ReviewState.AUTO_EXTRACTED)
