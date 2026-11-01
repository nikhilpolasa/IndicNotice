"""NLP-4 evidence-gated hybrid semantic extractor."""

from __future__ import annotations

from typing import Sequence

from indicnotice.schemas.actions import ActionNode
from indicnotice.schemas.eligibility import Condition, ConditionGroup
from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.notice import AnalysisWarning, NoticeAnalysis
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.extraction.contextual.types import ContextualExtractionResult
from services.nlp.ingestion.types import IngestionResult
from services.nlp.semantic.canonical import canonical_condition, canonical_document, canonical_group, iter_conditions
from services.nlp.semantic.rules import SemanticRuleExtractor
from services.nlp.semantic.support import action_support, condition_support, document_support, group_support
from services.nlp.semantic.types import (
    CandidateOrigin,
    GateDecision,
    RejectionReason,
    SemanticConflict,
    SemanticDiagnostics,
    SemanticExtractionResult,
)
from services.nlp.validation.validator import validate_analysis


def _evidence_ids(group: ConditionGroup) -> list[str]:
    return list(dict.fromkeys(group.evidence_ids + [eid for item in iter_conditions(group) for eid in item.evidence_ids]))


def _combine_groups(groups: Sequence[ConditionGroup]) -> ConditionGroup | None:
    if not groups:
        return None
    children: list[Condition | ConditionGroup] = []
    seen: set[object] = set()
    for group in groups:
        candidates = group.children if group.operator == "AND" and group.applies_when is None else [group]
        for child in candidates:
            marker = canonical_condition(child) if isinstance(child, Condition) else canonical_group(child)
            if marker not in seen:
                seen.add(marker)
                children.append(child)
    return ConditionGroup(
        group_id="nlp4_eligibility_root",
        operator="AND",
        label="Evidence-gated hybrid eligibility",
        children=children,
        evidence_ids=list(dict.fromkeys(eid for group in groups for eid in _evidence_ids(group))),
    )


def _action_key(action: ActionNode) -> tuple[object, ...]:
    return (
        action.action_type.value,
        tuple(sorted(action.required_document_refs)),
        action.fee_ref,
        action.deadline_ref,
        action.channel,
        action.url_ref,
        canonical_group(action.applies_when),
        bool(action.is_optional),
        " ".join(action.description.split()).casefold()
        if not any((action.required_document_refs, action.fee_ref, action.deadline_ref, action.channel, action.url_ref, action.applies_when))
        else None,
    )


def _reindex_actions(actions: list[ActionNode]) -> list[ActionNode]:
    mapping = {item.action_id: f"action_{index + 1:03d}" for index, item in enumerate(actions)}
    return [
        item.model_copy(update={
            "action_id": mapping[item.action_id],
            "depends_on": [mapping[dep] for dep in item.depends_on if dep in mapping],
        })
        for item in actions
    ]


def _condition_semantics_equal(left: Condition, right: Condition) -> bool:
    """Treat a missing unit as weaker metadata when the rule itself is equal."""
    return canonical_condition(left.model_copy(update={"unit": None})) == canonical_condition(
        right.model_copy(update={"unit": None})
    )


def _conditions_conflict(left: Condition, right: Condition) -> bool:
    """Identify a narrow, safe conflict without treating all same-attribute rules as conflicts."""
    return (
        left.attribute.casefold() == right.attribute.casefold()
        and left.comparator == right.comparator
        and bool(left.negated) == bool(right.negated)
        and left.reference_date == right.reference_date
        and canonical_group(left.applies_when) == canonical_group(right.applies_when)
        and not _condition_semantics_equal(left, right)
    )


def _reconcile_contextual_group(
    candidate: ConditionGroup,
    existing: list[Condition],
    evidence_map: dict[str, EvidenceSpan],
    decisions: list[GateDecision],
    conflicts: list[SemanticConflict],
    *,
    path: str,
) -> ConditionGroup | None:
    """Keep supported novel AND children while preserving nested logic.

    OR subtrees are atomic for reconciliation: removing one branch would alter
    their meaning, so mixed duplicate/conflicting OR groups are rejected.
    """
    if candidate.operator == "OR" or candidate.applies_when is not None:
        support = group_support(candidate, evidence_map)
        ids = tuple(_evidence_ids(candidate))
        if not support.supported:
            decisions.append(GateDecision("eligibility", path, CandidateOrigin.CONTEXTUAL, False, ids, support.reason, support.detail))
            return None
        leaves = list(iter_conditions(candidate))
        if any(any(_condition_semantics_equal(item, prior) for prior in existing) for item in leaves):
            decisions.append(GateDecision("eligibility", path, CandidateOrigin.CONTEXTUAL, False, ids, RejectionReason.DUPLICATE, "OR/guarded subtree overlaps an existing condition and cannot be partially removed safely."))
            return None
        if any(any(_conditions_conflict(item, prior) for prior in existing) for item in leaves):
            decisions.append(GateDecision("eligibility", path, CandidateOrigin.CONTEXTUAL, False, ids, RejectionReason.CONFLICT, "OR/guarded subtree contains a conflicting condition."))
            return None
        existing.extend(leaves)
        decisions.append(GateDecision("eligibility", path, CandidateOrigin.CONTEXTUAL, True, ids))
        return candidate

    retained: list[Condition | ConditionGroup] = []
    for index, child in enumerate(candidate.children):
        child_path = f"{path}.children[{index}]"
        if isinstance(child, ConditionGroup):
            accepted = _reconcile_contextual_group(
                child, existing, evidence_map, decisions, conflicts, path=child_path
            )
            if accepted is not None:
                retained.append(accepted)
            continue
        support = condition_support(child, evidence_map)
        ids = tuple(child.evidence_ids)
        if not support.supported:
            decisions.append(GateDecision("eligibility", child_path, CandidateOrigin.CONTEXTUAL, False, ids, support.reason, support.detail))
            continue
        duplicate = next(
            (item for item in existing if _condition_semantics_equal(item, child)),
            None,
        )
        if duplicate is not None:
            decisions.append(GateDecision("eligibility", child_path, CandidateOrigin.CONTEXTUAL, False, ids, RejectionReason.DUPLICATE, "Atomic condition already exists."))
            continue
        conflict = next((item for item in existing if _conditions_conflict(item, child)), None)
        if conflict is not None:
            conflicts.append(SemanticConflict(
                child_path,
                canonical_condition(conflict),
                canonical_condition(child),
                tuple(conflict.evidence_ids),
                ids,
                "retained deterministic condition; rejected conflicting contextual condition",
            ))
            decisions.append(GateDecision("eligibility", child_path, CandidateOrigin.CONTEXTUAL, False, ids, RejectionReason.CONFLICT, "Same attribute/operator/guard has a different value."))
            continue
        retained.append(child)
        existing.append(child)
        decisions.append(GateDecision("eligibility", child_path, CandidateOrigin.CONTEXTUAL, True, ids))
    if not retained:
        return None
    return candidate.model_copy(update={"children": retained})


class EvidenceGatedSemanticExtractor:
    """Combine NLP-2 facts, bounded rules, and optional NLP-3 candidates."""

    method = "evidence-gated-semantic-nlp4-v1"

    def __init__(self) -> None:
        self.baseline = RegexBaselineExtractor()
        self.rules = SemanticRuleExtractor()

    def extract_ingestion(
        self,
        ingestion: IngestionResult,
        contextual: ContextualExtractionResult | NoticeAnalysis | None = None,
    ) -> SemanticExtractionResult:
        baseline = self.baseline.extract_ingestion(ingestion).analysis
        contextual_analysis = contextual.analysis if isinstance(contextual, ContextualExtractionResult) else contextual
        return self.combine(baseline, ingestion.evidence, contextual_analysis)

    def combine(
        self,
        baseline: NoticeAnalysis,
        evidence: Sequence[EvidenceSpan],
        contextual: NoticeAnalysis | None = None,
    ) -> SemanticExtractionResult:
        evidence_map = {item.evidence_id: item for item in evidence}
        semantic = self.rules.extract(evidence)
        decisions: list[GateDecision] = []
        conflicts: list[SemanticConflict] = []
        warnings = list(baseline.warnings)

        deterministic_groups = [item for item in (baseline.eligibility, semantic.eligibility) if item is not None]
        eligibility = _combine_groups(deterministic_groups)
        for group, path in ((baseline.eligibility, "eligibility.nlp2"), (semantic.eligibility, "eligibility.semantic_rules")):
            if group is not None:
                decisions.append(GateDecision("eligibility", path, CandidateOrigin.DETERMINISTIC, True, tuple(_evidence_ids(group))))

        actions: list[ActionNode] = []
        seen_actions: set[tuple[object, ...]] = set()
        for source, path in ((baseline.actions, "actions.nlp2"), (list(semantic.actions), "actions.semantic_rules")):
            for index, item in enumerate(source):
                marker = _action_key(item)
                if marker in seen_actions:
                    decisions.append(GateDecision("action", f"{path}[{index}]", CandidateOrigin.DETERMINISTIC, False, tuple(item.evidence_ids), RejectionReason.DUPLICATE, "Duplicate deterministic action."))
                    continue
                seen_actions.add(marker)
                actions.append(item)
                decisions.append(GateDecision("action", f"{path}[{index}]", CandidateOrigin.DETERMINISTIC, True, tuple(item.evidence_ids)))

        documents = list(baseline.required_documents)
        if contextual is not None:
            eligibility, documents, actions = self._merge_contextual(
                eligibility, documents, actions, contextual, evidence_map, decisions, conflicts,
            )
            self._record_strong_field_conflicts(baseline, contextual, decisions, conflicts)

        if conflicts:
            warnings.append(AnalysisWarning(
                code="nlp4_contextual_conflict",
                message=f"NLP-4 retained deterministic facts and surfaced {len(conflicts)} contextual conflict(s).",
                severity="warning",
                evidence_ids=list(dict.fromkeys(eid for item in conflicts for eid in item.deterministic_evidence_ids + item.contextual_evidence_ids)),
            ))
        rejected = sum(not item.promoted for item in decisions if item.origin == CandidateOrigin.CONTEXTUAL)
        if rejected:
            warnings.append(AnalysisWarning(
                code="nlp4_contextual_claims_rejected",
                message=f"Evidence/semantic gates rejected {rejected} contextual candidate claim(s).",
                severity="warning",
            ))
        for item in semantic.unresolved:
            warnings.append(AnalysisWarning(code="nlp4_semantic_unresolved", message=item, severity="info"))

        analysis = baseline.model_copy(update={
            "analysis_id": baseline.analysis_id.replace("nlp2:", "nlp4:", 1),
            "eligibility": eligibility,
            "required_documents": documents,
            "actions": _reindex_actions(actions),
            "warnings": warnings,
            "extractor_model": self.method,
        })
        analysis = validate_analysis(analysis)
        diagnostics = SemanticDiagnostics(
            decisions=tuple(decisions),
            conflicts=tuple(conflicts),
            unresolved=semantic.unresolved,
        )
        return SemanticExtractionResult(analysis, diagnostics)

    @staticmethod
    def _merge_contextual(
        eligibility: ConditionGroup | None,
        documents: list,
        actions: list[ActionNode],
        contextual: NoticeAnalysis,
        evidence_map: dict[str, EvidenceSpan],
        decisions: list[GateDecision],
        conflicts: list[SemanticConflict],
    ) -> tuple[ConditionGroup | None, list, list[ActionNode]]:
        if contextual.eligibility is not None:
            existing = list(iter_conditions(eligibility)) if eligibility else []
            accepted = _reconcile_contextual_group(
                contextual.eligibility,
                existing,
                evidence_map,
                decisions,
                conflicts,
                path="eligibility.contextual",
            )
            if accepted is not None:
                eligibility = _combine_groups([item for item in (eligibility, accepted) if item])

        document_keys = {canonical_document(item): position for position, item in enumerate(documents)}
        for index, item in enumerate(contextual.required_documents):
            support = document_support(item, evidence_map)
            marker = canonical_document(item)
            if marker in document_keys:
                position = document_keys[marker]
                existing = documents[position]
                documents[position] = existing.model_copy(update={
                    "evidence_ids": list(dict.fromkeys([*existing.evidence_ids, *item.evidence_ids]))
                })
                decisions.append(GateDecision("document", f"required_documents.contextual[{index}]", CandidateOrigin.CONTEXTUAL, False, tuple(item.evidence_ids), RejectionReason.DUPLICATE, "Document requirement already exists."))
            elif not support.supported:
                decisions.append(GateDecision("document", f"required_documents.contextual[{index}]", CandidateOrigin.CONTEXTUAL, False, tuple(item.evidence_ids), support.reason, support.detail))
            else:
                documents.append(item.model_copy(update={"doc_req_id": f"doc_{len(documents)+1:03d}"}))
                document_keys[marker] = len(documents) - 1
                decisions.append(GateDecision("document", f"required_documents.contextual[{index}]", CandidateOrigin.CONTEXTUAL, True, tuple(item.evidence_ids)))

        action_keys = {_action_key(item) for item in actions}
        contextual_by_id = {item.action_id: item for item in contextual.actions}
        for index, item in enumerate(contextual.actions):
            support = action_support(item, evidence_map, contextual_by_id)
            marker = _action_key(item)
            if marker in action_keys:
                decisions.append(GateDecision("action", f"actions.contextual[{index}]", CandidateOrigin.CONTEXTUAL, False, tuple(item.evidence_ids), RejectionReason.DUPLICATE, "Action already exists."))
            elif not support.supported:
                decisions.append(GateDecision("action", f"actions.contextual[{index}]", CandidateOrigin.CONTEXTUAL, False, tuple(item.evidence_ids), support.reason, support.detail))
            else:
                actions.append(item.model_copy(update={
                    "action_id": f"ctx_{item.action_id}",
                    "depends_on": [f"ctx_{dep}" for dep in item.depends_on],
                }))
                action_keys.add(marker)
                decisions.append(GateDecision("action", f"actions.contextual[{index}]", CandidateOrigin.CONTEXTUAL, True, tuple(item.evidence_ids)))
        return eligibility, documents, actions

    @staticmethod
    def _record_strong_field_conflicts(
        baseline: NoticeAnalysis,
        contextual: NoticeAnalysis,
        decisions: list[GateDecision],
        conflicts: list[SemanticConflict],
    ) -> None:
        pairs = (
            ("category", baseline.category, contextual.category, (), ()),
            ("dates", [(x.date_type.value, x.value) for x in baseline.dates], [(x.date_type.value, x.value) for x in contextual.dates], tuple(e for x in baseline.dates for e in x.evidence_ids), tuple(e for x in contextual.dates for e in x.evidence_ids)),
            ("fees", [(x.fee_type, x.amount_inr) for x in baseline.fees], [(x.fee_type, x.amount_inr) for x in contextual.fees], tuple(e for x in baseline.fees for e in x.evidence_ids), tuple(e for x in contextual.fees for e in x.evidence_ids)),
            ("links", [x.url for x in baseline.links], [x.url for x in contextual.links], tuple(e for x in baseline.links for e in x.evidence_ids), tuple(e for x in contextual.links for e in x.evidence_ids)),
        )
        for path, deterministic, candidate, det_ids, ctx_ids in pairs:
            if candidate in (None, []) or candidate == deterministic:
                continue
            conflicts.append(SemanticConflict(path, deterministic, candidate, det_ids, ctx_ids, "deterministic exact-value parser retained; contextual candidate requires review"))
            decisions.append(GateDecision(path, f"{path}.contextual", CandidateOrigin.CONTEXTUAL, False, ctx_ids, RejectionReason.CONFLICT, "Field-specific trust policy gives exact deterministic parsing precedence."))
