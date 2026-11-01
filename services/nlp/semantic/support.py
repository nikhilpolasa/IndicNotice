"""Field-specific semantic support gates for NLP-4 candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Mapping

from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.documents_required import DocumentRequirement, RequirementType
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.semantic.types import RejectionReason
from services.nlp.validation.normalizers import normalize_inr
from services.nlp.semantic.vocabulary import controlled_value_supported


_WS = re.compile(r"\s+")
_NUMBER = re.compile(r"(?<!\w)(\d[\d,]*(?:\.\d+)?)(?:\s*(lakh|lac|करोड़|लाख|లక్ష|కోటి))?", re.I)
_DATE = re.compile(r"(?<!\d)(?:(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})|(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}))(?!\d)")

_ATTRIBUTE_CUES: dict[str, re.Pattern[str]] = {
    "age": re.compile(r"\bage\b|आयु|उम्र|वर्ष|వయస్సు|ఏళ్ల", re.I),
    "annual_family_income_inr": re.compile(r"income|आय|आमदनी|ఆదాయం", re.I),
    "marks_percentage": re.compile(r"marks?|percentage|प्रतिशत|अंक|మార్కులు|శాతం", re.I),
    "category": re.compile(r"category|वर्ग|श्रेणी|కేటగిరీ|వర్గం|\b(?:SC|ST|OBC|EWS|PwD)\b", re.I),
    "course": re.compile(r"course|degree|qualification|योग्यता|डिग्री|అర్హత|డిగ్రీ|B\.?\s*Tech|B\.?\s*E\.?,?", re.I),
    "education_level": re.compile(r"education|degree|qualification|pass|योग्यता|उत्तीर्ण|అర్హత|ఉత్తీర్ణ|B\.?\s*Tech|B\.?\s*E\.?,?", re.I),
    "state": re.compile(r"state|राज्य|प्रदेश|రాష్ట్రం", re.I),
    "domicile": re.compile(r"domicile|resident|residence|निवासी|अधिवास|నివాసి|స్థానిక", re.I),
    "disability_status": re.compile(r"disability|persons? with disabilit|PwD|दिव्यांग|विकलांग|దివ్యాంగ", re.I),
    "gender": re.compile(r"women|woman|female|महिला|स्त्री|మహిళ", re.I),
    "date_of_birth": re.compile(r"date of birth|born|जन्म|పుట్టిన|జన్మ", re.I),
    "current_class": re.compile(r"current(?:ly)?\s+stud|studying|class|अध्ययनरत|कक्षा|తరగతి", re.I),
    "previous_class": re.compile(r"passed|completed|previous|उत्तीर्ण|पास|పాస|ఉత్తీర్ణ", re.I),
    "current_school_type": re.compile(r"school|institution|government|aided|सरकारी|अनुदान|विद्यालय|ववद्या|విద్యాలయ|పాఠశాల", re.I),
    "previous_school_type": re.compile(r"school|institution|government|aided|सरकारी|अनुदान|विद्यालय|ववद्या|విద్యాలయ|పాఠశాల", re.I),
    "attempt_count": re.compile(r"attempt|sit for|appear|बार|बैठ|ప్రయత్న|హాజరు", re.I),
    "selection_status": re.compile(r"selected|selection|चयनित|मेरिट|ఎంపిక", re.I),
}

_PREFERENCE = re.compile(
    r"preference|preferred|desirable|वांछनीय|वरीयता|प्राथमिकता|ప్రాధాన్యత|కావాల్సిన|desirous",
    re.I,
)
_OPERATOR_CUES: dict[Comparator, re.Pattern[str]] = {
    Comparator.LTE: re.compile(r"<=|not (?:more|greater) than|not exceeding|does not exceed|at most|up to|maximum|only once|one time|अधिक नहीं|अधिकतम|तक|केवल\s*एक\s*बार|మించకూడదు|గరిష్ట|వరకు|ఒక్కసారి", re.I),
    Comparator.LT: re.compile(r"(?<![<])<(?![=])|less than|below|under|से कम|కంటే తక్కువ", re.I),
    Comparator.GTE: re.compile(r">=|at least|not less than|minimum|कम नहीं|न्यूनतम|कम से कम|కనీసం|తక్కువ కాకుండా", re.I),
    Comparator.GT: re.compile(r"(?<![>])>(?![=])|more than|greater than|above|से अधिक|కంటే ఎక్కువ", re.I),
    Comparator.BETWEEN: re.compile(r"between|from.{0,40}(?:to|and)|के बीच|से.{0,30}तक|మధ్య|నుండి.{0,30}వరకు", re.I | re.S),
    Comparator.NEQ: re.compile(r"!=|not equal|other than|except|exempt|नहीं|के अलावा|छूट|కాదు|మినహా|మినహాయింపు", re.I),
    Comparator.NOT_IN: re.compile(r"not in|except|excluding|may not|cannot|not eligible|के अलावा|को छोड़कर|नहीं.{0,30}(?:बैठ|आवेदन)|మినహా|అర్హులు కాదు", re.I | re.S),
}
_REQUIREMENT = re.compile(r"must|required|shall|should possess|essential|अनिवार्य|आवश्यक|होना चाहिए|తప్పనిసరి|కలిగి ఉండాలి|అవసరం", re.I)
_DOCUMENT_SUBMISSION = re.compile(
    r"\b(?:attach|enclos|upload|submit|provide|bring|produce|must have|shall have)\b|"
    r"अपलोड|जमा|संलग्न|साथ लाय|प्रस्तुत|అప్.?లోడ్|సమర్పించ|జత|తీసుకురా",
    re.I,
)
_DOCUMENT_REFERRAL_ONLY = re.compile(
    r"(?:visit|refer|see|consult|available).{0,55}(?:website|portal|online).{0,55}(?:details?|information)|"
    r"(?:details?|information).{0,55}(?:required documents?|documents required)",
    re.I | re.S,
)
_ALTERNATIVE = re.compile(r"\bor\b|either|या|अथवा|లేదా", re.I)
_OPTIONAL = re.compile(r"\bmay\b|optional|if desired|for (?:their|your) records|वैकल्पिक|कर सकते हैं|ఐచ్ఛిక|చేయవచ్చు", re.I)
_CONDITIONAL = re.compile(r"\bif\b|only for|जहाँ लागू|यदि|केवल|వర్తిస్తే|మాత్రమే", re.I)
_ORDERING = re.compile(r"after|before|then|only after|subsequently|के बाद|से पहले|तत्पश्चात|తర్వాత|ముందు|అనంతరం", re.I)

_ACTION_CUES: dict[ActionType, re.Pattern[str]] = {
    ActionType.OBTAIN_DOCUMENT: re.compile(r"obtain|get|procure|बनवायें|प्राप्त|తీసుకో|పొంద", re.I),
    ActionType.REGISTER: re.compile(r"register|registration|पंजीकरण|रजिस्टर|నమోదు", re.I),
    ActionType.PAY_FEE: re.compile(r"pay.{0,30}fee|fee.{0,30}(?:pay|payment)|शुल्क.{0,25}(?:भुगतान|जमा)|फीस.{0,25}(?:भुगतान|जमा)|ఫీజు.{0,25}చెల్ల", re.I | re.S),
    ActionType.UPLOAD_DOCUMENT: re.compile(r"upload|अपलोड|అప్.?లోడ్", re.I),
    ActionType.SUBMIT_APPLICATION: re.compile(r"submit|send.{0,30}(?:application|form)|आवेदन.{0,30}(?:जमा|भेज)|समर्पित|దరఖాస్తు.{0,30}సమర్ప", re.I | re.S),
    ActionType.DOWNLOAD_ADMIT_CARD: re.compile(r"download.{0,30}(?:admit|hall ticket)|प्रवेश.?पत्र.{0,20}डाउनलोड|హాల్ టికెట్.{0,20}డౌన్.?లోడ్", re.I | re.S),
    ActionType.CORRECTION: re.compile(r"correct|correction|edit|सुधार|संशोधन|సవరణ", re.I),
    ActionType.ATTEND_EXAM: re.compile(r"(?:attend|appear).{0,20}(?:exam|test)|परीक्षा.{0,20}(?:उपस्थित|सम्मिलित)|పరీక్ష.{0,20}హాజరు", re.I | re.S),
    ActionType.ATTEND_INTERVIEW: re.compile(r"(?:attend|appear).{0,20}interview|साक्षात्कार.{0,20}उपस्थित|ఇంటర్వ్యూ.{0,20}హాజరు", re.I | re.S),
    ActionType.VERIFY_DOCUMENTS: re.compile(r"verification|verify|सत्यापन|जाँच|ధృవీకరణ|వెరిఫికేషన్", re.I),
    ActionType.DOWNLOAD: re.compile(r"download|डाउनलोड|డౌన్.?లోడ్", re.I),
    ActionType.OTHER: re.compile(r"fill|bring|send|post|counsel|भरें|लायें|भेजें|डाक|కౌన్సెల|పంప|తీసుకురా", re.I),
}


@dataclass(frozen=True, slots=True)
class SupportDecision:
    supported: bool
    reason: RejectionReason | None = None
    detail: str | None = None


def _normal(value: str) -> str:
    return _WS.sub(" ", value).strip().casefold()


def _evidence_text(
    evidence_ids: list[str],
    evidence: Mapping[str, EvidenceSpan],
) -> tuple[str | None, SupportDecision | None]:
    if not evidence_ids:
        return None, SupportDecision(False, RejectionReason.INVALID_EVIDENCE, "No evidence IDs supplied.")
    unknown = [item for item in evidence_ids if item not in evidence]
    if unknown:
        return None, SupportDecision(False, RejectionReason.INVALID_EVIDENCE, f"Unknown evidence IDs: {unknown}")
    return "\n".join(evidence[item].text for item in evidence_ids), None


def _numeric_values(text: str) -> list[float]:
    values: list[float] = []
    scales = {"lakh": 100000.0, "lac": 100000.0, "लाख": 100000.0, "లక్ష": 100000.0, "करोड़": 10000000.0, "కోటి": 10000000.0}
    for match in _NUMBER.finditer(text):
        value = float(match.group(1).replace(",", ""))
        if match.group(2):
            value *= scales[match.group(2).casefold()]
        values.append(value)
    return values


def _dates(text: str) -> set[str]:
    values: set[str] = set()
    for match in _DATE.finditer(text):
        try:
            if match.group(1):
                values.add(date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat())
            else:
                values.add(date(int(match.group(6)), int(match.group(5)), int(match.group(4))).isoformat())
        except ValueError:
            continue
    return values


def _value_supported(condition: Condition, text: str) -> bool:
    controlled = controlled_value_supported(condition.attribute, condition.value, text)
    if controlled is not None:
        return controlled
    if condition.comparator in {Comparator.EXISTS, Comparator.NOT_EXISTS}:
        return True
    if condition.attribute == "date_of_birth" and condition.comparator == Comparator.BETWEEN:
        return isinstance(condition.value, (list, tuple)) and all(str(value) in _dates(text) for value in condition.value)
    if isinstance(condition.value, (int, float)):
        if condition.attribute == "annual_family_income_inr":
            amount = normalize_inr(text)
            if amount is not None and abs(amount - float(condition.value)) < 0.01:
                return True
        return any(abs(value - float(condition.value)) < 0.01 for value in _numeric_values(text))
    if isinstance(condition.value, (list, tuple, set)):
        if condition.comparator == Comparator.BETWEEN and all(isinstance(item, (int, float)) for item in condition.value):
            values = _numeric_values(text)
            return all(any(abs(candidate - float(item)) < 0.01 for candidate in values) for item in condition.value)
        normalized = _normal(text)
        return all(_normal(str(item)) in normalized for item in condition.value)
    if condition.value is None:
        return True
    return _normal(str(condition.value)) in _normal(text)


def condition_support(
    condition: Condition,
    evidence: Mapping[str, EvidenceSpan],
) -> SupportDecision:
    text, failure = _evidence_text(condition.evidence_ids, evidence)
    if failure:
        return failure
    assert text is not None
    if condition.source_text and _normal(condition.source_text) not in _normal(text):
        return SupportDecision(False, RejectionReason.INVALID_EVIDENCE, "source_text is not present in cited evidence.")
    semantic_clause = condition.source_text or text
    if _PREFERENCE.search(semantic_clause):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_ATTRIBUTE, "Preference/desirable wording is not a mandatory eligibility rule.")
    cue = _ATTRIBUTE_CUES.get(condition.attribute)
    if cue is None:
        if not (condition.comparator == Comparator.EXISTS and condition.attribute.endswith(("certificate", "qualification"))):
            return SupportDecision(False, RejectionReason.UNSUPPORTED_ATTRIBUTE, f"No support policy exists for attribute {condition.attribute!r}.")
    elif not cue.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_ATTRIBUTE, f"Cited evidence lacks a cue for {condition.attribute!r}.")
    if not _value_supported(condition, text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_VALUE, "Condition value is not present in cited evidence.")
    if condition.reference_date and condition.reference_date not in _dates(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_VALUE, "Reference date is not present in cited evidence.")
    if condition.comparator in _OPERATOR_CUES and not _OPERATOR_CUES[condition.comparator].search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, f"Evidence lacks an exact {condition.comparator.value} cue.")
    if condition.comparator in {Comparator.EXISTS, Comparator.NOT_EXISTS}:
        if condition.comparator == Comparator.EXISTS and not _REQUIREMENT.search(text):
            return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Evidence does not state a mandatory possession requirement.")
        if condition.comparator == Comparator.NOT_EXISTS and not re.search(r"need not|not required|exempt|नहीं|छूट|అవసరం లేదు|మినహాయింపు", text, re.I):
            return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Evidence does not state absence or exemption.")
    if condition.comparator == Comparator.IN and len(condition.value or []) > 1 and not _ALTERNATIVE.search(text) and "/" not in text:
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Multiple allowed values lack an alternative/membership cue.")
    return SupportDecision(True)


def group_support(
    group: ConditionGroup,
    evidence: Mapping[str, EvidenceSpan],
) -> SupportDecision:
    if not group.children:
        return SupportDecision(False, RejectionReason.SCHEMA_INVALID, "Eligibility group is empty.")
    if group.applies_when:
        decision = group_support(group.applies_when, evidence)
        if not decision.supported:
            return decision
    for child in group.children:
        decision = condition_support(child, evidence) if isinstance(child, Condition) else group_support(child, evidence)
        if not decision.supported:
            return decision
        if isinstance(child, Condition) and child.applies_when:
            guard_decision = group_support(child.applies_when, evidence)
            if not guard_decision.supported:
                return guard_decision
    return SupportDecision(True)


def document_support(
    item: DocumentRequirement,
    evidence: Mapping[str, EvidenceSpan],
) -> SupportDecision:
    text, failure = _evidence_text(item.evidence_ids, evidence)
    if failure:
        return failure
    assert text is not None
    if _normal(item.source_name) not in _normal(text):
        return SupportDecision(False, RejectionReason.INVALID_EVIDENCE, "Document source name is absent from evidence.")
    if _DOCUMENT_REFERRAL_ONLY.search(text) and not _DOCUMENT_SUBMISSION.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Document is mentioned only in an external-information referral.")
    if item.requirement_type == RequirementType.MANDATORY and not (
        _REQUIREMENT.search(text) or _DOCUMENT_SUBMISSION.search(text)
    ):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Mandatory document lacks an obligation or submission relation.")
    if item.requirement_type == RequirementType.OPTIONAL and not _OPTIONAL.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Optional document lacks an optional cue.")
    if item.requirement_type == RequirementType.CONDITIONAL:
        if item.applies_when is None:
            return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Conditional document lacks a supported guard cue.")
        decision = group_support(item.applies_when, evidence)
        if not decision.supported:
            return decision
    if item.alternatives and not _ALTERNATIVE.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Document alternatives lack an OR cue.")
    return SupportDecision(True)


def action_support(
    item: ActionNode,
    evidence: Mapping[str, EvidenceSpan],
    actions_by_id: Mapping[str, ActionNode] | None = None,
) -> SupportDecision:
    text, failure = _evidence_text(item.evidence_ids, evidence)
    if failure:
        return failure
    assert text is not None
    if _normal(item.description) not in _normal(text):
        return SupportDecision(False, RejectionReason.INVALID_EVIDENCE, "Action description is absent from cited evidence.")
    cue = _ACTION_CUES[item.action_type]
    if not cue.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_ATTRIBUTE, f"Evidence lacks a {item.action_type.value} action cue.")
    if item.is_optional and not _OPTIONAL.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Optional action lacks an optional cue.")
    if not item.is_optional and _OPTIONAL.search(text):
        return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Optional wording was promoted as mandatory.")
    if item.applies_when:
        decision = group_support(item.applies_when, evidence)
        if not decision.supported:
            return decision
    if item.depends_on:
        if not _ORDERING.search(text):
            return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Dependency lacks an explicit ordering cue.")
        if actions_by_id is None:
            return SupportDecision(False, RejectionReason.SCHEMA_INVALID, "Dependency targets were not supplied for validation.")
        for dependency in item.depends_on:
            prerequisite = actions_by_id.get(dependency)
            if prerequisite is None:
                return SupportDecision(False, RejectionReason.SCHEMA_INVALID, f"Missing dependency action {dependency!r}.")
            if not _ACTION_CUES[prerequisite.action_type].search(text):
                return SupportDecision(False, RejectionReason.UNSUPPORTED_OPERATOR, "Ordering evidence does not mention the prerequisite action.")
    return SupportDecision(True)
