from __future__ import annotations

import json
from pathlib import Path

from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.evaluation.review_models import (
    adapt_semantic_example,
    load_candidate_profiles,
    load_qa_review,
    load_semantic_review,
)


ROOT = Path(__file__).resolve().parents[2]


def test_all_review_records_validate_and_semantic_candidates_adapt():
    semantic = load_semantic_review(ROOT / "datasets/annotations/nlp4/v1/semantic_examples.json")
    qa = load_qa_review(ROOT / "datasets/annotations/nlp5/v1/qa_examples.json")
    assert len(semantic) == 20
    assert len(qa) == 30
    assert all(item.verification_state == "NEEDS_HUMAN_VERIFICATION" for item in [*semantic, *qa])
    adapted = [adapt_semantic_example(item) for item in semantic]
    assert all(evidence.evidence_id for evidence, _ in adapted)
    assert all(candidates.eligibility or candidates.actions or candidates.unresolved for _, candidates in adapted)


def test_pre_gold_corrections_preserve_source_grounding_and_open_verification_gate():
    qa = {
        item.qa_id: item
        for item in load_qa_review(ROOT / "datasets/annotations/nlp5/v1/qa_examples.json")
    }
    hi_prefix = "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:"

    assert qa["hi-q06"].candidate_answer == (
        "The notice says the online application link will be available on "
        "https://www.scertharyana.gov.in and https://www.bseh.org.in."
    )
    assert qa["hi-q06"].expected_evidence_ids == [
        f"{hi_prefix}p3:b2",
        f"{hi_prefix}p3:b3",
    ]

    expected_eligibility_evidence = [
        f"{hi_prefix}p1:b3",
        *[f"{hi_prefix}p2:b{block}" for block in (20, 21, 22, 23, 26, 27, 28)],
    ]
    for qa_id in ("hi-q07", "hi-q08"):
        assert "state" in qa[qa_id].expected_missing_information
        assert qa[qa_id].expected_evidence_ids == expected_eligibility_evidence
        assert f"{hi_prefix}p2:b24" not in qa[qa_id].expected_evidence_ids
        assert f"{hi_prefix}p2:b25" not in qa[qa_id].expected_evidence_ids
        assert qa[qa_id].verification_state == "NEEDS_HUMAN_VERIFICATION"

    assert qa["hi-q08"].expected_answerability == "PARTIAL"
    assert "state" in qa["hi-q08"].candidate_answer
    assert "https://kvsonlineadmission.kvs.gov.in" in qa["te-q14"].candidate_answer
    assert "https://balvatika.kvs.gov.in/" in qa["te-q14"].candidate_answer


def test_candidate_profile_expectations_are_executable_against_named_scenarios():
    fixture = load_candidate_profiles(ROOT / "datasets/fixtures/nlp4/candidate_profiles.json")
    scenarios = {item.scenario_ref: item.eligibility for item in fixture.scenarios}
    actual = {
        case.id: evaluate_eligibility(case.profile, scenarios[case.scenario_ref]).overall.value
        for case in fixture.profiles
    }
    assert actual == {case.id: case.expected for case in fixture.profiles}


def test_runtime_nlp_does_not_import_review_annotations_or_fixture_gold():
    forbidden = (
        "datasets/annotations",
        "datasets/fixtures",
        "candidate_profiles.json",
        "semantic_examples.json",
        "qa_examples.json",
        "scert_haryana_nmmss_2025_hindi.pdf",
        "kv_kadapa_admission_2025_telugu.pdf",
        "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2",
        "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc",
        '"hi-q',
        '"te-q',
    )
    offenders: list[str] = []
    for path in (ROOT / "services/nlp").rglob("*.py"):
        if path.name == "review_models.py":
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_generated_human_review_summary_keeps_gold_gate_open():
    summary = json.loads(
        (ROOT / "reports/final_human_review/review_summary.json").read_text(encoding="utf-8")
    )
    assert summary["human_gold_gate"] == "OPEN"
    assert summary["final_nlp6_scoring_started"] is False
    assert summary["qa"]["total"] == 30
    assert summary["qa"]["verification_states"] == {"NEEDS_HUMAN_VERIFICATION": 30}
    assert summary["synthetic_semantic"]["total"] == 20
    assert summary["synthetic_semantic"]["verification_states"] == {"NEEDS_HUMAN_VERIFICATION": 20}
    assert summary["synthetic_semantic"]["suggestions"] == {"READY_TO_VERIFY": 20}
    assert summary["candidate_profiles"]["consistent"] == 13
    assert summary["ambiguous_or_excluded"] == ["hi-q15"]
    assert summary["recommended_exclusions"] == [
        {"id": "hi-q15", "reason": "QUESTION_AMBIGUITY / multiple valid interpretations"}
    ]
