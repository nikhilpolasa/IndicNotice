"""Shared enums used across canonical IndicNotice schemas."""

from enum import Enum


class ReviewState(str, Enum):
    """Human-review lifecycle for extracted canonical values."""

    AUTO_EXTRACTED = "auto_extracted"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
