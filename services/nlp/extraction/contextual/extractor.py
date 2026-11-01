"""Evidence-grounded contextual extractor behind the frozen adapter boundary."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

from pydantic import ValidationError

from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.benefits import BenefitItem
from indicnotice.schemas.common import ReviewState
from indicnotice.schemas.dates import DatePrecision, DateRole, TypedDate
from indicnotice.schemas.document import Document
from indicnotice.schemas.documents_required import DocumentRequirement, RequirementType
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.fees import FeeItem
from indicnotice.schemas.links import LinkItem
from indicnotice.schemas.notice import AnalysisWarning, NoticeAnalysis, NoticeCategory, NoticeMetadata
from services.nlp.ingestion.types import IngestionResult
from services.nlp.validation.normalizers import normalize_inr
from services.nlp.validation.validator import validate_analysis
from services.nlp.validation.urls import canonicalize_url

from .context import DocumentChunk, build_chunks, evidence_from_document
from .errors import EvidenceValidationFailure, SchemaValidationFailure
from .schema import ModelChunkOutput, ModelCondition, ModelGroup, response_schema
from .types import (
    ChunkAttempt,
    ContextualExtractionResult,
    ExtractionDiagnostics,
    ModelRequest,
    StructuredModelProvider,
)


PROMPT_VERSION = "indicnotice-contextual-v1"
_PROMPT_DIR = Path(__file__).with_name("prompts")
_WS = re.compile(r"\s+")
_ALTERNATIVE_CUE = re.compile(r"\b(?:or|either|alternative)\b|या|अथवा|లేదా", re.I)
_DEPENDENCY_CUE = re.compile(r"\b(?:after|before|only after|then)\b|के बाद|से पहले|తర్వాత|అనంతరం|ముందు", re.I)
_MONTHS = {
    "january": 1, "jan": 1, "जनवरी": 1, "జనవరి": 1,
    "february": 2, "feb": 2, "फरवरी": 2, "ఫిబ్రవరి": 2,
    "march": 3, "mar": 3, "मार्च": 3, "మార్చి": 3,
    "april": 4, "apr": 4, "अप्रैल": 4, "ఏప్రిల్": 4,
    "may": 5, "मई": 5, "మే": 5,
    "june": 6, "jun": 6, "जून": 6, "జూన్": 6,
    "july": 7, "jul": 7, "जुलाई": 7, "జూలై": 7,
    "august": 8, "aug": 8, "अगस्त": 8, "ఆగస్టు": 8,
    "september": 9, "sep": 9, "sept": 9, "सितंबर": 9, "सितम्बर": 9, "సెప్టెంబర్": 9,
    "october": 10, "oct": 10, "अक्टूबर": 10, "అక్టోబర్": 10,
    "november": 11, "nov": 11, "नवंबर": 11, "नवम्बर": 11, "నవంబర్": 11,
    "december": 12, "dec": 12, "दिसंबर": 12, "दिसम्बर": 12, "డిసెంబర్": 12,
}
_MONTH_RE = "|".join(sorted((re.escape(item) for item in _MONTHS), key=len, reverse=True))
_NAMED_DATE = re.compile(rf"(?<!\d)(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})[,]?\s+(\d{{4}})(?!\d)", re.I)
_NUMERIC_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
_ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_ZERO_FEE_CONTEXT = re.compile(
    r"(?:\b(?:no|nil|zero)\s+(?:application\s+|exam(?:ination)?\s+|processing\s+)?(?:fee|charge)s?\b|"
    r"\b(?:fee|charge)s?\b.{0,30}\b(?:nil|zero|not\s+(?:charged|payable|required)|free)\b|"
    r"(?:\u0936\u0941\u0932\u094d\u0915|\u092b\u0940\u0938).{0,30}(?:\u0928\u0939\u0940\u0902|\u0928\u093f\u0903?\u0936\u0941\u0932\u094d\u0915)|"
    r"(?:\u0928\u093f\u0903?\u0936\u0941\u0932\u094d\u0915)|"
    r"(?:\u0c2b\u0c40\u0c1c\u0c41|\u0c30\u0c41\u0c38\u0c41\u0c2e\u0c41).{0,30}(?:\u0c32\u0c47\u0c26\u0c41|\u0c35\u0c38\u0c42\u0c32\u0c41\s*\u0c1a\u0c47\u0c2f\u0c2c\u0c21\u0c26\u0c41)|"
    r"(?:\u0c09\u0c1a\u0c3f\u0c24).{0,20}(?:\u0c26\u0c30\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41|\u0c05\u0c2a\u0c4d\u0c32\u0c3f\u0c15\u0c47\u0c37\u0c28))",
    re.I | re.S,
)
_CATEGORY_SUPPORT = {
    "scholarship": re.compile(r"scholarship|NMMSS|NMMS|\u091b\u093e\u0924\u094d\u0930\u0935[\u0943\u0941]\u0924|\u0c09\u0c2a\u0c15\u0c3e\u0c30\s*\u0c35\u0c47\u0c24\u0c28|\u0c38\u0c4d\u0c15\u0c3e\u0c32\u0c30", re.I),
    "examination": re.compile(r"exam(?:ination)?|test|\u092a\u0930\u0940\u0915\u094d\u0937\u093e|\u0c2a\u0c30\u0c40\u0c15\u0c4d\u0c37", re.I),
    "admission": re.compile(r"admission|\u092a\u094d\u0930\u0935\u0947\u0936|\u0c2a\u0c4d\u0c30\u0c35\u0c47\u0c36|\u0c05\u0c21\u0c4d\u0c2e\u0c3f\u0c37\u0c28\u0c4d", re.I),
    "recruitment": re.compile(r"recruitment|vacanc|\u092d\u0930\u094d\u0924\u0940|\u0c09\u0c26\u0c4d\u0c2f\u0c4b\u0c17|\u0c28\u0c3f\u0c2f\u0c3e\u0c2e\u0c15", re.I),
    "other": re.compile(r"notice|notification|prospectus|\u0938\u0942\u091a\u0928\u093e|\u0c38\u0c42\u0c1a\u0c28", re.I),
}
_DOCUMENT_OBLIGATION = re.compile(
    r"\b(?:must|required|shall|attach|enclos|upload|submit|provide|bring|produce)\b|"
    r"\u0905\u0928\u093f\u0935\u093e\u0930\u094d\u092f|\u0906\u0935\u0936\u094d\u092f\u0915|\u0905\u092a\u0932\u094b\u0921|\u091c\u092e\u093e|\u0938\u0902\u0932\u0917\u094d\u0928|"
    r"\u0c24\u0c2a\u0c4d\u0c2a\u0c28\u0c3f\u0c38\u0c30\u0c3f|\u0c05\u0c35\u0c38\u0c30\u0c02|\u0c05\u0c2a\u0c4d.?\u0c32\u0c4b\u0c21\u0c4d|\u0c38\u0c2e\u0c30\u0c4d\u0c2a\u0c3f\u0c02\u0c1a",
    re.I,
)
_DOCUMENT_SUBMISSION = re.compile(
    r"\b(?:attach|enclos|upload|submit|provide|bring|produce)\b|"
    r"\u0905\u092a\u0932\u094b\u0921|\u091c\u092e\u093e|\u0938\u0902\u0932\u0917\u094d\u0928|"
    r"\u0c05\u0c2a\u0c4d.?\u0c32\u0c4b\u0c21\u0c4d|\u0c38\u0c2e\u0c30\u0c4d\u0c2a\u0c3f\u0c02\u0c1a",
    re.I,
)
_DOCUMENT_REFERRAL_ONLY = re.compile(
    r"(?:visit|refer|see|consult|available).{0,55}(?:website|portal|online).{0,55}(?:details?|information)|"
    r"(?:details?|information).{0,55}(?:required documents?|documents required)",
    re.I | re.S,
)


def _normalized(value: str) -> str:
    return _WS.sub(" ", value).strip().casefold()


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _canonical_url(value: str) -> str:
    """Apply the same conservative ``www.`` normalization as NLP-2."""
    return canonicalize_url(value)


def _supported_dates(source: str) -> set[str]:
    """Parse only unambiguous source dates; no locale or OCR correction."""
    values: set[str] = set()
    for match in _ISO_DATE.finditer(source):
        try:
            values.add(date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat())
        except ValueError:
            pass
    for match in _NUMERIC_DATE.finditer(source):
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if day <= 12 and month <= 12:
            continue
        try:
            values.add(date(year, month, day).isoformat())
        except ValueError:
            pass
    for match in _NAMED_DATE.finditer(source):
        try:
            values.add(date(int(match.group(3)), _MONTHS[match.group(2).casefold()], int(match.group(1))).isoformat())
        except ValueError:
            pass
    return values


class ContextualStructuredExtractor:
    """Contextual model orchestration with deterministic validation/conversion."""

    def __init__(
        self,
        provider: StructuredModelProvider,
        *,
        max_chunk_chars: int = 3_000,
        hard_max_unit_chars: int = 24_000,
        timeout_seconds: float = 300.0,
        max_repair_attempts: int = 1,
        compact_context: bool = False,
    ):
        if max_repair_attempts not in {0, 1}:
            raise ValueError("Extraction permits zero or one bounded repair attempt")
        self.provider = provider
        self.max_chunk_chars = max_chunk_chars
        self.compact_context = compact_context
        self.hard_max_unit_chars = hard_max_unit_chars
        self.timeout_seconds = timeout_seconds
        self.max_repair_attempts = max_repair_attempts
        self.system_prompt = (_PROMPT_DIR / "system_v1.txt").read_text(encoding="utf-8")
        self.extraction_prompt = (_PROMPT_DIR / "extraction_v1.txt").read_text(encoding="utf-8")
        self.repair_prompt = (_PROMPT_DIR / "repair_v1.txt").read_text(encoding="utf-8")

    def extract(self, doc: Document) -> NoticeAnalysis:
        """Implement the frozen ``StructuredExtractor`` protocol."""
        return self.extract_with_evidence(doc, evidence_from_document(doc)).analysis

    def extract_ingestion(self, result: IngestionResult) -> ContextualExtractionResult:
        """Preferred entry point because it consumes exact NLP-1 evidence spans."""
        return self.extract_with_evidence(result.document, result.evidence)

    def extract_with_evidence(
        self,
        document: Document,
        evidence: Sequence[EvidenceSpan],
    ) -> ContextualExtractionResult:
        spans = tuple(item for item in evidence if item.document_id == document.document_id)
        chunks = build_chunks(
            document,
            spans,
            max_chars=self.max_chunk_chars,
            hard_max_unit_chars=self.hard_max_unit_chars,
            compact=self.compact_context,
        )
        outputs: list[ModelChunkOutput] = []
        attempts: list[ChunkAttempt] = []
        raw_responses: list[str] = []
        for chunk in chunks:
            output, chunk_attempts, chunk_raw = self._extract_chunk(document, chunk, spans, len(chunks))
            outputs.append(output)
            attempts.extend(chunk_attempts)
            raw_responses.extend(chunk_raw)
        try:
            analysis = self._to_analysis(
                document,
                spans,
                outputs,
                rejected_claims=sum(item.rejected_claims for item in attempts),
                evidence_realignments=sum(item.evidence_realignments for item in attempts),
            )
        except (ValidationError, ValueError) as exc:
            raise SchemaValidationFailure(
                f"Validated model output could not be converted to NoticeAnalysis 1.0: {exc}"
            ) from exc
        diagnostics = ExtractionDiagnostics(
            model_id=self.provider.model_id,
            prompt_version=PROMPT_VERSION,
            chunk_count=len(chunks),
            attempts=tuple(attempts),
            raw_responses=tuple(raw_responses),
        )
        return ContextualExtractionResult(analysis, diagnostics)

    def _extract_chunk(
        self,
        document: Document,
        chunk: DocumentChunk,
        spans: tuple[EvidenceSpan, ...],
        chunk_count: int,
    ) -> tuple[ModelChunkOutput, list[ChunkAttempt], list[str]]:
        prompt = self.extraction_prompt.format(
            document_id=document.document_id,
            chunk_number=chunk.index + 1,
            chunk_count=chunk_count,
            language=document.detected_language or "unknown",
            chunk_text=chunk.text,
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        allowed = set(chunk.evidence_ids)
        evidence_map = {item.evidence_id: item for item in spans if item.evidence_id in allowed}
        attempts: list[ChunkAttempt] = []
        raw: list[str] = []
        last_kind = "schema"
        last_error = "unknown validation error"
        for attempt_number in range(1, self.max_repair_attempts + 2):
            response = self.provider.complete(ModelRequest(tuple(messages), response_schema(), self.timeout_seconds))
            raw.append(response.text)
            schema_valid = False
            evidence_valid = False
            realignments = 0
            rejected_claims = 0
            try:
                payload = json.loads(response.text)
                self._expand_evidence_aliases(payload, dict(chunk.evidence_aliases))
                output = ModelChunkOutput.model_validate(payload)
                schema_valid = True
                realignments = self._realign_exact_evidence(output, evidence_map)
                self._validate_evidence(output, allowed, evidence_map)
                evidence_valid = True
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_kind = "evidence" if schema_valid else "schema"
                last_error = str(exc)
                if attempt_number > self.max_repair_attempts and schema_valid:
                    rejected_claims = self._sanitize_unsupported(output, allowed, evidence_map)
                    try:
                        self._validate_evidence(output, allowed, evidence_map)
                        evidence_valid = True
                    except ValueError as sanitized_exc:
                        last_error = str(sanitized_exc)
                    else:
                        attempts.append(
                            ChunkAttempt(
                                chunk.index,
                                attempt_number,
                                True,
                                True,
                                response.latency_seconds,
                                response.prompt_tokens,
                                response.completion_tokens,
                                f"Unsupported claims rejected after validation: {last_error[:1000]}",
                                realignments,
                                rejected_claims,
                            )
                        )
                        return output, attempts, raw
                attempts.append(
                    ChunkAttempt(
                        chunk.index,
                        attempt_number,
                        schema_valid,
                        evidence_valid,
                        response.latency_seconds,
                        response.prompt_tokens,
                        response.completion_tokens,
                        last_error[:2000],
                        realignments,
                        rejected_claims,
                    )
                )
                if attempt_number > self.max_repair_attempts:
                    break
                messages.extend(
                    [
                        {"role": "assistant", "content": response.text},
                        {
                            "role": "user",
                            "content": self.repair_prompt.format(
                                validation_errors=last_error[:3000],
                                previous_output=response.text,
                            ),
                        },
                    ]
                )
                continue
            attempts.append(
                ChunkAttempt(
                    chunk.index,
                    attempt_number,
                    True,
                    True,
                    response.latency_seconds,
                    response.prompt_tokens,
                    response.completion_tokens,
                    evidence_realignments=realignments,
                    rejected_claims=rejected_claims,
                )
            )
            return output, attempts, raw
        message = f"Chunk {chunk.index + 1} remained invalid after {self.max_repair_attempts} repair(s): {last_error[:2000]}"
        if last_kind == "evidence":
            raise EvidenceValidationFailure(message)
        raise SchemaValidationFailure(message)

    @staticmethod
    def _expand_evidence_aliases(value: Any, aliases: dict[str, str]) -> None:
        """Map compact prompt-local IDs back to canonical NLP-1 evidence IDs."""
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith("evidence_ids") and isinstance(item, list):
                    value[key] = [aliases.get(candidate, candidate) for candidate in item]
                else:
                    ContextualStructuredExtractor._expand_evidence_aliases(item, aliases)
        elif isinstance(value, list):
            for item in value:
                ContextualStructuredExtractor._expand_evidence_aliases(item, aliases)

    @staticmethod
    def _realign_ids(
        source_value: str | None,
        current: list[str],
        evidence_map: dict[str, EvidenceSpan],
    ) -> tuple[list[str], bool]:
        """Repair only exact textual provenance, never a semantic value."""
        if source_value is None:
            return current, False
        target = _normalized(source_value)
        current_text = "\n".join(evidence_map[eid].text for eid in current if eid in evidence_map)
        if target in _normalized(current_text):
            return current, False
        ordered = sorted(
            evidence_map.values(),
            key=lambda item: (
                item.page_number,
                item.char_start if item.char_start is not None else 10**9,
                item.evidence_id,
            ),
        )
        for start in range(len(ordered)):
            for width in range(1, min(3, len(ordered) - start) + 1):
                window = ordered[start:start + width]
                if len({item.page_number for item in window}) != 1:
                    break
                if target in _normalized("\n".join(item.text for item in window)):
                    return [item.evidence_id for item in window], True
        return current, False

    @classmethod
    def _realign_group(cls, group: ModelGroup | None, evidence_map: dict[str, EvidenceSpan]) -> int:
        if group is None:
            return 0
        count = cls._realign_group(group.applies_when, evidence_map)
        for child in group.children:
            if isinstance(child, ModelCondition):
                child.evidence_ids, changed = cls._realign_ids(child.source_text, child.evidence_ids, evidence_map)
                count += int(changed)
                count += cls._realign_group(child.applies_when, evidence_map)
            else:
                count += cls._realign_group(child, evidence_map)
        return count

    @classmethod
    def _realign_exact_evidence(
        cls,
        output: ModelChunkOutput,
        evidence_map: dict[str, EvidenceSpan],
    ) -> int:
        count = 0
        metadata_pairs = (
            ("title", "title_evidence_ids"),
            ("issuing_authority", "issuing_authority_evidence_ids"),
            ("notice_number", "notice_number_evidence_ids"),
            ("academic_year", "academic_year_evidence_ids"),
        )
        for value_attr, ids_attr in metadata_pairs:
            ids, changed = cls._realign_ids(
                getattr(output.metadata, value_attr),
                getattr(output.metadata, ids_attr),
                evidence_map,
            )
            setattr(output.metadata, ids_attr, ids)
            count += int(changed)
        for collection, value_attr in (
            (output.dates, "source_text"),
            (output.fees, "source_text"),
            (output.benefits, "source_text"),
            (output.required_documents, "source_name"),
            (output.actions, "description"),
            (output.links, "url"),
        ):
            for item in collection:
                item.evidence_ids, changed = cls._realign_ids(
                    getattr(item, value_attr), item.evidence_ids, evidence_map
                )
                count += int(changed)
                count += cls._realign_group(getattr(item, "applies_when", None), evidence_map)
        count += cls._realign_group(output.eligibility, evidence_map)
        return count

    @staticmethod
    def _source_supported(value: str, ids: list[str], evidence_map: dict[str, EvidenceSpan]) -> bool:
        if not ids or any(eid not in evidence_map for eid in ids):
            return False
        joined = "\n".join(evidence_map[eid].text for eid in ids)
        return _normalized(value) in _normalized(joined)

    @classmethod
    def _sanitize_group(
        cls,
        group: ModelGroup | None,
        allowed: set[str],
        evidence_map: dict[str, EvidenceSpan],
    ) -> tuple[ModelGroup | None, int]:
        if group is None:
            return None, 0
        rejected = 0
        group.evidence_ids = [eid for eid in group.evidence_ids if eid in allowed]
        group.applies_when, count = cls._sanitize_group(group.applies_when, allowed, evidence_map)
        rejected += count
        children = []
        for child in group.children:
            if isinstance(child, ModelCondition):
                child.applies_when, count = cls._sanitize_group(child.applies_when, allowed, evidence_map)
                rejected += count
                if cls._source_supported(child.source_text, child.evidence_ids, evidence_map):
                    children.append(child)
                else:
                    rejected += 1
            else:
                cleaned, count = cls._sanitize_group(child, allowed, evidence_map)
                rejected += count
                if cleaned is not None:
                    children.append(cleaned)
        group.children = children
        if not children:
            return None, rejected + 1
        return group, rejected

    @classmethod
    def _sanitize_unsupported(
        cls,
        output: ModelChunkOutput,
        allowed: set[str],
        evidence_map: dict[str, EvidenceSpan],
    ) -> int:
        """Reject unsupported claims after the sole repair; never alter their values."""
        rejected = 0
        if output.category is not None and not cls._category_supported(
            output.category, output.category_evidence_ids, allowed, evidence_map
        ):
            output.category = None
            output.category_evidence_ids = []
            rejected += 1
        metadata_pairs = (
            ("title", "title_evidence_ids"),
            ("issuing_authority", "issuing_authority_evidence_ids"),
            ("notice_number", "notice_number_evidence_ids"),
            ("academic_year", "academic_year_evidence_ids"),
        )
        for value_attr, ids_attr in metadata_pairs:
            value = getattr(output.metadata, value_attr)
            ids = getattr(output.metadata, ids_attr)
            if value is not None and not cls._source_supported(value, ids, evidence_map):
                setattr(output.metadata, value_attr, None)
                setattr(output.metadata, ids_attr, [])
                rejected += 1

        kept_dates = []
        for item in output.dates:
            valid = cls._source_supported(item.source_text, item.evidence_ids, evidence_map)
            valid = valid and any(value is not None for value in (item.value, item.end_value, item.time))
            supported = _supported_dates(item.source_text)
            valid = valid and (item.value is None or item.value in supported)
            valid = valid and (item.end_value is None or item.end_value in supported)
            if item.time is not None and valid:
                joined = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
                times = {
                    f"{int(hour):02d}:{minute}"
                    for hour, minute in re.findall(r"(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)", joined)
                }
                valid = item.time[:5] in times
            if valid:
                kept_dates.append(item)
            else:
                rejected += 1
        output.dates = kept_dates

        for name in ("fees", "benefits"):
            kept = []
            for item in getattr(output, name):
                valid = cls._source_supported(item.source_text, item.evidence_ids, evidence_map)
                if valid:
                    try:
                        cls._validate_amount(item.amount_inr, item.source_text, name)
                    except ValueError:
                        valid = False
                if valid:
                    kept.append(item)
                else:
                    rejected += 1
            setattr(output, name, kept)

        kept_documents = []
        for item in output.required_documents:
            valid = cls._source_supported(item.source_name, item.evidence_ids, evidence_map)
            if valid:
                joined = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
                valid = cls._document_requirement_supported(
                    item.requirement_type, item.applies_when, joined
                )
            if item.alternatives and valid:
                joined = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
                valid = bool(_ALTERNATIVE_CUE.search(joined))
            item.applies_when, count = cls._sanitize_group(item.applies_when, allowed, evidence_map)
            rejected += count
            if valid:
                kept_documents.append(item)
            else:
                rejected += 1
        output.required_documents = kept_documents
        output.eligibility, count = cls._sanitize_group(output.eligibility, allowed, evidence_map)
        rejected += count

        kept_actions = []
        seen_action_ids: set[str] = set()
        for item in output.actions:
            if item.action_id in seen_action_ids:
                rejected += 1
                continue
            seen_action_ids.add(item.action_id)
            valid = cls._source_supported(item.description, item.evidence_ids, evidence_map)
            item.applies_when, count = cls._sanitize_group(item.applies_when, allowed, evidence_map)
            rejected += count
            if item.depends_on and valid:
                joined = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
                if not _DEPENDENCY_CUE.search(joined):
                    item.depends_on = []
                    rejected += 1
            if valid:
                kept_actions.append(item)
            else:
                rejected += 1
        output.actions = kept_actions
        original_links = output.links
        output.links = [
            item for item in output.links
            if cls._source_supported(item.url, item.evidence_ids, evidence_map)
        ]
        rejected += len(original_links) - len(output.links)
        return rejected

    @staticmethod
    def _validate_evidence(
        output: ModelChunkOutput,
        allowed: set[str],
        evidence_map: dict[str, EvidenceSpan],
    ) -> None:
        references: list[tuple[str, list[str], str | None]] = [
            ("category", output.category_evidence_ids, None),
            ("metadata.title", output.metadata.title_evidence_ids, output.metadata.title),
            (
                "metadata.issuing_authority",
                output.metadata.issuing_authority_evidence_ids,
                output.metadata.issuing_authority,
            ),
            (
                "metadata.notice_number",
                output.metadata.notice_number_evidence_ids,
                output.metadata.notice_number,
            ),
            (
                "metadata.academic_year",
                output.metadata.academic_year_evidence_ids,
                output.metadata.academic_year,
            ),
        ]
        for index, item in enumerate(output.dates):
            references.append((f"dates[{index}]", item.evidence_ids, item.source_text))
        for index, item in enumerate(output.fees):
            references.append((f"fees[{index}]", item.evidence_ids, item.source_text))
        for index, item in enumerate(output.benefits):
            references.append((f"benefits[{index}]", item.evidence_ids, item.source_text))
        for index, item in enumerate(output.required_documents):
            references.append((f"required_documents[{index}]", item.evidence_ids, item.source_name))
            ContextualStructuredExtractor._collect_group_references(item.applies_when, references, f"required_documents[{index}].applies_when")
        ContextualStructuredExtractor._collect_group_references(output.eligibility, references, "eligibility")
        for index, item in enumerate(output.actions):
            references.append((f"actions[{index}]", item.evidence_ids, item.description))
            ContextualStructuredExtractor._collect_group_references(item.applies_when, references, f"actions[{index}].applies_when")
        for index, item in enumerate(output.links):
            references.append((f"links[{index}]", item.evidence_ids, item.url))

        for path, evidence_ids, source_value in references:
            unknown = set(evidence_ids) - allowed
            if unknown:
                raise ValueError(f"{path} cites unavailable evidence IDs: {sorted(unknown)}")
            if source_value is None:
                continue
            joined = "\n".join(evidence_map[item].text for item in evidence_ids)
            if _normalized(source_value) not in _normalized(joined):
                raise ValueError(f"{path} source value is not present in its cited evidence")

        if output.category is not None and not ContextualStructuredExtractor._category_supported(
            output.category, output.category_evidence_ids, allowed, evidence_map
        ):
            raise ValueError("category is not semantically supported by cited evidence")

        for index, item in enumerate(output.fees):
            ContextualStructuredExtractor._validate_amount(item.amount_inr, item.source_text, f"fees[{index}]")
        for index, item in enumerate(output.benefits):
            ContextualStructuredExtractor._validate_amount(item.amount_inr, item.source_text, f"benefits[{index}]")
        for index, item in enumerate(output.dates):
            if item.value is None and item.end_value is None and item.time is None:
                raise ValueError(f"dates[{index}] has no supported date or time value")
            supported_dates = _supported_dates(item.source_text)
            if item.value is not None and item.value not in supported_dates:
                raise ValueError(f"dates[{index}] normalized value is not deterministically supported by source_text")
            if item.end_value is not None and item.end_value not in supported_dates:
                raise ValueError(f"dates[{index}] end_value is not deterministically supported by source_text")
            if item.time is not None:
                date_evidence = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
                source_times = {
                    f"{int(hour):02d}:{minute}"
                    for hour, minute in re.findall(r"(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)", date_evidence)
                }
                if item.time[:5] not in source_times:
                    raise ValueError(f"dates[{index}] time is not stated in cited evidence")
        for index, item in enumerate(output.required_documents):
            joined = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
            if not ContextualStructuredExtractor._document_requirement_supported(
                item.requirement_type, item.applies_when, joined
            ):
                raise ValueError(
                    f"required_documents[{index}] lacks a supported requirement relation"
                )
            if item.alternatives:
                if not _ALTERNATIVE_CUE.search(joined):
                    raise ValueError(
                        f"required_documents[{index}] alternatives lack an explicit alternative cue"
                    )
        for index, item in enumerate(output.actions):
            if item.depends_on:
                joined = "\n".join(evidence_map[eid].text for eid in item.evidence_ids)
                if not _DEPENDENCY_CUE.search(joined):
                    raise ValueError(
                        f"actions[{index}] dependency lacks an explicit ordering cue"
                    )

    @staticmethod
    def _validate_amount(value: float | None, source: str, path: str) -> None:
        if value is None:
            return
        parsed = normalize_inr(source)
        if value == 0 and _ZERO_FEE_CONTEXT.search(source):
            return
        if parsed is None or abs(parsed - value) > 0.01:
            raise ValueError(f"{path} amount does not deterministically match source_text")

    @staticmethod
    def _category_supported(
        category: str,
        evidence_ids: list[str],
        allowed: set[str],
        evidence_map: dict[str, EvidenceSpan],
    ) -> bool:
        if not evidence_ids or any(
            evidence_id not in allowed or evidence_id not in evidence_map
            for evidence_id in evidence_ids
        ):
            return False
        text = "\n".join(evidence_map[evidence_id].text for evidence_id in evidence_ids)
        cue = _CATEGORY_SUPPORT.get(category)
        return bool(cue and cue.search(text))

    @staticmethod
    def _document_requirement_supported(
        requirement_type: str,
        applies_when: ModelGroup | None,
        text: str,
    ) -> bool:
        if _DOCUMENT_REFERRAL_ONLY.search(text) and not _DOCUMENT_SUBMISSION.search(text):
            return False
        if requirement_type == "optional":
            return bool(
                re.search(
                    r"\b(?:may|optional|if available)\b|\u0935\u0948\u0915\u0932\u094d\u092a\u093f\u0915|\u0c10\u0c1a\u0c4d\u0c1b\u0c3f\u0c15",
                    text,
                    re.I,
                )
            )
        if not _DOCUMENT_OBLIGATION.search(text):
            return False
        if requirement_type == "conditional" and applies_when is None:
            return False
        return True

    @staticmethod
    def _collect_group_references(
        group: ModelGroup | None,
        references: list[tuple[str, list[str], str | None]],
        path: str,
    ) -> None:
        if group is None:
            return
        if group.evidence_ids:
            references.append((path, group.evidence_ids, None))
        if group.applies_when:
            ContextualStructuredExtractor._collect_group_references(group.applies_when, references, f"{path}.applies_when")
        for index, child in enumerate(group.children):
            child_path = f"{path}.children[{index}]"
            if isinstance(child, ModelCondition):
                references.append((child_path, child.evidence_ids, child.source_text))
                if child.applies_when:
                    ContextualStructuredExtractor._collect_group_references(child.applies_when, references, f"{child_path}.applies_when")
            else:
                ContextualStructuredExtractor._collect_group_references(child, references, child_path)

    def _to_analysis(
        self,
        document: Document,
        evidence: tuple[EvidenceSpan, ...],
        outputs: list[ModelChunkOutput],
        *,
        rejected_claims: int = 0,
        evidence_realignments: int = 0,
    ) -> NoticeAnalysis:
        warnings: list[AnalysisWarning] = []
        if rejected_claims:
            warnings.append(
                AnalysisWarning(
                    code="unsupported_model_claims_rejected",
                    message=f"Deterministic grounding rejected {rejected_claims} unsupported model claim(s).",
                    severity="warning",
                )
            )
        if evidence_realignments:
            warnings.append(
                AnalysisWarning(
                    code="evidence_realignments",
                    message=f"Deterministic exact-text matching realigned {evidence_realignments} evidence reference(s).",
                    severity="info",
                )
            )
        category = self._select_scalar([(item.category, item.category_evidence_ids) for item in outputs], "category", warnings)
        title = self._select_scalar([(item.metadata.title, item.metadata.title_evidence_ids) for item in outputs], "metadata.title", warnings)
        authority = self._select_scalar([(item.metadata.issuing_authority, item.metadata.issuing_authority_evidence_ids) for item in outputs], "metadata.issuing_authority", warnings)
        notice_number = self._select_scalar([(item.metadata.notice_number, item.metadata.notice_number_evidence_ids) for item in outputs], "metadata.notice_number", warnings)
        academic_year = self._select_scalar([(item.metadata.academic_year, item.metadata.academic_year_evidence_ids) for item in outputs], "metadata.academic_year", warnings)
        metadata = NoticeMetadata(
            title=title[0],
            title_evidence_ids=title[1],
            issuing_authority=authority[0],
            issuing_authority_evidence_ids=authority[1],
            notice_number=notice_number[0],
            notice_number_evidence_ids=notice_number[1],
            academic_year=academic_year[0],
        )
        dates = self._convert_dates(outputs, warnings)
        publication = next((item for item in dates if item.date_type == DateRole.PUBLICATION_DATE and item.value), None)
        if publication:
            metadata = metadata.model_copy(update={"publication_date": publication.value, "publication_date_evidence_ids": publication.evidence_ids})
        fees = self._convert_fees(outputs, warnings)
        benefits = self._convert_benefits(outputs, warnings)
        documents = self._convert_documents(outputs, warnings)
        eligibility = self._convert_eligibility(outputs, warnings)
        links = self._convert_links(outputs, warnings)
        actions = self._convert_actions(outputs, dates, fees, documents, links, warnings)
        model_hash = sha256(self.provider.model_id.encode("utf-8")).hexdigest()[:12]
        analysis = NoticeAnalysis(
            analysis_id=f"nlp3:{model_hash}:{document.document_id}",
            document_id=document.document_id,
            source_language=document.detected_language,
            category=NoticeCategory(category[0]) if category[0] else None,
            category_confidence=None,
            metadata=metadata,
            dates=dates,
            fees=fees,
            benefits=benefits,
            required_documents=documents,
            eligibility=eligibility,
            actions=actions,
            links=links,
            evidence=list(evidence),
            warnings=warnings,
            overall_review_state=ReviewState.NEEDS_REVIEW if warnings else ReviewState.AUTO_EXTRACTED,
            extractor_model=self.provider.model_id,
            extraction_timestamp=None,
        )
        return validate_analysis(analysis)

    @staticmethod
    def _select_scalar(
        candidates: list[tuple[str | None, list[str]]],
        path: str,
        warnings: list[AnalysisWarning],
    ) -> tuple[str | None, list[str]]:
        populated = [(value, ids) for value, ids in candidates if value is not None]
        if not populated:
            return None, []
        first_value, first_ids = populated[0]
        conflicts = [(value, ids) for value, ids in populated[1:] if _normalized(value or "") != _normalized(first_value or "")]
        if conflicts:
            warnings.append(
                AnalysisWarning(
                    code="contextual_conflict",
                    message=f"Conflicting contextual values for {path}; retained the earliest source-order value.",
                    field_path=path,
                    evidence_ids=_unique(first_ids + [eid for _, ids in conflicts for eid in ids]),
                )
            )
        return first_value, _unique(first_ids)

    @staticmethod
    def _dedupe(items: list[Any], key: Any, warnings: list[AnalysisWarning], path: str) -> list[Any]:
        result: list[Any] = []
        positions: dict[Any, int] = {}
        for item in items:
            marker = key(item)
            if marker in positions:
                existing_index = positions[marker]
                existing = result[existing_index]
                merged_ids = _unique(existing.evidence_ids + item.evidence_ids)
                result[existing_index] = existing.model_copy(update={"evidence_ids": merged_ids})
                warnings.append(
                    AnalysisWarning(
                        code="contextual_duplicate_merged",
                        message=f"Duplicate {path} item was merged deterministically.",
                        field_path=path,
                        evidence_ids=merged_ids,
                        severity="info",
                    )
                )
            else:
                positions[marker] = len(result)
                result.append(item)
        return result

    def _convert_dates(self, outputs: list[ModelChunkOutput], warnings: list[AnalysisWarning]) -> list[TypedDate]:
        items: list[TypedDate] = []
        for output in outputs:
            for item in output.dates:
                items.append(
                    TypedDate(
                        date_id=f"date_{len(items)+1:03d}",
                        date_type=DateRole(item.date_type),
                        value=item.value,
                        end_value=item.end_value,
                        time=item.time,
                        timezone=item.timezone,
                        source_text=item.source_text,
                        precision=DatePrecision(item.precision),
                        is_tentative=item.is_tentative,
                        mandatory=item.mandatory,
                        evidence_ids=item.evidence_ids,
                    )
                )
        result = self._dedupe(items, lambda item: (item.date_type, item.value, item.end_value, item.time, _normalized(item.source_text or "")), warnings, "dates")
        return [item.model_copy(update={"date_id": f"date_{index+1:03d}"}) for index, item in enumerate(result)]

    def _convert_fees(self, outputs: list[ModelChunkOutput], warnings: list[AnalysisWarning]) -> list[FeeItem]:
        flattened = [item for output in outputs for item in output.fees]
        items = [
            FeeItem(
                fee_id=f"fee_{index+1:03d}",
                fee_type=item.fee_type,
                amount_inr=item.amount_inr,
                source_text=item.source_text,
                applies_to_category=item.applies_to_category,
                waived_for=item.waived_for,
                payment_mode=item.payment_mode,
                is_refundable=item.is_refundable,
                evidence_ids=item.evidence_ids,
            )
            for index, item in enumerate(flattened)
        ]
        result = self._dedupe(items, lambda item: (item.fee_type, item.amount_inr, item.applies_to_category, item.waived_for), warnings, "fees")
        return [item.model_copy(update={"fee_id": f"fee_{index+1:03d}"}) for index, item in enumerate(result)]

    def _convert_benefits(self, outputs: list[ModelChunkOutput], warnings: list[AnalysisWarning]) -> list[BenefitItem]:
        flattened = [item for output in outputs for item in output.benefits]
        items = [
            BenefitItem(
                benefit_id=f"benefit_{index+1:03d}",
                benefit_type=item.benefit_type,
                amount_inr=item.amount_inr,
                description=item.description,
                source_text=item.source_text,
                applies_to=item.applies_to,
                frequency=item.frequency,
                evidence_ids=item.evidence_ids,
            )
            for index, item in enumerate(flattened)
        ]
        result = self._dedupe(items, lambda item: (item.benefit_type, item.amount_inr, item.applies_to, item.frequency), warnings, "benefits")
        return [item.model_copy(update={"benefit_id": f"benefit_{index+1:03d}"}) for index, item in enumerate(result)]

    def _convert_documents(self, outputs: list[ModelChunkOutput], warnings: list[AnalysisWarning]) -> list[DocumentRequirement]:
        items: list[DocumentRequirement] = []
        for chunk_index, output in enumerate(outputs):
            for item in output.required_documents:
                items.append(
                    DocumentRequirement(
                        doc_req_id=f"doc_{len(items)+1:03d}",
                        canonical_name=item.canonical_name,
                        source_name=item.source_name,
                        requirement_type=RequirementType(item.requirement_type),
                        applies_when=self._convert_group(item.applies_when, f"c{chunk_index}_"),
                        alternatives=item.alternatives,
                        notes=item.notes,
                        evidence_ids=item.evidence_ids,
                    )
                )
        from services.nlp.semantic.canonical import canonical_document

        result: list[DocumentRequirement] = []
        positions: dict[tuple[object, ...], int] = {}
        for item in items:
            marker = canonical_document(item)
            if marker not in positions:
                positions[marker] = len(result)
                result.append(item)
                continue
            position = positions[marker]
            prior = result[position]
            result[position] = prior.model_copy(update={
                "evidence_ids": _unique([*prior.evidence_ids, *item.evidence_ids])
            })
            warnings.append(AnalysisWarning(
                code="contextual_duplicate",
                message="Duplicate required_documents candidate merged with its evidence provenance.",
                field_path="required_documents",
                severity="info",
                evidence_ids=item.evidence_ids,
            ))
        return [item.model_copy(update={"doc_req_id": f"doc_{index+1:03d}"}) for index, item in enumerate(result)]

    def _convert_eligibility(self, outputs: list[ModelChunkOutput], warnings: list[AnalysisWarning]) -> ConditionGroup | None:
        groups = [self._convert_group(item.eligibility, f"c{index}_") for index, item in enumerate(outputs) if item.eligibility]
        groups = [item for item in groups if item is not None]
        if not groups:
            return None
        if len(groups) == 1:
            return groups[0]
        evidence_ids = _unique(eid for group in groups for eid in group.evidence_ids)
        warnings.append(
            AnalysisWarning(
                code="contextual_chunk_merge",
                message="Eligibility groups from multiple context chunks were joined with AND; review cross-chunk logic.",
                field_path="eligibility",
                evidence_ids=evidence_ids,
                severity="info",
            )
        )
        return ConditionGroup(group_id="eligibility_root", operator="AND", label="Merged explicit eligibility conditions", children=groups, evidence_ids=evidence_ids)

    def _convert_group(self, group: ModelGroup | None, prefix: str) -> ConditionGroup | None:
        if group is None:
            return None
        children: list[Condition | ConditionGroup] = []
        for child in group.children:
            if isinstance(child, ModelCondition):
                children.append(
                    Condition(
                        condition_id=f"{prefix}{child.condition_id}",
                        attribute=child.attribute,
                        comparator=Comparator(child.comparator),
                        value=child.value,
                        unit=child.unit,
                        negated=child.negated,
                        scope=child.scope,
                        exception_of=f"{prefix}{child.exception_of}" if child.exception_of else None,
                        applies_when=self._convert_group(child.applies_when, prefix),
                        reference_date=child.reference_date,
                        source_text=child.source_text,
                        evidence_ids=child.evidence_ids,
                    )
                )
            else:
                converted = self._convert_group(child, prefix)
                if converted:
                    children.append(converted)
        return ConditionGroup(
            group_id=f"{prefix}{group.group_id}" if group.group_id else None,
            operator=group.operator,
            label=group.label,
            applies_when=self._convert_group(group.applies_when, prefix),
            children=children,
            evidence_ids=group.evidence_ids,
        )

    def _convert_links(self, outputs: list[ModelChunkOutput], warnings: list[AnalysisWarning]) -> list[LinkItem]:
        items = [
            LinkItem(
                url=_canonical_url(item.url),
                link_type=item.link_type,
                description=item.description,
                evidence_ids=item.evidence_ids,
            )
            for output in outputs
            for item in output.links
        ]
        return self._dedupe(
            items,
            lambda item: (item.url, item.link_type, _normalized(item.description or "")),
            warnings,
            "links",
        )

    def _convert_actions(
        self,
        outputs: list[ModelChunkOutput],
        dates: list[TypedDate],
        fees: list[FeeItem],
        documents: list[DocumentRequirement],
        links: list[LinkItem],
        warnings: list[AnalysisWarning],
    ) -> list[ActionNode]:
        actions: list[ActionNode] = []
        for chunk_index, output in enumerate(outputs):
            local_ids = {item.action_id: f"action_{len(actions)+offset+1:03d}" for offset, item in enumerate(output.actions)}
            for item in output.actions:
                doc_refs = [doc.doc_req_id for doc in documents if doc.canonical_name in item.required_document_names]
                fee = next((candidate for candidate in fees if candidate.fee_type == item.fee_type), None)
                deadline = next((candidate for candidate in dates if candidate.date_type.value == item.deadline_type), None)
                link = next(
                    (
                        candidate
                        for candidate in links
                        if item.url is not None and candidate.url == _canonical_url(item.url)
                    ),
                    None,
                )
                dependencies = [local_ids[dep] for dep in item.depends_on if dep in local_ids]
                if len(dependencies) != len(item.depends_on):
                    warnings.append(
                        AnalysisWarning(
                            code="contextual_dangling_dependency_removed",
                            message="An action dependency not present in the same evidence chunk was removed.",
                            field_path="actions.depends_on",
                            evidence_ids=item.evidence_ids,
                        )
                    )
                actions.append(
                    ActionNode(
                        action_id=local_ids[item.action_id],
                        action_type=ActionType(item.action_type),
                        description=item.description,
                        depends_on=dependencies,
                        required_document_refs=doc_refs,
                        fee_ref=fee.fee_id if fee else None,
                        deadline_ref=deadline.date_id if deadline else None,
                        channel=item.channel,
                        url_ref=link.url if link else None,
                        applies_when=self._convert_group(item.applies_when, f"c{chunk_index}_"),
                        is_optional=item.is_optional,
                        evidence_ids=item.evidence_ids,
                    )
                )
        return self._dedupe(actions, lambda item: (item.action_type, _normalized(item.description), tuple(item.depends_on)), warnings, "actions")
