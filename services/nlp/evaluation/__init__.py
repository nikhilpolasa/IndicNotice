"""NLP-1 extraction evaluation utilities."""

from services.nlp.evaluation.ocr_metrics import character_error_rate, word_error_rate

__all__ = ["character_error_rate", "word_error_rate"]
"""Deterministic evaluation utilities."""

from services.nlp.evaluation.extraction_metrics import (
    CorpusEvaluationReport,
    EvaluationReport,
    FieldError,
    FieldMetrics,
    aggregate_reports,
    evaluate_extraction,
)
from services.nlp.evaluation.contextual_metrics import GroundingMetrics, grounding_metrics
from services.nlp.evaluation.semantic_metrics import (
    ActionSemanticMetrics,
    EligibilitySemanticMetrics,
    evaluate_action_semantics,
    evaluate_eligibility_semantics,
)
from services.nlp.evaluation.qa_metrics import (
    QAMetrics,
    RetrievalMetrics,
    citation_validity,
    evaluate_qa,
    evaluate_retrieval,
    normalized_exact_match,
    token_f1,
)

__all__ = [
    "CorpusEvaluationReport",
    "EvaluationReport",
    "FieldError",
    "FieldMetrics",
    "aggregate_reports",
    "evaluate_extraction",
    "GroundingMetrics",
    "grounding_metrics",
    "ActionSemanticMetrics",
    "EligibilitySemanticMetrics",
    "evaluate_action_semantics",
    "evaluate_eligibility_semantics",
    "QAMetrics",
    "RetrievalMetrics",
    "citation_validity",
    "evaluate_qa",
    "evaluate_retrieval",
    "normalized_exact_match",
    "token_f1",
]
