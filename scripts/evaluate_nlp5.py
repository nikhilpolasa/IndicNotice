"""Execute deterministic NLP-5 QA over the real Hindi/Telugu NLP-4 outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import date
import argparse
import json
from pathlib import Path
from typing import Any

from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.evaluation.qa_metrics import citation_validity, evaluate_qa
from services.nlp.qa import GroundedQAService


def records_by_document_id(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index every report record without collapsing notices that share a language."""
    records: dict[str, dict[str, Any]] = {}
    for item in source["documents"]:
        document_id = item["document_id"]
        if document_id in records:
            raise ValueError(f"duplicate document_id in NLP-4 report: {document_id}")
        records[document_id] = item
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="reports/nlp4_real_evaluation.json", help="NLP-4 evaluation report")
    parser.add_argument("--output", default="reports/nlp5_real_qa.json", help="Destination report")
    args = parser.parse_args()

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = records_by_document_id(source)
    analyses = {
        document_id: NoticeAnalysis.model_validate(record["nlp4_analysis"])
        for document_id, record in records.items()
    }
    language_documents: dict[str, list[str]] = {}
    for document_id, record in records.items():
        language_documents.setdefault(record["language"], []).append(document_id)
    selected_documents = {
        language: document_ids[0]
        for language, document_ids in language_documents.items()
    }
    service = GroundedQAService()
    cases = [
        ("hi-structured", "hi", "आवेदन की अंतिम तिथि क्या है?", None),
        ("hi-retrieval", "hi", "What annual family income limit is stated?", None),
        ("hi-unanswerable", "hi", "What is the interview venue?", None),
        ("te-structured", "te", "దరఖాస్తు చివరి తేదీ ఏమిటి?", None),
        ("te-retrieval", "te", "What is admission preference based on?", None),
        ("te-unanswerable", "te", "పరీక్ష వేదిక ఎక్కడ ఉంది?", None),
        ("hi-eligibility", "hi", "Am I eligible?", {"marks_percentage": 60, "annual_family_income_inr": 300000}),
        ("hi-eligibility-missing", "hi", "What information is missing to determine my eligibility?", {"marks_percentage": 60}),
    ]
    outputs: list[dict[str, Any]] = []
    for case_id, language, question, profile in cases:
        document_id = selected_documents[language]
        analysis = analyses[document_id]
        response = service.answer(question, analysis, profile)
        retrieved = service.retriever.retrieve(question, analysis.evidence, top_k=5)
        outputs.append({
            "case_id": case_id,
            "document_id": document_id,
            "notice_language": language,
            "question": question,
            "candidate_profile": profile,
            "response": response.model_dump(mode="json"),
            "citation_validity": citation_validity(response, analysis),
            "retrieval": [item.model_dump(mode="json") for item in retrieved],
        })

    annotations = json.loads(Path("datasets/annotations/nlp5/v1/qa_examples.json").read_text(encoding="utf-8"))
    verification = Counter(item["verification_state"] for item in annotations)
    languages = Counter(item["question_language"] for item in annotations)
    answerability = Counter(item["expected_answerability"] for item in annotations)
    not_scored = evaluate_qa({}, [], {})
    payload = {
        "milestone": "NLP-5",
        "run_date": date.today().isoformat(),
        "method": service.method,
        "retrieval_method": service.retriever.method,
        "generator": {
            "status": "NOT_RUN",
            "reason": "Structured/extractive QA satisfies the real smoke run; Qwen QA generation was not marked tested without a separate real inference.",
            "validation_available": ["retrieved-context-only", "citation subset", "document membership", "critical numeric and URL support"],
        },
        "annotation_set": {
            "items": len(annotations),
            "verification_states": dict(verification),
            "question_languages": dict(languages),
            "answerability_candidates": dict(answerability),
            "scored_gold_items": 0,
        },
        "qa_metrics": {
            **asdict(not_scored),
            "status": "NOT_SCORED",
            "reason": "All 30 items require human verification.",
        },
        "real_smoke": outputs,
        "real_smoke_summary": {
            "cases": len(outputs),
            "valid_citation_cases": sum(item["citation_validity"] == 1.0 for item in outputs),
            "abstentions": sum(item["response"]["abstained"] for item in outputs),
            "modes": dict(Counter(item["response"]["answer_mode"] for item in outputs)),
        },
        "baselines": {
            "A_structured_lookup_only": "Implemented and exercised for canonical fields.",
            "B_lexical_retrieval_extractive": "Implemented and exercised with Unicode BM25 scores.",
            "proposed_schema_retrieval_optional_generation": "Implemented; real smoke used deterministic/extractive path, optional generation not run.",
        },
        "limitations": [
            "The QA review set is not human-verified and produces no quality metric.",
            "Lexical concept expansion is bounded and cross-lingual recall remains limited.",
            "The real smoke set has two notices and is not a benchmark.",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": output.as_posix(), **payload["real_smoke_summary"], "annotations": payload["annotation_set"]}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
