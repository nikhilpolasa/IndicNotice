"""Apply the source-audited pre-NLP-6 annotation candidate corrections.

This migration is intentionally explicit and idempotent.  It preserves every
item's NEEDS_HUMAN_VERIFICATION state and writes the review ledger used for the
corrective-pass audit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


QA_PATH = Path("datasets/annotations/nlp5/v1/qa_examples.json")
LOG_PATH = Path("docs/NLP6_PREP_REVIEW_LOG.md")
HI = "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2"
TE = "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc"


def ev(document_id: str, page: int, block: int) -> str:
    return f"ev:{document_id}:p{page}:b{block}"


def main() -> None:
    items: list[dict[str, Any]] = json.loads(QA_PATH.read_text(encoding="utf-8"))
    before = {item["qa_id"]: dict(item) for item in items}
    by_id = {item["qa_id"]: item for item in items}

    for item in items:
        item["annotation_scope"] = "real_notice"
        if item["qa_id"].startswith("te-"):
            item["notice_language"] = "mixed"

    for qa_id in ("hi-q01", "hi-q02", "hi-q03"):
        by_id[qa_id]["acceptable_evidence_groups"] = [[ev(HI, 1, 6)], [ev(HI, 3, 0)]]

    by_id["hi-q05"].update({
        "candidate_answer": (
            "Income certificate after selection; caste certificate for SC/ST students; "
            "and disability certificate for candidates with disabilities. Aadhaar details "
            "are used for date of birth, but an Aadhaar upload is not explicitly required."
        ),
        "expected_evidence_ids": [
            ev(HI, 3, 12), ev(HI, 3, 13), ev(HI, 3, 19), ev(HI, 3, 20),
            ev(HI, 3, 22), ev(HI, 3, 23), ev(HI, 3, 25), ev(HI, 3, 26),
        ],
    })
    by_id["hi-q06"].update({
        "candidate_answer": (
            "The notice says the online application link will be available on "
            "https://www.scertharyana.gov.in and https://www.bseh.org.in."
        ),
        "expected_evidence_ids": [ev(HI, 3, 2), ev(HI, 3, 3)],
        "acceptable_evidence_groups": [[ev(HI, 3, 2), ev(HI, 3, 3)]],
    })
    eligibility_evidence = [
        ev(HI, 1, 3),
        *[ev(HI, 2, block) for block in (20, 21, 22, 23, 26, 27, 28)],
    ]
    core_missing = [
        "current_class", "current_school_type", "previous_class",
        "previous_school_type", "attempt_count", "state",
    ]
    by_id["hi-q07"].update({
        "expected_answerability": "PARTIAL",
        "candidate_answer": "Eligibility cannot be determined from the supplied profile.",
        "expected_evidence_ids": eligibility_evidence,
        "expected_eligibility_result": "UNKNOWN",
        "expected_missing_information": core_missing,
    })
    by_id["hi-q08"].update({
        "candidate_answer": (
            "Missing: annual_family_income_inr, current_class, current_school_type, "
            "previous_class, previous_school_type, attempt_count, and state."
        ),
        "expected_evidence_ids": eligibility_evidence,
        "expected_missing_information": ["annual_family_income_inr", *core_missing],
    })
    by_id["hi-q09"].update({
        "candidate_answer": "Complete and submit the application online through the SCERT Haryana or BSEH website before 15 October 2025.",
        "expected_evidence_ids": [ev(HI, 3, block) for block in range(0, 4)],
    })
    by_id["hi-q13"].update({
        "question_type": "structured",
        "expected_answerability": "ANSWERABLE",
        "candidate_answer": "30 November 2025, 11:00 AM to 2:00 PM, at examination centres across Haryana.",
        "expected_source_field": "dates.exam_date",
        "expected_evidence_ids": [ev(HI, 1, 8), ev(HI, 1, 9), ev(HI, 3, 9), ev(HI, 3, 10)],
    })
    by_id["hi-q15"].update({
        "question_type": "partial",
        "expected_answerability": "PARTIAL",
        "candidate_answer": "The question is ambiguous: 55% concerns prior Class VII marks, while the exam has separate MAT/SAT qualifying marks (36, relaxed to 29 for listed categories).",
        "expected_evidence_ids": [ev(HI, 1, 25), ev(HI, 1, 26), ev(HI, 1, 27), ev(HI, 1, 28), ev(HI, 2, 21)],
    })

    both_kvs_links = "Class I: https://kvsonlineadmission.kvs.gov.in; Balvatika-III: https://balvatika.kvs.gov.in/"
    for qa_id in ("te-q05", "te-q15"):
        by_id[qa_id].update({
            "candidate_answer": both_kvs_links,
            "expected_evidence_ids": [ev(TE, 2, 12)],
        })
    by_id["te-q07"].update({
        "question_type": "unanswerable",
        "expected_answerability": "UNANSWERABLE",
        "candidate_answer": None,
        "expected_source_field": None,
        "expected_evidence_ids": [],
    })
    by_id["te-q12"].update({
        "candidate_answer": None,
        "expected_source_field": None,
        "expected_evidence_ids": [],
        "expected_eligibility_result": None,
    })
    by_id["te-q13"].update({
        "candidate_answer": "Kendriya Vidyalaya Sangathan (KVS) Admission Schedule for Class I & Balvatika-III – 2025-2026",
        "expected_evidence_ids": [ev(TE, 1, 1), ev(TE, 1, 2)],
    })
    by_id["te-q14"].update({
        "question_type": "structured",
        "expected_answerability": "ANSWERABLE",
        "candidate_answer": (
            "Submit online only by 21 March 2025. Use "
            "https://kvsonlineadmission.kvs.gov.in for Class I or "
            "https://balvatika.kvs.gov.in/ for Balvatika-III, as applicable."
        ),
        "expected_source_field": "dates.application_deadline, actions.channel, links",
        "expected_evidence_ids": [ev(TE, 1, 5), ev(TE, 1, 6), ev(TE, 2, 12)],
    })

    # Candidate annotations remain review candidates, never silently promoted.
    assert all(item["verification_state"] == "NEEDS_HUMAN_VERIFICATION" for item in items)
    QA_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changed_items = [
        item for item in items
        if any(before[item["qa_id"]].get(key) != item.get(key) for key in item)
    ]
    if not changed_items:
        return

    lines = [
        "# NLP-6 Preparation Review Log", "",
        "These are source-audited AI-assisted candidate corrections. They remain `NEEDS_HUMAN_VERIFICATION`; this log is not a human sign-off.", "",
        "Source basis: the two checked-in original PDFs, inspected page by page. No generated report was treated as source truth.", "",
    ]
    for item in changed_items:
        original = before[item["qa_id"]]
        changed = [key for key in item if original.get(key) != item.get(key)]
        if not changed:
            continue
        lines.extend([f"## {item['qa_id']}", "", "| Field | Old candidate | New candidate |", "|---|---|---|"])
        for key in changed:
            old = json.dumps(original.get(key), ensure_ascii=False)
            new = json.dumps(item.get(key), ensure_ascii=False)
            old_cell = old.replace("|", "\\|")
            new_cell = new.replace("|", "\\|")
            lines.append(f"| `{key}` | {old_cell} | {new_cell} |")
        source = ", ".join(item.get("expected_evidence_ids", [])) or "Original PDF: requested fact is not stated"
        reason = "Correct metadata/scope and align the candidate answer and provenance with the original notice."
        if item["qa_id"].startswith("te-"):
            reason += " The KVS notice contains English, Hindi, and Telugu content, so its notice language is mixed."
        lines.extend(["", f"- Source evidence: {source}", f"- Reason: {reason}", "- Change type: OTHER", ""])
    LOG_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
