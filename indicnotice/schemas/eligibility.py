"""
Eligibility condition schemas and deterministic evaluator for IndicNotice.

=============================================================================
DESIGN
=============================================================================

The eligibility representation is a recursive Logical AST (Abstract Syntax
Tree) — the same pattern used in database query planners and rule engines.

                     ConditionGroup (AND/OR)
                    /                       \
          Condition(age <= 25)    ConditionGroup (OR)
                                 /                   \
                    Condition(cat == SC)   Condition(cat == ST)

This allows arbitrary nesting and is serializable to JSON for storage and
transport.

=============================================================================
COMPARATORS
=============================================================================

Supported:  >  >=  <  <=  ==  !=  IN  NOT_IN  EXISTS  NOT_EXISTS  BETWEEN

The evaluator is deterministic — it NEVER uses a generative model to decide
whether a candidate is eligible.  NLP populates the AST; this module evaluates.

=============================================================================
RETURN STATES
=============================================================================

  PASS     — candidate meets the condition
  FAIL     — candidate does not meet the condition
  UNKNOWN  — candidate profile does not supply the required attribute

Overall AND: PASS if all children PASS; FAIL if any child FAILs; else UNKNOWN.
Overall OR:  PASS if any child PASSes; FAIL if all children FAIL; else UNKNOWN.

=============================================================================
EXAMPLES (showing what the AST must be able to represent)
=============================================================================

1.  age <= 25
    Condition(attribute="age", comparator="<=", value=25, unit="years")

2.  marks >= 75
    Condition(attribute="marks_percentage", comparator=">=", value=75.0)

3.  annual income <= 250000
    Condition(attribute="annual_family_income_inr", comparator="<=", value=250000.0)

4.  category is SC OR ST
    ConditionGroup(operator="OR", children=[
        Condition(attribute="category", comparator="IN", value=["SC", "ST"])
    ])
    — or equivalently two leaf Conditions under an OR group.

5.  B.Tech AND income <= 300000
    ConditionGroup(operator="AND", children=[
        Condition(attribute="education_level", comparator="==", value="B.Tech"),
        Condition(attribute="annual_family_income_inr", comparator="<=", value=300000.0),
    ])

6.  Document A OR Document B (see documents_required.py, alternatives=[])

7.  Category-specific document: DocumentRequirement with
    applies_when=ConditionGroup(OR, [Condition(category IN [SC, ST])])

8.  Eligibility exception: Condition(negated=True, exception_of="c1", ...)

9.  See dates.py for application_open vs application_deadline.

10. See actions.py for action dependency graph.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from indicnotice.schemas.common import ReviewState


# ---------------------------------------------------------------------------
# Comparator vocabulary
# ---------------------------------------------------------------------------

class Comparator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    IN = "IN"
    NOT_IN = "NOT_IN"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"
    BETWEEN = "BETWEEN"


# ---------------------------------------------------------------------------
# Leaf condition
# ---------------------------------------------------------------------------

class Condition(BaseModel):
    """
    A single atomic eligibility condition, e.g. age <= 25.

    The `value` field carries whatever the comparator needs:
      - numeric:   float/int
      - string:    str
      - list:      list[str] for IN/NOT_IN
      - tuple/list of 2: [low, high] for BETWEEN
      - None:      for EXISTS/NOT_EXISTS

    `negated=True` flips the result (NOT semantics), e.g. "except SC/ST".
    `exception_of` names the condition_id this is an exception to.
    `scope` is a free-text scope limiter, e.g. "for OBC category only".
    """

    condition_id: str = Field(
        ...,
        description="Unique ID for this condition within the notice analysis.",
    )
    attribute: str = Field(
        ...,
        description=(
            "Normalized attribute name, e.g. 'age', 'marks_percentage', "
            "'annual_family_income_inr', 'category', 'education_level'."
        ),
    )
    comparator: Comparator = Field(...)
    value: Any = Field(
        default=None,
        description=(
            "The threshold or reference value. Type depends on comparator. "
            "None for EXISTS/NOT_EXISTS."
        ),
    )
    unit: str | None = Field(
        default=None,
        description="Unit of the value, e.g. 'years', 'INR', '%'.",
    )
    negated: bool = Field(
        default=False,
        description="If True, the result of evaluating this condition is inverted.",
    )
    scope: str | None = Field(
        default=None,
        description="Optional scope qualifier, e.g. 'for OBC only'.",
    )
    exception_of: str | None = Field(
        default=None,
        description=(
            "condition_id of the parent condition this is an exception to. "
            "Used to model 'except …' and 'unless …' clauses."
        ),
    )
    applies_when: "ConditionGroup | None" = Field(
        default=None,
        description=(
            "Guard condition: this condition only applies to candidates "
            "who satisfy applies_when (e.g. only SC/ST or only male candidates)."
        ),
    )
    reference_date: str | None = Field(
        default=None,
        description=(
            "Reckoning / cutoff ISO date for age or qualification calculation "
            "(e.g. '2024-07-01' for 'age as on 01-07-2024')."
        ),
    )
    source_text: str | None = Field(
        default=None,
        description="Verbatim eligibility text from the notice.",
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_state: ReviewState = Field(default=ReviewState.AUTO_EXTRACTED)

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("reference_date")
    @classmethod
    def validate_reference_date(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("reference_date must be a valid ISO date") from exc
        return value

    @model_validator(mode="after")
    def validate_comparator_value(self) -> "Condition":
        if self.comparator in (Comparator.EXISTS, Comparator.NOT_EXISTS):
            if self.value is not None:
                raise ValueError(f"{self.comparator.value} requires value=None")
        elif self.comparator in (Comparator.IN, Comparator.NOT_IN):
            if not isinstance(self.value, (list, tuple, set)) or not self.value:
                raise ValueError(f"{self.comparator.value} requires a non-empty collection")
        elif self.comparator == Comparator.BETWEEN:
            if not isinstance(self.value, (list, tuple)) or len(self.value) != 2:
                raise ValueError("BETWEEN requires a two-element list or tuple")
        return self


# ---------------------------------------------------------------------------
# Recursive condition group (AND / OR)
# ---------------------------------------------------------------------------

# ConditionNode is a union of Condition and ConditionGroup.
# Pydantic handles forward references via model_rebuild().

class ConditionGroup(BaseModel):
    """
    A logical grouping of conditions joined by AND or OR.

    This node and Condition together form a logical tree (the condition AST).
    """

    group_id: str | None = Field(
        default=None,
        description="Optional unique identifier for this branch, e.g. 'grp_age'.",
    )
    operator: str = Field(
        ...,
        description="Logical operator: 'AND' or 'OR'.",
    )
    label: str | None = Field(
        default=None,
        description="Human-readable label or description, e.g. 'Age relaxation for SC/ST'.",
    )
    applies_when: "ConditionGroup | None" = Field(
        default=None,
        description="Guard condition: entire group only applies if applies_when evaluates to PASS.",
    )
    children: list["ConditionNode"] = Field(
        default_factory=list,
        description="Child nodes (either Condition or ConditionGroup).",
    )
    evidence_ids: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"AND", "OR"}:
            raise ValueError("operator must be 'AND' or 'OR'")
        return normalized


# ConditionNode is the union type for recursive references.
ConditionNode = Union[Condition, ConditionGroup]

# Resolve mutual forward references.
Condition.model_rebuild()
ConditionGroup.model_rebuild()


# ---------------------------------------------------------------------------
# Evaluation result types
# ---------------------------------------------------------------------------

class EvalStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConditionResult(BaseModel):
    """Result of evaluating a single atomic Condition."""

    condition_id: str
    status: EvalStatus
    reason: str


class EligibilityResult(BaseModel):
    """
    Overall result returned by the deterministic eligibility evaluator.

    `overall` is computed from all leaf conditions following AND/OR semantics.
    `conditions` lists per-leaf results for transparency.

    Mapping to user-facing labels (future):
      PASS    -> appears_eligible
      FAIL    -> does_not_meet_stated_requirements
      UNKNOWN -> insufficient_information / needs_review

    NOTE: This is NOT a legal or governmental eligibility determination.
    """

    overall: EvalStatus
    conditions: list[ConditionResult] = Field(default_factory=list)
