"""Debug-only sidecar types for the deterministic extractor.

These types do not compete with the canonical NoticeAnalysis schema.  They
explain how a canonical field was produced and are intentionally excluded
from downstream business contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from indicnotice.schemas.notice import NoticeAnalysis


@dataclass(frozen=True, slots=True)
class RuleTrace:
    rule_id: str
    field_path: str
    evidence_ids: tuple[str, ...]
    outcome: Literal["accepted", "rejected", "needs_review"] = "accepted"
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class BaselineExtractionResult:
    analysis: NoticeAnalysis
    traces: tuple[RuleTrace, ...]
