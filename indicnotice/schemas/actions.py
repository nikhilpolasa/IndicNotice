"""
Action node and dependency graph schemas for IndicNotice.

The master plan requires the system to go beyond a flat checklist.
Actions must capture:
  - what to do
  - in what order (depends_on)
  - which documents are needed
  - by what deadline
  - under what conditions (optional/conditional actions)

Example dependency chain:
    obtain_income_certificate (a1)
        ↓
    upload_documents (a2, depends_on=[a1])
        ↓
    submit_application (a3, depends_on=[a2])
        deadline_ref → TypedDate(application_deadline)

The dependency graph MUST be acyclic (validated by the validation layer).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from indicnotice.schemas.eligibility import ConditionGroup  # runtime import for model_rebuild
from indicnotice.schemas.common import ReviewState


class ActionType(str, Enum):
    """Controlled vocabulary for action types."""

    OBTAIN_DOCUMENT = "obtain_document"
    REGISTER = "register"
    PAY_FEE = "pay_fee"
    UPLOAD_DOCUMENT = "upload_document"
    SUBMIT_APPLICATION = "submit_application"
    DOWNLOAD_ADMIT_CARD = "download_admit_card"
    CORRECTION = "correction"
    ATTEND_EXAM = "attend_exam"
    ATTEND_INTERVIEW = "attend_interview"
    VERIFY_DOCUMENTS = "verify_documents"
    DOWNLOAD = "download"
    OTHER = "other"


class ActionNode(BaseModel):
    """
    A single action a candidate must perform.

    `depends_on` lists the action_ids that must be completed before this
    action can begin.  The order of this list has no significance — all
    named actions are prerequisites.

    `required_document_refs` lists doc_req_ids from DocumentRequirement
    objects that are needed to complete this action.

    `deadline_ref` is the date_type string (e.g. 'application_deadline')
    or a TypedDate object ID that constrains when this action must occur.

    `applies_when` restricts this action to a subset of candidates, using
    the same ConditionGroup AST as eligibility conditions.
    """

    action_id: str = Field(
        ...,
        description="Unique ID for this action, e.g. 'a1'.",
    )
    action_type: ActionType = Field(...)
    description: str = Field(
        ...,
        description="Human-readable description of the action.",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="action_ids that must complete before this action.",
    )
    required_document_refs: list[str] = Field(
        default_factory=list,
        description="doc_req_ids of documents needed for this action.",
    )
    fee_ref: str | None = Field(
        default=None,
        description="ID of the FeeItem required for this action (e.g. application_fee).",
    )
    deadline_ref: str | None = Field(
        default=None,
        description=(
            "Reference to a TypedDate's date_type or a specific date_id. "
            "Ties this action to a deadline."
        ),
    )
    channel: str | None = Field(
        default=None,
        description="Execution modality: 'online_portal', 'offline_post', 'in_person_center'.",
    )
    url_ref: str | None = Field(
        default=None,
        description="Reference to URL or LinkItem for executing this action.",
    )
    applies_when: "ConditionGroup | None" = Field(
        default=None,
        description="If set, this action only applies when the condition is met.",
    )
    is_optional: bool = Field(
        default=False,
        description="True when the notice explicitly presents this action as optional.",
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_state: ReviewState = Field(default=ReviewState.AUTO_EXTRACTED)

    model_config = {"arbitrary_types_allowed": True}


# Resolve ConditionGroup forward reference at module load time.
ActionNode.model_rebuild()


def get_action_execution_order(actions: list[ActionNode]) -> list[ActionNode]:
    """
    Compute a deterministic topological sort of actions based on depends_on edges.

    Returns actions in valid sequential execution order (prerequisites first).
    Raises ValueError if a cycle is detected.
    """
    action_map = {a.action_id: a for a in actions}
    if len(action_map) != len(actions):
        raise ValueError("Duplicate action_id values prevent deterministic ordering")
    # In-degree computation restricted to actions present in the set
    in_degree: dict[str, int] = {a.action_id: 0 for a in actions}
    adjacency: dict[str, list[str]] = {a.action_id: [] for a in actions}

    for a in actions:
        for dep in a.depends_on:
            if dep not in action_map:
                raise ValueError(
                    f"Action {a.action_id!r} depends on missing action {dep!r}"
                )
            adjacency[dep].append(a.action_id)
            in_degree[a.action_id] += 1

    # Deterministic queue: sort by action_id for reproducibility
    queue = sorted([aid for aid, deg in in_degree.items() if deg == 0])
    ordered: list[ActionNode] = []

    while queue:
        curr_id = queue.pop(0)
        ordered.append(action_map[curr_id])
        for nxt in adjacency[curr_id]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
                queue.sort()  # Maintain deterministic tie-breaking

    if len(ordered) != len(actions):
        unresolved = [aid for aid, deg in in_degree.items() if deg > 0]
        raise ValueError(
            f"Cyclic dependency detected involving actions: {unresolved}"
        )

    return ordered
