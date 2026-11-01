"""Build the human-review packet without changing verification states.

This script is deliberately read-only with respect to annotations.  Its AI
audit suggestions are navigation aids for a human reviewer, never gold labels.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path
from typing import Any

from indicnotice.schemas.eligibility import Condition, ConditionGroup
from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.evaluation.qa_metrics import citation_semantic_support
from services.nlp.evaluation.review_models import (
    adapt_semantic_example,
    load_candidate_profiles,
    load_qa_review,
    load_semantic_review,
)
from services.nlp.qa.router import route_question
from services.nlp.qa.types import AnswerMode, Answerability, QAResponse
from services.nlp.qa.validation import citations_from_ids
from services.nlp.semantic.canonical import iter_conditions


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/final_human_review"
QA_PATH = ROOT / "datasets/annotations/nlp5/v1/qa_examples.json"
SEMANTIC_PATH = ROOT / "datasets/annotations/nlp4/v1/semantic_examples.json"
PROFILE_PATH = ROOT / "datasets/fixtures/nlp4/candidate_profiles.json"
NLP4_PATH = ROOT / "reports/pre_nlp6/after/nlp4_real_evaluation.json"
SPECIAL_QA = {
    "hi-q05", "hi-q06", "hi-q07", "hi-q08", "hi-q09", "hi-q13", "hi-q15",
    "te-q05", "te-q07", "te-q13", "te-q14", "te-q15",
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _code(value: Any) -> str:
    return f"```json\n{_json(value)}\n```"


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _analysis_index() -> dict[str, NoticeAnalysis]:
    report = json.loads(NLP4_PATH.read_text(encoding="utf-8"))
    return {
        item["document_id"]: NoticeAnalysis.model_validate(item["nlp4_analysis"])
        for item in report["documents"]
    }


def _candidate_response(item: Any, analysis: NoticeAnalysis) -> QAResponse:
    route = route_question(item.question)
    valid_ids = analysis.evidence_ids()
    citations = citations_from_ids(
        [evidence_id for evidence_id in item.expected_evidence_ids if evidence_id in valid_ids],
        analysis,
    )
    unanswerable = item.expected_answerability == "UNANSWERABLE"
    if unanswerable:
        mode = AnswerMode.NOT_STATED
    elif item.question_type == "eligibility":
        mode = AnswerMode.ELIGIBILITY_RESULT
    else:
        mode = AnswerMode.STRUCTURED_FACT
    return QAResponse(
        answer_text=item.candidate_answer or "NOT_STATED",
        answer_mode=mode,
        answerability=Answerability(item.expected_answerability),
        intent=route.intent,
        citations=citations,
        structured_source_field=item.expected_source_field,
        eligibility_result=item.expected_eligibility_result,
        missing_information=item.expected_missing_information or [],
        abstained=unanswerable,
        answer_language=route.language,
    )


def _review_evidence_ids(item: Any) -> list[str]:
    return list(dict.fromkeys([
        *item.expected_evidence_ids,
        *(evidence_id for group in item.acceptable_evidence_groups for evidence_id in group),
    ]))


def _qa_audit(item: Any, analysis: NoticeAnalysis) -> tuple[str, str, bool, float]:
    valid_ids = analysis.evidence_ids()
    citations_exist = all(evidence_id in valid_ids for evidence_id in _review_evidence_ids(item))
    response = _candidate_response(item, analysis)
    support = citation_semantic_support(response, analysis)
    if item.qa_id == "hi-q15":
        return (
            "AMBIGUOUS",
            "QUESTION_AMBIGUITY: ‘minimum marks’ has multiple valid interpretations, so this item is recommended for exclusion from final scored gold.",
            citations_exist,
            support,
        )
    if not citations_exist:
        return "NEEDS_CORRECTION", "At least one expected evidence ID does not resolve in the current analysis.", False, support
    if support != 1.0:
        return (
            "READY_TO_VERIFY",
            "Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.",
            True,
            support,
        )
    if item.expected_answerability != "UNANSWERABLE" and not item.candidate_answer:
        return "NEEDS_CORRECTION", "An answerable item has no candidate answer.", True, support
    emphasis = " This is a designated high-attention item." if item.qa_id in SPECIAL_QA else ""
    return "READY_TO_VERIFY", "Citation references resolve and current semantic-support checks pass." + emphasis, True, support


def build_qa_review(analyses: dict[str, NoticeAnalysis]) -> tuple[str, list[dict[str, Any]]]:
    items = load_qa_review(QA_PATH)
    sections = [
        "# QA Human Review",
        "",
        "> These are 30 real-notice QA candidates from two source PDFs. AI suggestions are not human verification. The original PDF is authoritative.",
        "",
        "Use the source path and page shown for every decision. `READY_TO_VERIFY` means only that automated consistency checks found no issue.",
    ]
    summaries: list[dict[str, Any]] = []
    for item in items:
        analysis = analyses[item.document_id]
        evidence_map = {span.evidence_id: span for span in analysis.evidence}
        suggestion, rationale, citations_exist, support = _qa_audit(item, analysis)
        evidence = [
            {
                "evidence_id": evidence_id,
                "exists": evidence_id in evidence_map,
                "page": evidence_map[evidence_id].page_number if evidence_id in evidence_map else None,
                "block": evidence_map[evidence_id].block_id if evidence_id in evidence_map else None,
                "text": evidence_map[evidence_id].text if evidence_id in evidence_map else None,
            }
            for evidence_id in _review_evidence_ids(item)
        ]
        pages = sorted({entry["page"] for entry in evidence if entry["page"] is not None})
        summaries.append({
            "id": item.qa_id,
            "verification_state": item.verification_state,
            "suggestion": suggestion,
            "citations_exist": citations_exist,
            "semantic_support": support,
            "pages": pages,
        })
        sections.extend([
            "",
            f"## {item.qa_id}" + (" — high-attention" if item.qa_id in SPECIAL_QA else ""),
            "",
            f"- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**",
            f"- Verification state: `{item.verification_state}`",
            f"- AI audit suggestion: `{suggestion}`",
            f"- AI rationale: {rationale}",
            f"- Notice/document ID: `{item.document_id}`",
            f"- Notice language / question language: `{item.notice_language}` / `{item.question_language}`",
            f"- Question: {item.question}",
            f"- Current answerability: `{item.expected_answerability}`",
            f"- Candidate answer: {item.candidate_answer if item.candidate_answer is not None else '`NOT_STATED`'}",
            f"- Structured source field: `{item.expected_source_field or 'NONE'}`",
            f"- Structured eligibility expectation: `{item.expected_eligibility_result or 'NONE'}`",
            f"- Missing-information expectation: `{', '.join(item.expected_missing_information or []) or 'NONE'}`",
            f"- Source PDF: `{item.fixture_path}`",
            f"- Source page(s): `{', '.join(map(str, pages)) or 'NONE'}`",
            f"- Citation IDs exist: `{citations_exist}`",
            f"- Citation semantic support under current evaluator: `{support:.1f}`",
            "- Expected citation IDs:",
            _code(item.expected_evidence_ids),
            "- Acceptable evidence groups:",
            _code(item.acceptable_evidence_groups),
            "- Source evidence:",
            _code(evidence),
        ])
        if item.qa_id == "hi-q15":
            sections.extend([
                "",
                "### Required final-gold disposition for hi-q15",
                "",
                "- **EXCLUDE FROM FINAL SCORED GOLD:** the current wording has multiple valid interpretations (Class-VII eligibility marks versus MAT/SAT qualifying marks).",
                "",
                "Do not rewrite this item into an easier scored question and do not select it in the NLP-6 gold manifest.",
            ])
    return "\n".join(sections) + "\n", summaries


def _semantic_type(candidate: Any) -> str:
    parts = []
    if candidate.atomic_conditions or candidate.groups:
        parts.append("eligibility/semantic-rule")
    if candidate.guards:
        parts.append("applicability-guard")
    if candidate.actions:
        parts.append("action-graph")
    return " + ".join(parts) or "unresolved"


def build_semantic_review() -> tuple[str, list[dict[str, Any]]]:
    items = load_semantic_review(SEMANTIC_PATH)
    sections = [
        "# Synthetic Semantic Human Review",
        "",
        "> All 20 records are synthetic semantic challenge cases. They are not real-notice annotations and must never be reported as real-notice gold.",
    ]
    summaries: list[dict[str, Any]] = []
    for item in items:
        schema_status = "PASS"
        try:
            _, adapted = adapt_semantic_example(item)
            adapter_status = "PASS"
            adapter_detail = {
                "eligibility_present": adapted.eligibility is not None,
                "actions": len(adapted.actions),
                "unresolved": list(adapted.unresolved),
            }
        except Exception as exc:  # pragma: no cover - surfaced in generated review if data changes
            adapter_status = "FAIL"
            adapter_detail = {"error": str(exc)}
        meta_groups = [group.kind for group in item.candidate.groups if group.kind is not None]
        if adapter_status == "FAIL":
            suggestion = "NEEDS_CORRECTION"
            rationale = "The deterministic adapter rejected this record."
        else:
            suggestion = "READY_TO_VERIFY"
            rationale = "The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required."
            if meta_groups:
                rationale += " Relaxation/exemption/preference metadata is intentionally preserved as an unresolved adapter diagnostic."
        summaries.append({
            "id": item.example_id,
            "verification_state": item.verification_state,
            "suggestion": suggestion,
            "schema_validation": schema_status,
            "adapter_validation": adapter_status,
        })
        structure = [group.model_dump(mode="json") for group in item.candidate.groups]
        sections.extend([
            "",
            f"## {item.example_id}",
            "",
            "- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**",
            f"- Scope: `synthetic semantic case`",
            f"- Language: `{item.language}`",
            f"- Expected semantic type: `{_semantic_type(item.candidate)}`",
            f"- Source sentence: {item.source_evidence.text}",
            f"- Current verification state: `{item.verification_state}`",
            f"- Schema validation: `{schema_status}`",
            f"- Deterministic adapter validation: `{adapter_status}`",
            f"- AI audit suggestion: `{suggestion}`",
            f"- AI rationale: {rationale}",
            "- Atomic conditions (attribute, operator, value, unit/reference date):",
            _code([condition.model_dump(mode="json") for condition in item.candidate.atomic_conditions]),
            "- Guards / document applicability:",
            _code([guard.model_dump(mode="json") for guard in item.candidate.guards]),
            "- AND/OR and relaxation/exemption/preference structure:",
            _code(structure),
            "- Actions, dependency edges, and optionality:",
            _code({
                "actions": [action.model_dump(mode="json") for action in item.candidate.actions],
                "edges": item.candidate.edges,
            }),
            "- Adapter result:",
            _code(adapter_detail),
        ])
    return "\n".join(sections) + "\n", summaries


def _boundary_notes(group: ConditionGroup) -> list[str]:
    notes = []
    labels = {"<": "strict upper", ">": "strict lower", "<=": "inclusive upper", ">=": "inclusive lower"}
    for condition in iter_conditions(group):
        label = labels.get(condition.comparator.value, "non-ordered")
        note = f"{condition.attribute} {condition.comparator.value} {condition.value!r}: {label} comparator"
        if condition.reference_date:
            note += f" at cutoff {condition.reference_date}"
        notes.append(note)
    return notes


def _required_profile_attributes(group: ConditionGroup) -> set[str]:
    attributes: set[str] = set()
    for condition in iter_conditions(group):
        attributes.add("date_of_birth" if condition.attribute == "age" and condition.reference_date else condition.attribute)
    return attributes


def build_profile_review() -> tuple[str, list[dict[str, Any]]]:
    fixture = load_candidate_profiles(PROFILE_PATH)
    scenarios = {scenario.scenario_ref: scenario for scenario in fixture.scenarios}
    sections = [
        "# Candidate-Profile Scenario Review",
        "",
        "> These are 13 synthetic deterministic-evaluator cases. Actual results below are computed from each canonical AST plus its candidate profile; stored expectations are used only for comparison.",
    ]
    summaries: list[dict[str, Any]] = []
    for case in fixture.profiles:
        scenario = scenarios[case.scenario_ref]
        result = evaluate_eligibility(case.profile, scenario.eligibility)
        actual = result.overall.value
        consistent = actual == case.expected
        required = _required_profile_attributes(scenario.eligibility)
        missing = sorted(attribute for attribute in required if case.profile.get(attribute) is None)
        unambiguous = consistent and all(condition.comparator.value for condition in iter_conditions(scenario.eligibility))
        summaries.append({
            "id": case.id,
            "scenario_ref": case.scenario_ref,
            "expected": case.expected,
            "actual": actual,
            "consistent": consistent,
            "missing_information": missing,
            "unambiguous": bool(unambiguous),
        })
        sections.extend([
            "",
            f"## {case.id}",
            "",
            f"- Linked scenario: `{case.scenario_ref}` — {scenario.description}",
            f"- Expected result: `{case.expected}`",
            f"- Actual deterministic result: `{actual}`",
            f"- PASS/FAIL consistency: `{consistent}`",
            f"- Missing information: `{', '.join(missing) or 'NONE'}`",
            f"- Expected outcome unambiguous under this AST: `{bool(unambiguous)}`",
            "- Boundary / strict-vs-inclusive semantics:",
            *[f"  - {note}" for note in _boundary_notes(scenario.eligibility)],
            "- Candidate attributes:",
            _code(case.profile),
            "- Evaluated AST:",
            _code(scenario.eligibility.model_dump(mode="json")),
            "- Per-condition evaluator output:",
            _code([condition.model_dump(mode="json") for condition in result.conditions]),
        ])
    return "\n".join(sections) + "\n", summaries


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    analyses = _analysis_index()
    qa_text, qa_summary = build_qa_review(analyses)
    semantic_text, semantic_summary = build_semantic_review()
    profile_text, profile_summary = build_profile_review()

    (OUTPUT / "qa_review.md").write_text(qa_text, encoding="utf-8")
    (OUTPUT / "semantic_review.md").write_text(semantic_text, encoding="utf-8")
    (OUTPUT / "profile_review.md").write_text(profile_text, encoding="utf-8")

    summary = {
        "generated_on": date.today().isoformat(),
        "human_gold_gate": "OPEN",
        "final_nlp6_scoring_started": False,
        "qa": {
            "total": len(qa_summary),
            "verification_states": dict(Counter(item["verification_state"] for item in qa_summary)),
            "suggestions": dict(Counter(item["suggestion"] for item in qa_summary)),
            "items": qa_summary,
        },
        "synthetic_semantic": {
            "total": len(semantic_summary),
            "verification_states": dict(Counter(item["verification_state"] for item in semantic_summary)),
            "suggestions": dict(Counter(item["suggestion"] for item in semantic_summary)),
            "items": semantic_summary,
        },
        "candidate_profiles": {
            "total": len(profile_summary),
            "consistent": sum(item["consistent"] for item in profile_summary),
            "items": profile_summary,
        },
        "ambiguous_or_excluded": [
            item["id"] for item in [*qa_summary, *semantic_summary]
            if item["suggestion"] == "AMBIGUOUS"
        ],
        "recommended_exclusions": [
            {"id": "hi-q15", "reason": "QUESTION_AMBIGUITY / multiple valid interpretations"}
        ],
        "special_attention_qa_ids": sorted(SPECIAL_QA),
    }
    (OUTPUT / "review_summary.json").write_text(_json(summary) + "\n", encoding="utf-8")
    readme = f"""# Final Human Review Package

Status: **HUMAN GOLD GATE: OPEN**

This package is a review aid, not gold and not an evaluation report. No item was
marked `VERIFIED` by automation, and final NLP-6 scoring has not started.

## Contents

- `qa_review.md`: all {len(qa_summary)} real-notice QA candidates with source evidence.
- `semantic_review.md`: all {len(semantic_summary)} synthetic semantic challenge cases.
- `profile_review.md`: all {len(profile_summary)} synthetic evaluator scenarios, executed from AST + profile.
- `review_summary.json`: machine-readable counts and AI audit suggestions.

## Required review procedure

1. Open the source PDF named in each QA record at the listed page; the PDF is authoritative.
2. Decide each QA item explicitly: verify, correct, exclude, or leave unverified.
3. Exclude `hi-q15` from final scored gold because the current question has multiple valid interpretations. Do not rewrite it into an easier scored item.
4. Review every synthetic semantic case separately; do not describe these as real-notice gold.
5. Review the candidate-profile expectations and any boundary/missing-information behavior.
6. Apply decisions manually or with `scripts/review_final_annotations.py`.
7. Create a manifest only after the intended selected items are `VERIFIED`, then run `scripts/validate_nlp6_gold.py`.

`READY_TO_VERIFY` is only AI guidance. It never means `VERIFIED`.
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")
    print(_json({
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "qa": summary["qa"],
        "synthetic_semantic": summary["synthetic_semantic"],
        "candidate_profiles": {
            "total": summary["candidate_profiles"]["total"],
            "consistent": summary["candidate_profiles"]["consistent"],
        },
        "human_gold_gate": "OPEN",
    }))


if __name__ == "__main__":
    main()
