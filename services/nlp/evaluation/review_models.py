"""Typed review-corpus contracts and adapters for pre-NLP-6 data review.

These models deliberately do not confer gold status.  A candidate remains
unscored until its ``verification_state`` is changed by a human reviewer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.semantic.types import SemanticCandidates


VerificationState = Literal["NEEDS_HUMAN_VERIFICATION", "VERIFIED", "REJECTED"]
AnnotationScope = Literal["synthetic", "real_notice"]


class ReviewSourceEvidence(BaseModel):
    evidence_id: str
    text: str = Field(min_length=1)
    model_config = {"extra": "forbid"}


class ReviewCondition(BaseModel):
    attribute: str = Field(min_length=1)
    operator: Comparator
    value: Any = None
    unit: str | None = None
    reference_date: str | None = None
    model_config = {"extra": "forbid"}


class ReviewGroup(BaseModel):
    operator: Literal["AND", "OR"] | None = None
    members: list[int] = Field(default_factory=list)
    kind: Literal["delta_relaxation", "exemption", "preference_only"] | None = None
    attribute: str | None = None
    delta: float | None = None
    target: str | None = None
    unresolved_without_base: bool | None = None
    must_not_be_mandatory: bool | None = None
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_shape(self) -> "ReviewGroup":
        if (self.operator is None) == (self.kind is None):
            raise ValueError("group must have exactly one of operator or kind")
        if self.operator is not None and not self.members:
            raise ValueError("logical group requires member indexes")
        return self


class ReviewAction(BaseModel):
    id: str = Field(min_length=1)
    type: ActionType
    optional: bool = False
    model_config = {"extra": "forbid"}


class ReviewCandidate(BaseModel):
    atomic_conditions: list[ReviewCondition] = Field(default_factory=list)
    guards: list[ReviewCondition] = Field(default_factory=list)
    groups: list[ReviewGroup] = Field(default_factory=list)
    actions: list[ReviewAction] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_references(self) -> "ReviewCandidate":
        for group in self.groups:
            if group.operator is not None and any(index < 0 or index >= len(self.atomic_conditions) for index in group.members):
                raise ValueError("logical group references an invalid atomic-condition index")
        action_ids = {action.id for action in self.actions}
        if len(action_ids) != len(self.actions):
            raise ValueError("candidate contains duplicate action IDs")
        if any(source not in action_ids or target not in action_ids for source, target in self.edges):
            raise ValueError("candidate edge references an unknown action")
        return self


class SemanticReviewExample(BaseModel):
    example_id: str
    document_id: str
    language: Literal["hi", "te"]
    annotation_scope: AnnotationScope = "synthetic"
    verification_state: VerificationState
    source_evidence: ReviewSourceEvidence
    candidate: ReviewCandidate
    model_config = {"extra": "forbid"}


class QAReviewExample(BaseModel):
    qa_id: str
    fixture_path: str
    document_id: str
    notice_language: Literal["hi", "te", "mixed"]
    question: str = Field(min_length=1)
    question_language: Literal["en", "hi", "te"]
    question_type: Literal["structured", "eligibility", "procedure", "retrieval", "unanswerable", "partial"]
    expected_answerability: Literal["ANSWERABLE", "PARTIAL", "UNANSWERABLE"]
    candidate_answer: str | None
    expected_source_field: str | None
    expected_evidence_ids: list[str]
    acceptable_evidence_groups: list[list[str]] = Field(default_factory=list)
    candidate_profile: dict[str, Any] | None = None
    expected_eligibility_result: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"] | None = None
    expected_missing_information: list[str] | None = None
    annotation_scope: AnnotationScope = "real_notice"
    verification_state: VerificationState
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_answerability(self) -> "QAReviewExample":
        if self.expected_answerability == "UNANSWERABLE" and self.expected_evidence_ids:
            raise ValueError("unanswerable item cannot require supporting evidence")
        if self.question_type == "eligibility" and self.expected_eligibility_result is None:
            raise ValueError("eligibility item requires expected_eligibility_result")
        return self


class EvaluationScenario(BaseModel):
    scenario_ref: str
    description: str
    eligibility: ConditionGroup
    model_config = {"extra": "forbid"}


class CandidateProfileCase(BaseModel):
    id: str
    scenario_ref: str
    profile: dict[str, Any]
    expected: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
    model_config = {"extra": "forbid"}


class CandidateProfileFixture(BaseModel):
    notice: str
    scenarios: list[EvaluationScenario]
    profiles: list[CandidateProfileCase]
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_scenario_references(self) -> "CandidateProfileFixture":
        scenario_ids = {scenario.scenario_ref for scenario in self.scenarios}
        if len(scenario_ids) != len(self.scenarios):
            raise ValueError("duplicate scenario_ref")
        missing = {case.scenario_ref for case in self.profiles} - scenario_ids
        if missing:
            raise ValueError(f"unknown scenario_ref values: {sorted(missing)}")
        return self


def _condition(item: ReviewCondition, example: SemanticReviewExample, suffix: str) -> Condition:
    return Condition(
        condition_id=f"{example.example_id}:{suffix}",
        attribute=item.attribute,
        comparator=item.operator,
        value=item.value,
        unit=item.unit,
        reference_date=item.reference_date,
        source_text=example.source_evidence.text,
        evidence_ids=[example.source_evidence.evidence_id],
    )


def adapt_semantic_example(example: SemanticReviewExample) -> tuple[EvidenceSpan, SemanticCandidates]:
    """Convert a review record into executable canonical semantic candidates."""
    evidence = EvidenceSpan(
        evidence_id=example.source_evidence.evidence_id,
        document_id=example.document_id,
        page_number=1,
        block_id=example.source_evidence.evidence_id,
        text=example.source_evidence.text,
    )
    atoms = [_condition(item, example, f"condition-{index}") for index, item in enumerate(example.candidate.atomic_conditions)]
    logical_groups = [group for group in example.candidate.groups if group.operator is not None]
    if logical_groups:
        children: list[Condition | ConditionGroup] = []
        referenced: set[int] = set()
        for index, group in enumerate(logical_groups):
            referenced.update(group.members)
            children.append(ConditionGroup(
                group_id=f"{example.example_id}:group-{index}",
                operator=group.operator,
                children=[atoms[member] for member in group.members],
                evidence_ids=[evidence.evidence_id],
            ))
        children.extend(atom for index, atom in enumerate(atoms) if index not in referenced)
    else:
        children = list(atoms)
    eligibility = ConditionGroup(
        group_id=f"{example.example_id}:root",
        operator="AND",
        children=children,
        evidence_ids=[evidence.evidence_id],
    ) if children else None

    guard_atoms = [_condition(item, example, f"guard-{index}") for index, item in enumerate(example.candidate.guards)]
    guard = ConditionGroup(
        group_id=f"{example.example_id}:guard",
        operator="AND",
        children=guard_atoms,
        evidence_ids=[evidence.evidence_id],
    ) if guard_atoms else None
    dependencies: dict[str, list[str]] = {action.id: [] for action in example.candidate.actions}
    for source, target in example.candidate.edges:
        dependencies[target].append(source)
    actions = tuple(
        ActionNode(
            action_id=f"{example.example_id}:{action.id}",
            action_type=action.type,
            description=example.source_evidence.text,
            depends_on=[f"{example.example_id}:{value}" for value in dependencies[action.id]],
            applies_when=guard,
            is_optional=action.optional,
            evidence_ids=[evidence.evidence_id],
        )
        for action in example.candidate.actions
    )
    unresolved = tuple(
        f"{example.example_id}:{group.kind}"
        for group in example.candidate.groups
        if group.kind is not None
    )
    return evidence, SemanticCandidates(eligibility=eligibility, actions=actions, unresolved=unresolved)


def load_semantic_review(path: Path) -> list[SemanticReviewExample]:
    return [SemanticReviewExample.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def load_qa_review(path: Path) -> list[QAReviewExample]:
    return [QAReviewExample.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def load_candidate_profiles(path: Path) -> CandidateProfileFixture:
    return CandidateProfileFixture.model_validate_json(path.read_text(encoding="utf-8"))
