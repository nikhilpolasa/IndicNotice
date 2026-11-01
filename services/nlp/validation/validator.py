"""
Validation layer for IndicNotice NoticeAnalysis objects.

After extraction, this module runs deterministic checks and appends
AnalysisWarning objects to the analysis.  It NEVER silently fixes
uncertain extractions — ambiguous fields are flagged as needs_review.

Checks performed:
  1. ISO date format validity
  2. Plausible date ordering (open < deadline, pub < deadline, etc.)
  3. Percentage range [0, 100]
  4. Age range plausibility [0, 120]
  5. Evidence ID resolution (every referenced ID must exist in evidence list)
  6. Dangling document/action references
  7. Action dependency graph acyclicity
  8. Duplicate date roles
  9. Contradictory fee amounts for same category
  10. Duplicate IDs and cross-document evidence
  11. Fee/date/link references from actions
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Callable

from indicnotice.schemas.notice import AnalysisWarning, NoticeAnalysis, ReviewState
from indicnotice.schemas.eligibility import Condition, ConditionGroup, ConditionNode

_VALIDATOR_WARNING_CODES = {
    "dangling_evidence_ref",
    "evidence_document_mismatch",
    "duplicate_id",
    "invalid_date_format",
    "unexpected_date_order",
    "duplicate_date_role",
    "metadata_date_conflict",
    "cyclic_action_dependency",
    "dangling_action_ref",
    "dangling_doc_ref",
    "dangling_fee_ref",
    "dangling_deadline_ref",
    "dangling_url_ref",
    "implausible_percentage",
    "implausible_age",
    "contradictory_fee_amount",
    "eligibility_structure_too_deep",
    "dangling_condition_ref",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_analysis(analysis: NoticeAnalysis) -> NoticeAnalysis:
    """
    Run all deterministic validators against a NoticeAnalysis.

    Returns the same analysis object with warnings appended and
    overall_review_state updated if errors are found.

    This function is idempotent — calling it multiple times is safe.
    """
    # Preserve extractor/user warnings, but recompute validator-owned warnings.
    # This makes repeated validation deterministic and genuinely idempotent.
    warnings = [
        warning for warning in analysis.warnings
        if warning.code not in _VALIDATOR_WARNING_CODES
    ]

    _check_duplicate_ids(analysis, warnings)
    _check_evidence_documents(analysis, warnings)
    _check_evidence_refs(analysis, warnings)
    _check_date_formats(analysis, warnings)
    _check_date_ordering(analysis, warnings)
    _check_duplicate_date_roles(analysis, warnings)
    _check_metadata_date_consistency(analysis, warnings)
    _check_action_graph_acyclic(analysis, warnings)
    _check_dangling_action_refs(analysis, warnings)
    _check_dangling_doc_refs(analysis, warnings)
    _check_action_resource_refs(analysis, warnings)
    _check_contradictory_fees(analysis, warnings)
    _check_eligibility_ranges(analysis, warnings)

    has_errors = any(w.severity == "error" for w in warnings)
    has_warnings = any(w.severity == "warning" for w in warnings)

    if has_errors:
        new_state = ReviewState.NEEDS_REVIEW
    elif has_warnings:
        new_state = ReviewState.NEEDS_REVIEW
    else:
        new_state = analysis.overall_review_state

    return analysis.model_copy(
        update={"warnings": warnings, "overall_review_state": new_state}
    )


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _check_evidence_refs(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Every evidence_id referenced anywhere must exist in analysis.evidence."""
    declared = analysis.evidence_ids()

    def check_ids(ids: list[str], field_path: str) -> None:
        for eid in ids:
            if eid not in declared:
                warnings.append(AnalysisWarning(
                    code="dangling_evidence_ref",
                    message=f"evidence_id {eid!r} referenced in {field_path} not found in evidence list.",
                    severity="error",
                    field_path=field_path,
                ))

    for i, td in enumerate(analysis.dates):
        check_ids(td.evidence_ids, f"dates[{i}].evidence_ids")

    for i, fee in enumerate(analysis.fees):
        check_ids(fee.evidence_ids, f"fees[{i}].evidence_ids")

    for i, doc in enumerate(analysis.required_documents):
        check_ids(doc.evidence_ids, f"required_documents[{i}].evidence_ids")

    for i, action in enumerate(analysis.actions):
        check_ids(action.evidence_ids, f"actions[{i}].evidence_ids")

    for i, link in enumerate(analysis.links):
        check_ids(link.evidence_ids, f"links[{i}].evidence_ids")

    for i, benefit in enumerate(analysis.benefits):
        check_ids(benefit.evidence_ids, f"benefits[{i}].evidence_ids")

    check_ids(
        analysis.metadata.issuing_authority_evidence_ids,
        "metadata.issuing_authority_evidence_ids",
    )
    check_ids(analysis.metadata.title_evidence_ids, "metadata.title_evidence_ids")
    check_ids(
        analysis.metadata.notice_number_evidence_ids,
        "metadata.notice_number_evidence_ids",
    )
    check_ids(
        analysis.metadata.publication_date_evidence_ids,
        "metadata.publication_date_evidence_ids",
    )
    for i, warning in enumerate(analysis.warnings):
        check_ids(warning.evidence_ids, f"warnings[{i}].evidence_ids")

    if analysis.eligibility is not None:
        _walk_condition_tree(
            analysis.eligibility,
            lambda node, path: check_ids(node.evidence_ids, f"{path}.evidence_ids"),
            warnings,
            "eligibility",
        )
    for i, document in enumerate(analysis.required_documents):
        if document.applies_when is not None:
            _walk_condition_tree(
                document.applies_when,
                lambda node, path: check_ids(node.evidence_ids, f"{path}.evidence_ids"),
                warnings,
                f"required_documents[{i}].applies_when",
            )
    for i, action in enumerate(analysis.actions):
        if action.applies_when is not None:
            _walk_condition_tree(
                action.applies_when,
                lambda node, path: check_ids(node.evidence_ids, f"{path}.evidence_ids"),
                warnings,
                f"actions[{i}].applies_when",
            )


def _walk_condition_tree(
    root: ConditionNode,
    visit: Callable[[ConditionNode, str], None],
    warnings: list[AnalysisWarning],
    root_path: str,
    max_depth: int = 100,
) -> None:
    """Iteratively walk children and guards without looping on mutated cycles."""
    stack: list[tuple[ConditionNode, str, int]] = [(root, root_path, 0)]
    visited: set[int] = set()
    while stack:
        node, path, depth = stack.pop()
        identity = id(node)
        if identity in visited:
            continue
        visited.add(identity)
        if depth > max_depth:
            warnings.append(AnalysisWarning(
                code="eligibility_structure_too_deep",
                message=f"Eligibility structure exceeds maximum validation depth {max_depth}.",
                severity="error",
                field_path=path,
            ))
            return
        visit(node, path)
        guard = node.applies_when
        if guard is not None:
            stack.append((guard, f"{path}.applies_when", depth + 1))
        if isinstance(node, ConditionGroup):
            for index, child in reversed(list(enumerate(node.children))):
                stack.append((child, f"{path}.children[{index}]", depth + 1))


def _check_duplicate_ids(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """IDs used as reference targets must be non-empty and unique by type."""
    collections = {
        "evidence": [item.evidence_id for item in analysis.evidence],
        "dates": [item.date_id for item in analysis.dates if item.date_id],
        "fees": [item.fee_id for item in analysis.fees if item.fee_id],
        "required_documents": [item.doc_req_id for item in analysis.required_documents if item.doc_req_id],
        "actions": [item.action_id for item in analysis.actions],
    }
    for field_name, identifiers in collections.items():
        seen: set[str] = set()
        for identifier in identifiers:
            if identifier in seen:
                warnings.append(AnalysisWarning(
                    code="duplicate_id",
                    message=f"Duplicate {field_name} identifier {identifier!r}.",
                    severity="error",
                    field_path=field_name,
                ))
            seen.add(identifier)

    condition_ids: list[str] = []
    group_ids: list[str] = []
    exception_refs: list[tuple[str, str]] = []

    def collect(node: ConditionNode, path: str) -> None:
        if isinstance(node, Condition):
            condition_ids.append(node.condition_id)
            if node.exception_of is not None:
                exception_refs.append((path, node.exception_of))
        elif node.group_id:
            group_ids.append(node.group_id)

    roots: list[tuple[ConditionNode, str]] = []
    if analysis.eligibility is not None:
        roots.append((analysis.eligibility, "eligibility"))
    roots.extend(
        (item.applies_when, f"required_documents[{index}].applies_when")
        for index, item in enumerate(analysis.required_documents)
        if item.applies_when is not None
    )
    roots.extend(
        (item.applies_when, f"actions[{index}].applies_when")
        for index, item in enumerate(analysis.actions)
        if item.applies_when is not None
    )
    for root, path in roots:
        _walk_condition_tree(root, collect, warnings, path)

    for field_name, identifiers in (
        ("condition", condition_ids),
        ("condition_group", group_ids),
    ):
        seen: set[str] = set()
        for identifier in identifiers:
            if identifier in seen:
                warnings.append(AnalysisWarning(
                    code="duplicate_id",
                    message=f"Duplicate {field_name} identifier {identifier!r}.",
                    severity="error",
                    field_path="eligibility",
                ))
            seen.add(identifier)

    declared_conditions = set(condition_ids)
    for path, target in exception_refs:
        if target not in declared_conditions:
            warnings.append(AnalysisWarning(
                code="dangling_condition_ref",
                message=f"exception_of references missing condition {target!r}.",
                severity="error",
                field_path=f"{path}.exception_of",
            ))


def _check_evidence_documents(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    for index, evidence in enumerate(analysis.evidence):
        if evidence.document_id != analysis.document_id:
            warnings.append(AnalysisWarning(
                code="evidence_document_mismatch",
                message=(
                    f"Evidence {evidence.evidence_id!r} belongs to document "
                    f"{evidence.document_id!r}, not {analysis.document_id!r}."
                ),
                severity="error",
                field_path=f"evidence[{index}].document_id",
                evidence_ids=[evidence.evidence_id],
            ))


def _check_date_formats(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Validate that all date values are valid calendar dates."""
    for i, td in enumerate(analysis.dates):
        if td.value is None:
            continue
        try:
            date.fromisoformat(td.value)
        except ValueError:
            warnings.append(AnalysisWarning(
                code="invalid_date_format",
                message=f"dates[{i}] ({td.date_type}) value {td.value!r} is not a valid ISO date.",
                severity="error",
                field_path=f"dates[{i}].value",
                evidence_ids=td.evidence_ids,
            ))


def _check_date_ordering(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """
    Warn if dates that should be ordered are in unexpected order.

    Rules:
      publication_date <= application_open
      application_open <= application_deadline
      application_deadline <= exam_date (usually)
      fee_payment_deadline <= application_deadline (usually)
    """
    ORDERING_RULES = [
        ("publication_date", "application_open"),
        ("application_open", "application_deadline"),
        ("fee_payment_deadline", "application_deadline"),
        ("application_deadline", "exam_date"),
        ("exam_date", "result_date"),
    ]

    date_map: dict[str, date] = {}
    for td in analysis.dates:
        if td.value:
            try:
                date_map[td.date_type.value] = date.fromisoformat(td.value)
            except (ValueError, AttributeError):
                pass

    for earlier_role, later_role in ORDERING_RULES:
        if earlier_role in date_map and later_role in date_map:
            if date_map[earlier_role] > date_map[later_role]:
                warnings.append(AnalysisWarning(
                    code="unexpected_date_order",
                    message=(
                        f"{earlier_role} ({date_map[earlier_role]}) is after "
                        f"{later_role} ({date_map[later_role]}). "
                        "Verify extraction."
                    ),
                    severity="warning",
                ))


def _check_duplicate_date_roles(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Warn if the same date role appears more than once."""
    role_count: dict[str, int] = defaultdict(int)
    for td in analysis.dates:
        role_count[td.date_type] += 1

    for role, count in role_count.items():
        if count > 1:
            warnings.append(AnalysisWarning(
                code="duplicate_date_role",
                message=(
                    f"Date role {role!r} appears {count} times. Multiple occurrences "
                    "may be valid, but must be distinguished and evidence-grounded."
                ),
                severity="warning",
            ))


def _check_metadata_date_consistency(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    metadata_date = analysis.metadata.publication_date
    if metadata_date is None:
        return
    typed_dates = {
        item.value
        for item in analysis.dates
        if item.date_type.value == "publication_date" and item.value is not None
    }
    if typed_dates and metadata_date not in typed_dates:
        warnings.append(AnalysisWarning(
            code="metadata_date_conflict",
            message=(
                f"metadata.publication_date {metadata_date!r} conflicts with "
                f"typed publication date values {sorted(typed_dates)!r}."
            ),
            severity="error",
            field_path="metadata.publication_date",
        ))


def _check_action_graph_acyclic(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Check that the action dependency graph is a DAG (no cycles)."""
    action_ids = {a.action_id for a in analysis.actions}
    graph = {a.action_id: [d for d in a.depends_on if d in action_ids] for a in analysis.actions}
    # 0 = unseen, 1 = active, 2 = complete. Explicit stack avoids recursion limits.
    state: dict[str, int] = {action_id: 0 for action_id in action_ids}
    for action_id in sorted(action_ids):
        if state[action_id] != 0:
            continue
        stack: list[tuple[str, int]] = [(action_id, 0)]
        state[action_id] = 1
        while stack:
            node, next_index = stack[-1]
            neighbors = graph.get(node, [])
            if next_index >= len(neighbors):
                state[node] = 2
                stack.pop()
                continue
            neighbor = neighbors[next_index]
            stack[-1] = (node, next_index + 1)
            if state[neighbor] == 1:
                warnings.append(AnalysisWarning(
                    code="cyclic_action_dependency",
                    message=(
                        f"Action dependency graph contains a cycle involving action {neighbor!r}. "
                        "This must be resolved before evaluation."
                    ),
                    severity="error",
                ))
                return
            if state[neighbor] == 0:
                state[neighbor] = 1
                stack.append((neighbor, 0))


def _check_dangling_action_refs(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Warn about depends_on references to non-existent action IDs."""
    action_ids = {a.action_id for a in analysis.actions}
    for action in analysis.actions:
        for dep_id in action.depends_on:
            if dep_id not in action_ids:
                warnings.append(AnalysisWarning(
                    code="dangling_action_ref",
                    message=(
                        f"Action {action.action_id!r} depends_on {dep_id!r} "
                        "which does not exist in the actions list."
                    ),
                    severity="error",
                    field_path=f"actions[{action.action_id}].depends_on",
                ))


def _check_dangling_doc_refs(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Warn about required_document_refs in actions that don't exist."""
    doc_ids = {d.doc_req_id for d in analysis.required_documents if d.doc_req_id}
    for action in analysis.actions:
        for doc_ref in action.required_document_refs:
            if doc_ref not in doc_ids:
                warnings.append(AnalysisWarning(
                    code="dangling_doc_ref",
                    message=(
                        f"Action {action.action_id!r} references document {doc_ref!r} "
                        "which does not exist in required_documents."
                    ),
                    severity="warning",
                    field_path=f"actions[{action.action_id}].required_document_refs",
                ))


def _check_action_resource_refs(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    fee_ids = {fee.fee_id for fee in analysis.fees if fee.fee_id}
    date_refs = {date.date_id for date in analysis.dates if date.date_id}
    date_refs.update(date.date_type.value for date in analysis.dates)
    urls = {link.url for link in analysis.links}
    for fee in analysis.fees:
        if (
            fee.payment_deadline_ref is not None
            and fee.payment_deadline_ref not in date_refs
        ):
            warnings.append(AnalysisWarning(
                code="dangling_deadline_ref",
                message=(
                    f"Fee {fee.fee_id!r} references missing date "
                    f"{fee.payment_deadline_ref!r}."
                ),
                severity="error",
                field_path=f"fees[{fee.fee_id}].payment_deadline_ref",
            ))
    for action in analysis.actions:
        if action.fee_ref is not None and action.fee_ref not in fee_ids:
            warnings.append(AnalysisWarning(
                code="dangling_fee_ref",
                message=f"Action {action.action_id!r} references missing fee {action.fee_ref!r}.",
                severity="error",
                field_path=f"actions[{action.action_id}].fee_ref",
            ))
        if action.deadline_ref is not None and action.deadline_ref not in date_refs:
            warnings.append(AnalysisWarning(
                code="dangling_deadline_ref",
                message=f"Action {action.action_id!r} references missing date {action.deadline_ref!r}.",
                severity="error",
                field_path=f"actions[{action.action_id}].deadline_ref",
            ))
        if action.url_ref is not None and action.url_ref not in urls:
            warnings.append(AnalysisWarning(
                code="dangling_url_ref",
                message=f"Action {action.action_id!r} references missing URL {action.url_ref!r}.",
                severity="error",
                field_path=f"actions[{action.action_id}].url_ref",
            ))


def _check_contradictory_fees(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    amounts: dict[tuple[str, str | None], set[float]] = defaultdict(set)
    for fee in analysis.fees:
        if fee.amount_inr is not None:
            amounts[(fee.fee_type, fee.applies_to_category)].add(fee.amount_inr)
    for (fee_type, category), values in amounts.items():
        if len(values) > 1:
            warnings.append(AnalysisWarning(
                code="contradictory_fee_amount",
                message=(
                    f"Fee type {fee_type!r} for category {category!r} has "
                    f"conflicting amounts {sorted(values)!r}."
                ),
                severity="warning",
                field_path="fees",
            ))


def _check_eligibility_ranges(
    analysis: NoticeAnalysis,
    warnings: list[AnalysisWarning],
) -> None:
    """Warn about obviously implausible eligibility thresholds."""
    if analysis.eligibility is None:
        return

    def check_condition(cond: Condition) -> None:
        if cond.attribute == "marks_percentage" and cond.value is not None:
            try:
                v = float(cond.value)
                if not (0.0 <= v <= 100.0):
                    warnings.append(AnalysisWarning(
                        code="implausible_percentage",
                        message=(
                            f"Condition {cond.condition_id!r} marks_percentage "
                            f"threshold {v} is outside [0, 100]."
                        ),
                        severity="warning",
                        evidence_ids=cond.evidence_ids,
                    ))
            except (TypeError, ValueError):
                pass

        if cond.attribute == "age" and cond.value is not None:
            try:
                v = float(cond.value)
                if not (0 <= v <= 120):
                    warnings.append(AnalysisWarning(
                        code="implausible_age",
                        message=(
                            f"Condition {cond.condition_id!r} age threshold "
                            f"{v} is outside [0, 120]."
                        ),
                        severity="warning",
                        evidence_ids=cond.evidence_ids,
                    ))
            except (TypeError, ValueError):
                pass

    _walk_condition_tree(
        analysis.eligibility,
        lambda node, _path: check_condition(node) if isinstance(node, Condition) else None,
        warnings,
        "eligibility",
    )
