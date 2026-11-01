"""Separate eligibility and action metrics for verified NLP-4 annotations."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import re

from indicnotice.schemas.eligibility import ConditionGroup
from indicnotice.schemas.notice import NoticeAnalysis
from services.nlp.semantic.canonical import canonical_condition, canonical_group, iter_conditions


@dataclass(frozen=True, slots=True)
class PRF:
    precision: float
    recall: float
    f1: float
    true_positive: int
    predicted: int
    expected: int


@dataclass(frozen=True, slots=True)
class EligibilitySemanticMetrics:
    conditions: PRF
    attribute_accuracy: float | None
    operator_accuracy: float | None
    value_accuracy: float | None
    reference_date_accuracy: float | None
    logical_structure_correct: bool
    guard_correct: bool


@dataclass(frozen=True, slots=True)
class ActionSemanticMetrics:
    actions: PRF
    dependency_edges: PRF
    optional_accuracy: float | None
    conditional_accuracy: float | None
    deadline_accuracy: float | None


def _prf(predicted: set, expected: set) -> PRF:
    tp = len(predicted & expected)
    precision = tp / len(predicted) if predicted else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else (1.0 if not predicted else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PRF(precision, recall, f1, tp, len(predicted), len(expected))


def _prf_multiset(predicted: list[tuple], expected: list[tuple]) -> PRF:
    pred_counts, gold_counts = Counter(predicted), Counter(expected)
    tp = sum((pred_counts & gold_counts).values())
    precision = tp / len(predicted) if predicted else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else (1.0 if not predicted else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PRF(precision, recall, f1, tp, len(predicted), len(expected))


def _align_conditions(predicted: list, expected: list) -> list[tuple]:
    candidates = []
    for pred_index, pred in enumerate(predicted):
        for gold_index, gold in enumerate(expected):
            if pred.attribute.casefold() != gold.attribute.casefold():
                continue
            score = 4
            score += int(pred.comparator == gold.comparator)
            score += int(repr(pred.value) == repr(gold.value))
            score += int(pred.unit == gold.unit)
            score += int(pred.reference_date == gold.reference_date)
            score += int(canonical_group(pred.applies_when) == canonical_group(gold.applies_when))
            candidates.append((score, pred_index, gold_index))
    used_pred, used_gold, aligned = set(), set(), []
    for _, pred_index, gold_index in sorted(candidates, reverse=True):
        if pred_index in used_pred or gold_index in used_gold:
            continue
        used_pred.add(pred_index)
        used_gold.add(gold_index)
        aligned.append((predicted[pred_index], expected[gold_index]))
    return aligned


def evaluate_eligibility_semantics(predicted: ConditionGroup | None, expected: ConditionGroup | None) -> EligibilitySemanticMetrics:
    pred_items = list(iter_conditions(predicted)) if predicted else []
    gold_items = list(iter_conditions(expected)) if expected else []
    pred_canonical = {canonical_condition(item) for item in pred_items}
    gold_canonical = {canonical_condition(item) for item in gold_items}
    aligned = _align_conditions(pred_items, gold_items)

    def accuracy(field: str) -> float | None:
        if not aligned:
            return None
        return sum(getattr(pred, field) == getattr(gold, field) for pred, gold in aligned) / len(aligned)

    reference = accuracy("reference_date")
    guards_correct = all(
        canonical_group(pred.applies_when) == canonical_group(gold.applies_when)
        for pred, gold in aligned
    ) and len(aligned) == max(len(pred_items), len(gold_items))
    return EligibilitySemanticMetrics(
        conditions=_prf(pred_canonical, gold_canonical),
        attribute_accuracy=accuracy("attribute"),
        operator_accuracy=accuracy("comparator"),
        value_accuracy=(sum(repr(pred.value) == repr(gold.value) for pred, gold in aligned) / len(aligned)) if aligned else None,
        reference_date_accuracy=reference,
        logical_structure_correct=canonical_group(predicted) == canonical_group(expected),
        guard_correct=guards_correct,
    )


def evaluate_action_semantics(predicted: NoticeAnalysis, expected: NoticeAnalysis) -> ActionSemanticMetrics:
    def action_map(analysis: NoticeAnalysis):
        return {item.action_id: item for item in analysis.actions}

    pred_map, gold_map = action_map(predicted), action_map(expected)
    def base_key(item):
        target = tuple(sorted(item.required_document_refs))
        description = " ".join(re.findall(r"[^\W_]+", item.description.casefold()))
        return (
            item.action_type.value,
            target,
            item.channel,
            item.url_ref,
            description if not target else None,
            canonical_group(item.applies_when),
        )

    pred_actions = [base_key(item) for item in predicted.actions]
    gold_actions = [base_key(item) for item in expected.actions]
    pred_edges = [(base_key(pred_map[dep]), base_key(item)) for item in predicted.actions for dep in item.depends_on if dep in pred_map]
    gold_edges = [(base_key(gold_map[dep]), base_key(item)) for item in expected.actions for dep in item.depends_on if dep in gold_map]
    pred_by_key = {base_key(item): item for item in predicted.actions}
    gold_by_key = {base_key(item): item for item in expected.actions}
    common = list((Counter(pred_actions) & Counter(gold_actions)).elements())

    def field_accuracy(field: str) -> float | None:
        if not common:
            return None
        values = []
        for key in common:
            pred = pred_by_key[key]
            gold = gold_by_key[key]
            value_pred = bool(getattr(pred, field)) if field == "applies_when" else getattr(pred, field)
            value_gold = bool(getattr(gold, field)) if field == "applies_when" else getattr(gold, field)
            values.append(value_pred == value_gold)
        return sum(values) / len(values)

    return ActionSemanticMetrics(
        actions=_prf_multiset(pred_actions, gold_actions),
        dependency_edges=_prf_multiset(pred_edges, gold_edges),
        optional_accuracy=field_accuracy("is_optional"),
        conditional_accuracy=field_accuracy("applies_when"),
        deadline_accuracy=field_accuracy("deadline_ref"),
    )
