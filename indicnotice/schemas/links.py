"""Link item schema for IndicNotice."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class LinkItem(BaseModel):
    """A URL or web reference extracted from the notice."""

    url: str = Field(..., description="The extracted URL string.")
    link_type: str = Field(
        default="other",
        description=(
            "Controlled type: 'application_portal', 'notification_pdf', "
            "'payment_gateway', 'results_page', 'other'."
        ),
    )
    description: str | None = Field(
        default=None,
        description="Context describing what this URL points to.",
    )
    suspicious: bool = Field(
        default=False,
        description=(
            "True if this URL pattern appears suspicious (non-gov domain for "
            "payment, unusual characters, etc.)."
        ),
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or any(
            char.isspace() for char in value
        ):
            raise ValueError("url must be an absolute HTTP(S) URL")
        return value
