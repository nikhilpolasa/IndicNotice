"""Run NLP-4 on real Hindi/Telugu fixtures using recorded genuine NLP-3 candidates.

No model inference is hidden here: contextual candidates come from the
checkpointed NLP-3 real evaluation.  Re-run ``evaluate_nlp3.py`` first when a
fresh Qwen inference is required.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from datetime import date
from enum import Enum
import json
from pathlib import Path
from typing import Any

from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.evaluation import aggregate_reports, evaluate_extraction
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.ingestion.router import DocumentIngestor
from services.nlp.semantic import EvidenceGatedSemanticExtractor


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nlp3-report", default="reports/nlp3_real_evaluation.json")
    parser.add_argument("--output", default="reports/nlp4_real_evaluation.json")
    args = parser.parse_args()

    nlp3 = json.loads(Path(args.nlp3_report).read_text(encoding="utf-8"))
    annotations = json.loads(Path("datasets/annotations/nlp2/v1/annotations.json").read_text(encoding="utf-8"))
    by_fixture = {item["fixture_path"]: item for item in annotations}
    baseline_extractor = RegexBaselineExtractor()
    hybrid_extractor = EvidenceGatedSemanticExtractor()
    baseline_reports, contextual_reports, hybrid_reports = [], [], []
    documents: list[dict[str, Any]] = []

    for record in nlp3["documents"]:
        fixture = record["fixture_path"]
        ingestion = DocumentIngestor().ingest(Path(fixture))
        contextual = NoticeAnalysis.model_validate(record["nlp3"]["analysis"])
        baseline = baseline_extractor.extract_ingestion(ingestion).analysis
        hybrid = hybrid_extractor.extract_ingestion(ingestion, contextual)
        annotation = by_fixture[fixture]
        baseline_eval = evaluate_extraction(baseline, annotation)
        contextual_eval = evaluate_extraction(contextual, annotation)
        hybrid_eval = evaluate_extraction(hybrid.analysis, annotation)
        baseline_reports.append(baseline_eval)
        contextual_reports.append(contextual_eval)
        hybrid_reports.append(hybrid_eval)
        gate_diagnostics = _jsonable(hybrid.diagnostics)
        gate_diagnostics.update({
            "promoted_count": hybrid.diagnostics.promoted_count,
            "rejected_count": hybrid.diagnostics.rejected_count,
            "rejection_counts": hybrid.diagnostics.rejection_counts,
        })
        documents.append({
            "fixture_path": fixture,
            "language": annotation["language"],
            "document_id": ingestion.document.document_id,
            "nlp4_analysis": hybrid.analysis.model_dump(mode="json"),
            "verified_field_evaluation": _jsonable(hybrid_eval),
            "gate_diagnostics": gate_diagnostics,
            "eligibility_condition_count": sum(1 for _ in __import__("services.nlp.semantic.canonical", fromlist=["iter_conditions"]).iter_conditions(hybrid.analysis.eligibility)),
            "action_count": len(hybrid.analysis.actions),
        })

    payload = {
        "milestone": "NLP-4",
        "run_date": date.today().isoformat(),
        "method": "evidence-gated-semantic-nlp4-v1",
        "contextual_candidate_source": "Recorded genuine Qwen3-4B-Q4_K_M NLP-3 outputs; no new model inference in this run.",
        "verification_policy": "Only NLP-2 annotation fields marked verified_complete are scored. NLP-4 semantic review examples remain NEEDS_HUMAN_VERIFICATION and are not scored as gold.",
        "nlp3_finding_preserved": {
            "structured_output_repair": "every chunk required repair",
            "unsupported_claims": 66,
            "category_f1": {"nlp2": 1.0, "nlp3": 0.5},
            "fees_f1": {"nlp2": 1.0, "nlp3": 0.0},
            "post_validation_evidence_references": "116/116",
            "conclusion": "NLP-3 is structurally integrated but not quality-superior or production-ready."
        },
        "verified_comparison": {
            "nlp2": _jsonable(aggregate_reports(baseline_reports)),
            "nlp3": _jsonable(aggregate_reports(contextual_reports)),
            "nlp4": _jsonable(aggregate_reports(hybrid_reports)),
        },
        "semantic_evaluation": {
            "status": "NOT_SCORED",
            "reason": "The 20 dedicated semantic candidates need human verification.",
            "review_examples": 20,
            "eligibility_metrics_implemented": ["condition_precision", "condition_recall", "condition_f1", "attribute_accuracy", "operator_accuracy", "value_accuracy", "logical_structure_correctness", "guard_correctness", "reference_date_accuracy"],
            "action_metrics_implemented": ["action_precision", "action_recall", "action_f1", "dependency_edge_precision", "dependency_edge_recall", "dependency_edge_f1", "optional_accuracy", "conditional_accuracy", "deadline_accuracy"]
        },
        "ablation": {
            "contextual_alone_unsupported_claims_observed_in_nlp3": 66,
            "contextual_plus_nlp4_gate": {
                "contextual_promoted": sum(
                    decision["promoted"]
                    for item in documents for decision in item["gate_diagnostics"]["decisions"]
                    if decision["origin"] == "contextual"
                ),
                "contextual_rejected": sum(
                    not decision["promoted"]
                    for item in documents for decision in item["gate_diagnostics"]["decisions"]
                    if decision["origin"] == "contextual"
                ),
                "rejection_counts": {
                    reason: sum(
                        decision["reason"] == reason
                        for item in documents for decision in item["gate_diagnostics"]["decisions"]
                        if decision["origin"] == "contextual" and not decision["promoted"]
                    )
                    for reason in ["INVALID_EVIDENCE", "UNSUPPORTED_VALUE", "UNSUPPORTED_OPERATOR", "UNSUPPORTED_ATTRIBUTE", "SCHEMA_INVALID", "DUPLICATE", "CONFLICT", "OTHER"]
                }
            },
            "scope_note": "Counts are diagnostic candidate counts, not accuracy metrics."
        },
        "documents": documents,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": output.as_posix(),
        "documents": len(documents),
        "languages": [item["language"] for item in documents],
        "gate": payload["ablation"]["contextual_plus_nlp4_gate"],
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
