"""Bounded canonicalization for eligibility AST comparison and deduplication."""

from __future__ import annotations

from typing import Any

from indicnotice.schemas.eligibility import Condition, ConditionGroup
from indicnotice.schemas.documents_required import DocumentRequirement


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple, set)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, str):
        return " ".join(value.split()).casefold()
    return value


def canonical_condition(condition: Condition) -> tuple[Any, ...]:
    """Canonicalize semantic content while ignoring unstable condition IDs."""
    return (
        "condition",
        condition.attribute.casefold(),
        condition.comparator.value,
        _freeze(condition.value),
        _freeze(condition.unit),
        bool(condition.negated),
        _freeze(condition.reference_date),
        canonical_group(condition.applies_when) if condition.applies_when else None,
    )


def canonical_group(group: ConditionGroup | None) -> tuple[Any, ...] | None:
    """Normalize commutative sibling order without changing tree structure."""
    if group is None:
        return None
    children = [
        canonical_condition(child) if isinstance(child, Condition) else canonical_group(child)
        for child in group.children
    ]
    return (
        "group",
        group.operator,
        tuple(sorted(children, key=repr)),
        canonical_group(group.applies_when) if group.applies_when else None,
    )


def canonical_document(requirement: DocumentRequirement) -> tuple[Any, ...]:
    """Identity for a requirement instance, including applicability semantics."""
    return (
        requirement.canonical_name.casefold(),
        requirement.requirement_type.value,
        canonical_group(requirement.applies_when),
        tuple(sorted(value.casefold() for value in requirement.alternatives)),
        _freeze(requirement.notes),
    )


def iter_conditions(group: ConditionGroup | None):
    if group is None:
        return
    for child in group.children:
        if isinstance(child, Condition):
            yield child
            if child.applies_when:
                yield from iter_conditions(child.applies_when)
        else:
            yield from iter_conditions(child)
    if group.applies_when:
        yield from iter_conditions(group.applies_when)
