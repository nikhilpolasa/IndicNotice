"""Validate a human-created NLP-6 gold manifest and all referenced records."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from services.nlp.evaluation.review_models import (
    adapt_semantic_example,
    load_candidate_profiles,
    load_qa_review,
    load_semantic_review,
)
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.ingestion.router import DocumentIngestor
from services.nlp.semantic.canonical import iter_conditions


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "datasets/annotations/nlp6/v1/gold_manifest.json"
DEFAULT_SOURCES = {
    "qa": "datasets/annotations/nlp5/v1/qa_examples.json",
    "semantic": "datasets/annotations/nlp4/v1/semantic_examples.json",
    "profiles": "datasets/fixtures/nlp4/candidate_profiles.json",
}


def _fail(errors: list[str]) -> None:
    print("FAIL — NLP6 GOLD FREEZE INVALID", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_paths(manifest: dict[str, Any]) -> dict[str, Path]:
    configured = manifest.get("source_annotation_files", DEFAULT_SOURCES)
    if not isinstance(configured, dict):
        raise ValueError("source_annotation_files must map qa, semantic, and profiles to repository paths")
    return {key: ROOT / configured.get(key, value) for key, value in DEFAULT_SOURCES.items()}


def main() -> None:
    if not MANIFEST.exists():
        _fail([f"gold manifest does not exist: {MANIFEST.relative_to(ROOT)}", "Human verification is still required; no gold was frozen."])
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        sources = _source_paths(manifest)
        qa = load_qa_review(sources["qa"])
        semantic = load_semantic_review(sources["semantic"])
        profiles = load_candidate_profiles(sources["profiles"])
    except Exception as exc:
        _fail([f"manifest or annotation schema validation failed: {exc}"])

    errors: list[str] = []
    if manifest.get("canonical_schema_version") != "1.0":
        errors.append("canonical_schema_version must be '1.0'")
    selections = {
        "qa": list(manifest.get("verified_qa_item_ids", [])),
        "semantic": list(manifest.get("verified_synthetic_semantic_ids", [])),
        "profiles": list(manifest.get("candidate_profile_ids", [])),
        "excluded": list(manifest.get("excluded_or_ambiguous_ids", [])),
    }
    for name, values in selections.items():
        duplicates = _duplicates(values)
        if duplicates:
            errors.append(f"duplicate IDs in {name}: {duplicates}")
    selected = set(selections["qa"]) | set(selections["semantic"]) | set(selections["profiles"])
    overlap = selected & set(selections["excluded"])
    if overlap:
        errors.append(f"selected IDs are also excluded/ambiguous: {sorted(overlap)}")

    qa_by_id = {item.qa_id: item for item in qa}
    semantic_by_id = {item.example_id: item for item in semantic}
    profile_by_id = {item.id: item for item in profiles.profiles}
    for item_id in selections["qa"]:
        item = qa_by_id.get(item_id)
        if item is None:
            errors.append(f"unknown QA ID: {item_id}")
        elif item.verification_state != "VERIFIED":
            errors.append(f"QA item {item_id} is {item.verification_state}, not VERIFIED")
        elif item_id == "hi-q15":
            errors.append("hi-q15 is excluded for QUESTION_AMBIGUITY and cannot be selected")
    for item_id in selections["semantic"]:
        item = semantic_by_id.get(item_id)
        if item is None:
            errors.append(f"unknown semantic ID: {item_id}")
        elif item.verification_state != "VERIFIED":
            errors.append(f"semantic item {item_id} is {item.verification_state}, not VERIFIED")
        else:
            try:
                evidence, candidates = adapt_semantic_example(item)
                referenced = set()
                if candidates.eligibility:
                    referenced.update(candidates.eligibility.evidence_ids)
                    referenced.update(
                        evidence_id
                        for condition in iter_conditions(candidates.eligibility)
                        for evidence_id in condition.evidence_ids
                    )
                referenced.update(eid for action in candidates.actions for eid in action.evidence_ids)
                if referenced and referenced != {evidence.evidence_id}:
                    errors.append(f"semantic item {item_id} has invalid adapted evidence references")
            except Exception as exc:
                errors.append(f"semantic item {item_id} adapter validation failed: {exc}")
    for item_id in selections["profiles"]:
        case = profile_by_id.get(item_id)
        if case is None:
            errors.append(f"unknown candidate-profile ID: {item_id}")
            continue
        scenario = next(item for item in profiles.scenarios if item.scenario_ref == case.scenario_ref)
        actual = evaluate_eligibility(case.profile, scenario.eligibility).overall.value
        if actual != case.expected:
            errors.append(f"candidate profile {item_id} expected {case.expected} but evaluator returned {actual}")

    # Validate real QA source hashes/document IDs and evidence against the PDF-derived spans.
    ingestions: dict[str, Any] = {}
    for item_id in selections["qa"]:
        item = qa_by_id.get(item_id)
        if item is None:
            continue
        try:
            if item.fixture_path not in ingestions:
                ingestions[item.fixture_path] = DocumentIngestor().ingest(ROOT / item.fixture_path)
            ingestion = ingestions[item.fixture_path]
            if ingestion.document.document_id != item.document_id:
                errors.append(f"QA item {item_id} document ID does not match its source PDF")
            valid_evidence = {span.evidence_id for span in ingestion.evidence}
            invalid = sorted(set(item.expected_evidence_ids) - valid_evidence)
            invalid_groups = sorted({eid for group in item.acceptable_evidence_groups for eid in group} - valid_evidence)
            if invalid or invalid_groups:
                errors.append(f"QA item {item_id} has invalid evidence IDs: {sorted(set(invalid + invalid_groups))}")
        except Exception as exc:
            errors.append(f"QA item {item_id} source/evidence validation failed: {exc}")

    hashes = manifest.get("file_hashes", {})
    if not isinstance(hashes, dict):
        errors.append("file_hashes must be a path-to-SHA256 object")
    else:
        for source in sources.values():
            relative = source.relative_to(ROOT).as_posix()
            if relative not in hashes:
                errors.append(f"file_hashes is missing source annotation file: {relative}")
        for relative, expected in hashes.items():
            path = ROOT / relative
            if not path.is_file():
                errors.append(f"hashed source file does not exist: {relative}")
            elif _sha256(path) != expected:
                errors.append(f"source hash mismatch: {relative}")

    if not selections["qa"] and not selections["semantic"] and not selections["profiles"]:
        errors.append("manifest selects no gold items")
    if errors:
        _fail(errors)
    print("PASS — NLP6 GOLD FREEZE VALID")
    print(json.dumps({
        "verified_qa": len(selections["qa"]),
        "verified_synthetic_semantic": len(selections["semantic"]),
        "candidate_profiles": len(selections["profiles"]),
        "excluded_or_ambiguous": len(selections["excluded"]),
    }, indent=2))


if __name__ == "__main__":
    main()
