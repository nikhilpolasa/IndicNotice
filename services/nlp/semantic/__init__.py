"""NLP-4 evidence-gated eligibility and action semantics."""

from services.nlp.semantic.canonical import canonical_condition, canonical_group
from services.nlp.semantic.extractor import EvidenceGatedSemanticExtractor
from services.nlp.semantic.relaxations import DeltaRelaxation, apply_age_exemption, resolve_age_delta
from services.nlp.semantic.rules import SemanticRuleExtractor
from services.nlp.semantic.types import (
    CandidateOrigin,
    GateDecision,
    RejectionReason,
    SemanticConflict,
    SemanticDiagnostics,
    SemanticExtractionResult,
)

__all__ = [
    "CandidateOrigin",
    "DeltaRelaxation",
    "EvidenceGatedSemanticExtractor",
    "GateDecision",
    "RejectionReason",
    "SemanticConflict",
    "SemanticDiagnostics",
    "SemanticExtractionResult",
    "SemanticRuleExtractor",
    "apply_age_exemption",
    "canonical_condition",
    "canonical_group",
    "resolve_age_delta",
]
