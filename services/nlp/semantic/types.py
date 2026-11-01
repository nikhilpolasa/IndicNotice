"""Internal, auditable NLP-4 semantic-candidate contracts.

These diagnostics are deliberately service-layer types.  Canonical facts still
leave the pipeline only as ``NoticeAnalysis`` schema version 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from indicnotice.schemas.actions import ActionNode
from indicnotice.schemas.documents_required import DocumentRequirement
from indicnotice.schemas.eligibility import ConditionGroup
from indicnotice.schemas.notice import NoticeAnalysis


class RejectionReason(str, Enum):
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    UNSUPPORTED_OPERATOR = "UNSUPPORTED_OPERATOR"
    UNSUPPORTED_ATTRIBUTE = "UNSUPPORTED_ATTRIBUTE"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    OTHER = "OTHER"


class CandidateOrigin(str, Enum):
    DETERMINISTIC = "deterministic"
    CONTEXTUAL = "contextual"


@dataclass(frozen=True, slots=True)
class GateDecision:
    claim_type: str
    field_path: str
    origin: CandidateOrigin
    promoted: bool
    evidence_ids: tuple[str, ...] = ()
    reason: RejectionReason | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticConflict:
    field_path: str
    deterministic_value: object
    contextual_value: object
    deterministic_evidence_ids: tuple[str, ...]
    contextual_evidence_ids: tuple[str, ...]
    resolution: str


@dataclass(frozen=True, slots=True)
class SemanticCandidates:
    eligibility: ConditionGroup | None = None
    required_documents: tuple[DocumentRequirement, ...] = ()
    actions: tuple[ActionNode, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticDiagnostics:
    method: str = "evidence-gated-semantic-nlp4-v1"
    decisions: tuple[GateDecision, ...] = ()
    conflicts: tuple[SemanticConflict, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def promoted_count(self) -> int:
        return sum(item.promoted for item in self.decisions)

    @property
    def rejected_count(self) -> int:
        return sum(not item.promoted for item in self.decisions)

    @property
    def rejection_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.decisions:
            if item.promoted or item.reason is None:
                continue
            counts[item.reason.value] = counts.get(item.reason.value, 0) + 1
        return counts


@dataclass(frozen=True, slots=True)
class SemanticExtractionResult:
    analysis: NoticeAnalysis
    diagnostics: SemanticDiagnostics
