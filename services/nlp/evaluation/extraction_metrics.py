"""Per-field NLP-2 metrics with interpretable extraction errors.

Only fields explicitly marked ``verified_complete`` are scored.  A partially
annotated document is useful for spot checks but cannot establish false
positives, so treating it as complete gold would make the metrics dishonest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal

from indicnotice.schemas.eligibility import Condition, ConditionGroup
from indicnotice.schemas.notice import NoticeAnalysis


@dataclass(frozen=True, slots=True)
class FieldMetrics:
    field: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    exact_match: float


@dataclass(frozen=True, slots=True)
class FieldError:
    field: str
    error_type: Literal[
        "false_positive", "false_negative", "wrong_role", "wrong_operator",
        "wrong_value", "wrong_attribute", "wrong_logic", "hallucination",
        "evidence", "schema", "duplicate", "conflict",
    ]
    predicted: Any = None
    expected: Any = None


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    document_id: str
    fields: tuple[FieldMetrics, ...]
    errors: tuple[FieldError, ...]
    skipped_fields: tuple[str, ...]

    @property
    def macro_f1(self) -> float | None:
        return sum(item.f1 for item in self.fields) / len(self.fields) if self.fields else None

    @property
    def exact_match(self) -> float | None:
        return sum(item.exact_match for item in self.fields) / len(self.fields) if self.fields else None


@dataclass(frozen=True, slots=True)
class CorpusEvaluationReport:
    document_count: int
    fields: tuple[FieldMetrics, ...]
    errors: tuple[FieldError, ...]


def _condition_items(group: ConditionGroup | None) -> list[dict[str, Any]]:
    if group is None:
        return []
    items: list[dict[str, Any]] = []
    stack: list[Condition | ConditionGroup] = list(group.children)
    while stack:
        node = stack.pop(0)
        if isinstance(node, ConditionGroup):
            stack[0:0] = list(node.children)
        else:
            items.append(
                {
                    "attribute": node.attribute,
                    "comparator": node.comparator.value,
                    "value": node.value,
                    "unit": node.unit,
                }
            )
    return items


def _prediction(analysis: NoticeAnalysis, field: str) -> list[Any]:
    if field == "title":
        return [] if analysis.metadata.title is None else [analysis.metadata.title]
    if field == "authority":
        return [] if analysis.metadata.issuing_authority is None else [analysis.metadata.issuing_authority]
    if field == "notice_number":
        return [] if analysis.metadata.notice_number is None else [analysis.metadata.notice_number]
    if field == "dates":
        return [{"date_type": item.date_type.value, "value": item.value, "time": item.time} for item in analysis.dates]
    if field == "fees":
        return [{"fee_type": item.fee_type, "amount_inr": item.amount_inr, "applies_to_category": item.applies_to_category} for item in analysis.fees]
    if field == "required_documents":
        return [{"canonical_name": item.canonical_name, "requirement_type": item.requirement_type.value} for item in analysis.required_documents]
    if field == "links":
        return [{"url": item.url, "link_type": item.link_type} for item in analysis.links]
    if field == "eligibility":
        return _condition_items(analysis.eligibility)
    if field == "actions":
        return [{"action_type": item.action_type.value, "depends_on_types": _dependency_types(item, analysis)} for item in analysis.actions]
    if field == "category":
        return [] if analysis.category is None else [analysis.category.value]
    raise ValueError(f"Unsupported evaluation field: {field}")


def _dependency_types(action: Any, analysis: NoticeAnalysis) -> list[str]:
    action_by_id = {item.action_id: item for item in analysis.actions}
    return sorted(action_by_id[item].action_type.value for item in action.depends_on if item in action_by_id)


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple, set)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, float):
        return round(value, 8)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {key: _thaw(item) for key, item in value}
        return [_thaw(item) for item in value]
    return value


def _gold_values(spec: dict[str, Any]) -> list[Any]:
    if "items" in spec:
        return list(spec["items"])
    return [] if spec.get("value") is None else [spec["value"]]


def _specific_errors(field: str, predicted: list[Any], expected: list[Any]) -> tuple[list[FieldError], set[int], set[int]]:
    errors: list[FieldError] = []
    consumed_pred: set[int] = set()
    consumed_gold: set[int] = set()
    if field == "dates":
        for pi, pred in enumerate(predicted):
            for gi, gold in enumerate(expected):
                if pi in consumed_pred or gi in consumed_gold:
                    continue
                if pred.get("value") == gold.get("value") and pred.get("date_type") != gold.get("date_type"):
                    errors.append(FieldError(field, "wrong_role", pred, gold))
                    consumed_pred.add(pi); consumed_gold.add(gi)
                elif pred.get("date_type") == gold.get("date_type") and pred.get("value") != gold.get("value"):
                    errors.append(FieldError(field, "wrong_value", pred, gold))
                    consumed_pred.add(pi); consumed_gold.add(gi)
    elif field == "eligibility":
        for pi, pred in enumerate(predicted):
            for gi, gold in enumerate(expected):
                if pi in consumed_pred or gi in consumed_gold:
                    continue
                if (
                    pred.get("comparator") == gold.get("comparator")
                    and _freeze(pred.get("value")) == _freeze(gold.get("value"))
                    and pred.get("attribute") != gold.get("attribute")
                ):
                    errors.append(FieldError(field, "wrong_attribute", pred, gold))
                    consumed_pred.add(pi); consumed_gold.add(gi)
                    continue
                if pred.get("attribute") != gold.get("attribute"):
                    continue
                if _freeze(pred.get("value")) == _freeze(gold.get("value")) and pred.get("comparator") != gold.get("comparator"):
                    errors.append(FieldError(field, "wrong_operator", pred, gold))
                    consumed_pred.add(pi); consumed_gold.add(gi)
                elif pred.get("comparator") == gold.get("comparator") and _freeze(pred.get("value")) != _freeze(gold.get("value")):
                    errors.append(FieldError(field, "wrong_value", pred, gold))
                    consumed_pred.add(pi); consumed_gold.add(gi)
    return errors, consumed_pred, consumed_gold


def _metric(field: str, predicted: list[Any], expected: list[Any]) -> tuple[FieldMetrics, list[FieldError]]:
    pred_frozen = [_freeze(item) for item in predicted]
    gold_frozen = [_freeze(item) for item in expected]
    unmatched_pred = list(range(len(predicted)))
    unmatched_gold = list(range(len(expected)))
    true_positives = 0
    for pi in list(unmatched_pred):
        match = next((gi for gi in unmatched_gold if pred_frozen[pi] == gold_frozen[gi]), None)
        if match is not None:
            true_positives += 1
            unmatched_pred.remove(pi)
            unmatched_gold.remove(match)
    pred_remaining = [predicted[index] for index in unmatched_pred]
    gold_remaining = [expected[index] for index in unmatched_gold]
    errors, consumed_pred, consumed_gold = _specific_errors(field, pred_remaining, gold_remaining)
    unmatched_pred = [original for local, original in enumerate(unmatched_pred) if local not in consumed_pred]
    unmatched_gold = [original for local, original in enumerate(unmatched_gold) if local not in consumed_gold]
    errors.extend(FieldError(field, "false_positive", predicted[index], None) for index in unmatched_pred)
    errors.extend(FieldError(field, "false_negative", None, expected[index]) for index in unmatched_gold)
    false_positives = len(predicted) - true_positives
    false_negatives = len(expected) - true_positives
    precision = true_positives / (true_positives + false_positives) if true_positives + false_positives else 1.0
    recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = 1.0 if not false_positives and not false_negatives else 0.0
    return FieldMetrics(field, true_positives, false_positives, false_negatives, precision, recall, f1, exact), errors


def evaluate_extraction(analysis: NoticeAnalysis, annotation: dict[str, Any]) -> EvaluationReport:
    """Evaluate one analysis against a versioned annotation record."""
    if annotation.get("document_id") != analysis.document_id:
        raise ValueError("Annotation document_id does not match NoticeAnalysis.document_id")
    fields: list[FieldMetrics] = []
    errors: list[FieldError] = []
    skipped: list[str] = []
    for field, spec in annotation.get("fields", {}).items():
        if spec.get("status") != "verified_complete":
            skipped.append(field)
            continue
        predicted = _prediction(analysis, field)
        expected = _gold_values(spec)
        metrics, field_errors = _metric(field, predicted, expected)
        fields.append(metrics)
        errors.extend(field_errors)
    return EvaluationReport(analysis.document_id, tuple(fields), tuple(errors), tuple(skipped))


def aggregate_reports(reports: Iterable[EvaluationReport]) -> CorpusEvaluationReport:
    """Micro-aggregate counts and mean field exact match across documents."""
    materialized = tuple(reports)
    names = sorted({metric.field for report in materialized for metric in report.fields})
    aggregates: list[FieldMetrics] = []
    for name in names:
        items = [metric for report in materialized for metric in report.fields if metric.field == name]
        tp = sum(item.true_positives for item in items)
        fp = sum(item.false_positives for item in items)
        fn = sum(item.false_negatives for item in items)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        exact = sum(item.exact_match for item in items) / len(items)
        aggregates.append(FieldMetrics(name, tp, fp, fn, precision, recall, f1, exact))
    errors = tuple(error for report in materialized for error in report.errors)
    return CorpusEvaluationReport(len(materialized), tuple(aggregates), errors)
