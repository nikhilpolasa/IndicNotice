"""Interactive, explicit human review of one annotation at a time.

No choice defaults to verification.  Each persisted transition is validated,
backed up, and appended to the human review log without inventing a reviewer
identity.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from services.nlp.evaluation.review_models import load_qa_review, load_semantic_review


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "qa": ROOT / "datasets/annotations/nlp5/v1/qa_examples.json",
    "semantic": ROOT / "datasets/annotations/nlp4/v1/semantic_examples.json",
}
ID_FIELDS = {"qa": "qa_id", "semantic": "example_id"}
LOG_PATH = ROOT / "reports/final_human_review/human_review_log.jsonl"


def _validate(kind: str, path: Path) -> None:
    if kind == "qa":
        load_qa_review(path)
    else:
        load_semantic_review(path)


def _show(kind: str, item: dict) -> None:
    item_id = item[ID_FIELDS[kind]]
    print("\n" + "=" * 78)
    print(f"{kind.upper()} ITEM: {item_id}")
    print(f"Current state: {item['verification_state']}")
    if kind == "qa":
        print(f"PDF: {item['fixture_path']}")
        print(f"Question: {item['question']}")
        print(f"Answerability: {item['expected_answerability']}")
        print(f"Candidate answer: {item.get('candidate_answer') or 'NOT_STATED'}")
        print("Evidence IDs:")
        for evidence_id in item.get("expected_evidence_ids", []):
            print(f"  - {evidence_id}")
        if item_id == "hi-q15":
            print("QUESTION_AMBIGUITY: exclude this item from final scored gold.")
    else:
        print("Scope: SYNTHETIC SEMANTIC CASE (not real-notice gold)")
        print(f"Sentence: {item['source_evidence']['text']}")
        print(json.dumps(item["candidate"], ensure_ascii=False, indent=2))


def _persist(kind: str, path: Path, records: list[dict], item_id: str, state: str, action: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _validate(kind, temporary)
    temporary.replace(path)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "item_type": kind,
        "item_id": item_id,
        "explicit_action": action,
        "new_verification_state": state,
        "backup": backup.relative_to(ROOT).as_posix(),
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"Saved {item_id} -> {state}; backup: {backup.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=sorted(SOURCES), help="Annotation collection to review")
    parser.add_argument("--id", dest="selected_id", help="Review only this existing item ID")
    args = parser.parse_args()

    path = SOURCES[args.kind]
    _validate(args.kind, path)
    records = json.loads(path.read_text(encoding="utf-8"))
    id_field = ID_FIELDS[args.kind]
    selected = [item for item in records if args.selected_id is None or item[id_field] == args.selected_id]
    if args.selected_id and not selected:
        raise SystemExit(f"Unknown {args.kind} item ID: {args.selected_id}")

    print("Choices: V=VERIFY, S=SKIP/REJECT, L=LEAVE UNVERIFIED, Q=QUIT")
    print("There is no default VERIFY action. Pressing Enter leaves the item unchanged.")
    for item in selected:
        _show(args.kind, item)
        choice = input("Explicit choice [V/S/L/Q]: ").strip().upper()
        if choice == "Q":
            print("Review stopped; no action was taken on this item.")
            return
        if choice in {"", "L"}:
            print("Left unchanged.")
            continue
        if choice not in {"V", "S"}:
            print("Unrecognized choice; item left unchanged.")
            continue
        if args.kind == "qa" and item[id_field] == "hi-q15" and choice == "V":
            print("Verification blocked: hi-q15 is excluded because the question has multiple valid interpretations.")
            continue
        state = "VERIFIED" if choice == "V" else "REJECTED"
        item["verification_state"] = state
        _persist(args.kind, path, records, item[id_field], state, "VERIFY" if choice == "V" else "SKIP")


if __name__ == "__main__":
    main()
