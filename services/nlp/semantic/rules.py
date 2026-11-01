"""Conservative deterministic rules for NLP-4 semantic candidates.

These rules intentionally target bounded constructions.  Text that does not
match an explicit construction remains unresolved instead of being guessed.
"""

from __future__ import annotations

from datetime import date
import re
from typing import Sequence

from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.semantic.relaxations import DeltaRelaxation, resolve_age_delta
from services.nlp.semantic.types import SemanticCandidates
from services.nlp.semantic.vocabulary import class_values, institution_types
from services.nlp.validation.normalizers import normalize_inr


_PREFERENCE = re.compile(
    r"preference|preferred|desirable|वांछनीय|वरीयता|प्राथमिकता|ప్రాధాన్యత|కావాల్సిన",
    re.I,
)
_AGE = re.compile(r"age|आयु|उम्र|वर्ष|వయస్సు|ఏళ్లు", re.I)
_INCOME = re.compile(r"income|आय|आमदनी|ఆదాయం", re.I)
_MARKS = re.compile(r"marks?|percentage|प्रतिशत|अंक|మార్కులు|శాతం", re.I)
_QUALIFICATION = re.compile(r"qualification|degree|pass|योग्यता|उत्तीर्ण|अर्हता|అర్హత|ఉత్తీర్ణ|డిగ్రీ", re.I)
_REQUIRED = re.compile(r"must|required|shall|essential|अनिवार्य|आवश्यक|होना चाहिए|తప్పనిసరి|కలిగి ఉండాలి|అవసరం", re.I)
_CATEGORIES = re.compile(r"(?<![A-Z])(SC|ST|OBC|EWS|PwD)(?![A-Z])", re.I)
_NUMBER = re.compile(r"(?<!\w)(\d[\d,]*(?:\.\d+)?)")
_MONEY_VALUE = re.compile(
    r"(?:₹|Rs\.?|INR|रु\.?|రూ\.?)?\s*(\d[\d,]*(?:\.\d+)?\s*(?:lakh|lac|लाख|లక్షలు|లక్ష|crore|करोड़|కోటి)?)",
    re.I,
)
_PERCENT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|प्रतिशत|శాతం)", re.I)
_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
_ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_QUALIFICATIONS = (
    ("B.Tech", re.compile(r"B\.?\s*Tech", re.I)),
    ("B.E.", re.compile(r"B\.?\s*E\.?(?!\w)", re.I)),
    ("Postgraduate", re.compile(r"post.?graduat|master.?s degree|स्नातकोत्तर|పోస్ట్.?గ్రాడ్యుయేట్", re.I)),
    ("Graduate", re.compile(r"graduat(?:e|ion)|bachelor.?s degree|स्नातक|గ్రాడ్యుయేట్|డిగ్రీ", re.I)),
)
_OR = re.compile(r"\bor\b|either|या|अथवा|లేదా", re.I)


def _comparator(text: str, *, lower: bool) -> Comparator | None:
    rules = (
        (Comparator.LTE, r"<=|not (?:more|greater) than|not exceeding|does not exceed|at most|up to|maximum|अधिक नहीं|अधिकतम|तक|మించకూడదు|గరిష్ట|వరకు"),
        (Comparator.LT, r"(?<!<)<(?![=])|less than|below|under|से कम|కంటే తక్కువ"),
        (Comparator.GTE, r">=|at least|not less than|minimum|कम नहीं|न्यूनतम|कम से कम|కనీసం|తక్కువ కాకుండా"),
        (Comparator.GT, r"(?<!>)>(?![=])|more than|greater than|above|से अधिक|కంటే ఎక్కువ"),
    )
    for comparator, pattern in rules:
        if re.search(pattern, text, re.I):
            return comparator
    return Comparator.GTE if lower else Comparator.LTE


def _date_values(text: str) -> list[str]:
    values: list[str] = []
    for match in _DATE.finditer(text):
        try:
            values.append(date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat())
        except ValueError:
            pass
    for match in _ISO_DATE.finditer(text):
        try:
            values.append(date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat())
        except ValueError:
            pass
    return values


def _condition(
    index: int,
    span: EvidenceSpan,
    attribute: str,
    comparator: Comparator,
    value: object,
    *,
    unit: str | None = None,
    reference_date: str | None = None,
    source_text: str | None = None,
    evidence_ids: list[str] | None = None,
) -> Condition:
    return Condition(
        condition_id=f"nlp4_cond_{index:03d}",
        attribute=attribute,
        comparator=comparator,
        value=value,
        unit=unit,
        reference_date=reference_date,
        source_text=source_text or span.text,
        evidence_ids=evidence_ids or [span.evidence_id],
    )


def _category_guard(index: int, span: EvidenceSpan, categories: list[str]) -> ConditionGroup:
    return ConditionGroup(
        group_id=f"nlp4_guard_{index:03d}",
        operator="AND",
        children=[_condition(index, span, "category", Comparator.IN, categories)],
        evidence_ids=[span.evidence_id],
    )


_ACTION_PATTERNS: tuple[tuple[ActionType, re.Pattern[str]], ...] = (
    (ActionType.REGISTER, re.compile(r"register|registration|पंजीकरण|నమోదు", re.I)),
    (ActionType.OBTAIN_DOCUMENT, re.compile(r"(?:obtain|get|procure|प्राप्त|बनवायें|పొంద|తీసుకో).{0,35}(?:certificate|document|प्रमाण|दस्तावेज|సర్టిఫికెట్|పత్ర)", re.I | re.S)),
    (ActionType.UPLOAD_DOCUMENT, re.compile(r"upload|अपलोड|అప్.?లోడ్", re.I)),
    (ActionType.PAY_FEE, re.compile(r"(?:pay|payment|भुगतान|जमा).{0,25}(?:fee|शुल्क|फीस)|(?:fee|शुल्क|फीस|ఫీజు|రుసుము).{0,25}(?:pay|payment|भुगतान|जमा|చెల్ల)", re.I | re.S)),
    (ActionType.SUBMIT_APPLICATION, re.compile(r"(?:submit|send|जमा|भेज|సమర్పించ|పంప).{0,40}(?:application|form|आवेदन|फॉर्म|దరఖాస్తు|ఫారం)|(?:application|form|आवेदन|फॉर्म|దరఖాస్తు|ఫారం).{0,40}(?:submit|send|जमा|भेज|సమర్పించ|పంప)", re.I | re.S)),
    (ActionType.DOWNLOAD_ADMIT_CARD, re.compile(r"download.{0,30}(?:admit card|hall ticket)|प्रवेश.?पत्र.{0,20}डाउनलोड|హాల్ టికెట్.{0,20}డౌన్.?లోడ్", re.I | re.S)),
    (ActionType.ATTEND_EXAM, re.compile(r"(?:attend|appear).{0,20}(?:exam|test)|परीक्षा.{0,20}(?:उपस्थित|सम्मिलित)|పరీక్ష.{0,20}హాజరు", re.I | re.S)),
    (ActionType.ATTEND_INTERVIEW, re.compile(r"(?:attend|appear).{0,20}interview|साक्षात्कार.{0,20}उपस्थित|ఇంటర్వ్యూ.{0,20}హాజరు", re.I | re.S)),
    (ActionType.VERIFY_DOCUMENTS, re.compile(r"(?:document|certificate|दस्तावेज|प्रमाण|పత్ర).{0,30}(?:verification|सत्यापन|जाँच|ధృవీకరణ|వెరిఫికేషన్)", re.I | re.S)),
    (ActionType.DOWNLOAD, re.compile(r"download|डाउनलोड|డౌన్.?లోడ్", re.I)),
)


class SemanticRuleExtractor:
    """Produce conservative eligibility/action candidates from evidence spans."""

    def extract(self, evidence: Sequence[EvidenceSpan]) -> SemanticCandidates:
        children: list[Condition | ConditionGroup] = []
        unresolved: list[str] = []
        base_age: Condition | None = None
        relaxations: list[DeltaRelaxation] = []
        counter = 0

        for span_index, span in enumerate(evidence):
            next_span = evidence[span_index + 1] if span_index + 1 < len(evidence) else None
            joined = span.text
            joined_ids = [span.evidence_id]
            if next_span is not None and next_span.page_number == span.page_number:
                joined = f"{joined}\n{next_span.text}"
                joined_ids.append(next_span.evidence_id)
            text = span.text
            if _PREFERENCE.search(text):
                clauses = [item.strip() for item in re.split(r"[;।\n]", text) if item.strip()]
                mandatory_clauses = [item for item in clauses if not _PREFERENCE.search(item)]
                unresolved.append(f"{span.evidence_id}: preference/desirable clause excluded from mandatory eligibility")
                if not mandatory_clauses:
                    continue
                text = "; ".join(mandatory_clauses)

            born = re.search(r"born\s+between|जन्म.{0,20}(?:के बीच|से)|పుట్టిన.{0,20}(?:మధ్య|నుండి)", text, re.I | re.S)
            dates = _date_values(text)
            if born and len(dates) >= 2:
                counter += 1
                children.append(_condition(counter, span, "date_of_birth", Comparator.BETWEEN, dates[:2]))
                continue

            relaxation = re.search(
                r"(?:upper\s+)?age.{0,50}?relax(?:ed|ation|able)?.{0,30}?(\d{1,2}).{0,30}?(?:years?)|"
                r"आयु.{0,50}?(\d{1,2}).{0,20}?(?:वर्ष|साल).{0,20}?(?:छूट|शिथिल)|"
                r"వయస్సు.{0,50}?(\d{1,2}).{0,20}?(?:ఏళ్లు|సంవత్సరాలు).{0,20}?(?:సడలింపు)",
                text,
                re.I | re.S,
            )
            if relaxation:
                categories = tuple(dict.fromkeys(match.group(1).upper() for match in _CATEGORIES.finditer(text)))
                delta_text = next(group for group in relaxation.groups() if group is not None)
                if categories:
                    relaxations.append(DeltaRelaxation(categories, float(delta_text), text, (span.evidence_id,)))
                else:
                    unresolved.append(f"{span.evidence_id}: age relaxation has no supported category")
                continue

            if _AGE.search(text):
                age_match = re.search(r"(?:age|आयु|उम्र|వయస్సు).{0,70}?(\d{1,3})\s*(?:years?|वर्ष|साल|ఏళ్లు|సంవత్సరాలు)?", text, re.I | re.S)
                if age_match and 0 <= int(age_match.group(1)) <= 120:
                    counter += 1
                    ref = dates[0] if re.search(r"as on|reckon|के अनुसार|तक|నాటికి|ప్రకారం", text, re.I) and dates else None
                    item = _condition(counter, span, "age", _comparator(text, lower=False), int(age_match.group(1)), unit="years", reference_date=ref)
                    children.append(item)
                    if item.comparator in {Comparator.LT, Comparator.LTE}:
                        base_age = item

            if _INCOME.search(text):
                money = _MONEY_VALUE.search(text)
                amount = normalize_inr(money.group(0).strip()) if money else None
                if amount is not None:
                    counter += 1
                    children.append(_condition(counter, span, "annual_family_income_inr", _comparator(text, lower=False), amount, unit="INR"))

            if _MARKS.search(text):
                match = _PERCENT.search(text)
                if match:
                    counter += 1
                    children.append(_condition(counter, span, "marks_percentage", _comparator(text, lower=True), float(match.group(1)), unit="%"))

            qualifications = [name for name, pattern in _QUALIFICATIONS if pattern.search(text)]
            if qualifications and _QUALIFICATION.search(text) and _REQUIRED.search(text):
                leaves: list[Condition] = []
                for name in qualifications:
                    counter += 1
                    leaves.append(_condition(counter, span, "education_level", Comparator.EQ, name))
                if len(leaves) > 1 and _OR.search(text):
                    children.append(ConditionGroup(group_id=f"nlp4_qualification_{counter:03d}", operator="OR", children=leaves, evidence_ids=[span.evidence_id]))
                else:
                    children.extend(leaves)

            state = re.search(r"(?:resident of|domicile of|state\s*(?:is|=)|निवासी|అభ్యర్థి.{0,20}నివాసి)\s+([A-Za-z][A-Za-z ]{2,30})", text, re.I)
            if state and _REQUIRED.search(text):
                counter += 1
                children.append(_condition(counter, span, "state", Comparator.EQ, state.group(1).strip(" .")))

            if re.search(r"must (?:possess|have)|आवश्यक.{0,20}प्रमाण|अनिवार्य.{0,20}प्रमाण|తప్పనిసరిగా.{0,20}(?:పత్రం|సర్టిఫికెట్)", text, re.I | re.S):
                cert = re.search(r"([A-Za-z]+(?: [A-Za-z]+){0,3}) certificate|([\u0900-\u097f ]+प्रमाण.?पत्र)|([\u0c00-\u0c7f ]+(?:పత్రం|సర్టిఫికెట్))", text, re.I)
                if cert:
                    counter += 1
                    value = next(group for group in cert.groups() if group).strip()
                    certificate_attribute = re.sub(r"\W+", "_", value.casefold()).strip("_") + "_certificate"
                    children.append(_condition(counter, span, certificate_attribute, Comparator.EXISTS, None))
            school_values = institution_types(text)
            if school_values and re.search(r"currently\s+stud|studying|पढ़\s*रह|अध्ययनरत|చదువుతున్న", text, re.I):
                counter += 1
                children.append(_condition(
                    counter, span, "current_school_type", Comparator.IN, school_values,
                    source_text=text,
                ))

            classes = class_values(text)
            if classes and re.search(r"passed|completed|उत्तीर्ण|पास|పాస|ఉత్తీర్ణ", text, re.I):
                counter += 1
                children.append(_condition(counter, span, "previous_class", Comparator.EQ, classes[0]))
                if school_values:
                    counter += 1
                    children.append(_condition(
                        counter, span, "previous_school_type", Comparator.IN, school_values,
                    ))
            elif classes and re.search(r"currently\s+stud|studying|अध्ययनरत|पढ़\s*रह|చదువుతున్న", text, re.I):
                counter += 1
                children.append(_condition(counter, span, "current_class", Comparator.EQ, classes[0]))

            if re.search(r"\bonly once\b|\bone time\b|केवल\s*एक\s*बार|ఒక్కసారి\s*మాత్రమే", text, re.I):
                counter += 1
                children.append(_condition(counter, span, "attempt_count", Comparator.LTE, 1))

            excluded_schools = institution_types(joined)
            if excluded_schools and re.search(
                r"may not|cannot|not eligible|नहीं.{0,45}(?:बैठ|आवेदन)|అర్హులు కాదు",
                joined,
                re.I | re.S,
            ):
                counter += 1
                children.append(_condition(
                    counter,
                    span,
                    "current_school_type",
                    Comparator.NOT_IN,
                    excluded_schools,
                    source_text=joined,
                    evidence_ids=joined_ids,
                ))

        for relaxation in relaxations:
            resolved, reason = resolve_age_delta(base_age, relaxation)
            if resolved is None:
                unresolved.append(reason or "Unresolved age relaxation")
                continue
            if base_age in children:
                children.remove(base_age)
            children.append(resolved)

        actions = self._actions(evidence)
        eligibility = None
        if children:
            eligibility = ConditionGroup(
                group_id="nlp4_eligibility_root",
                operator="AND",
                label="Evidence-gated deterministic semantic rules",
                children=children,
                evidence_ids=list(dict.fromkeys(eid for child in children for eid in child.evidence_ids)),
            )
        return SemanticCandidates(eligibility=eligibility, actions=tuple(actions), unresolved=tuple(unresolved))

    @staticmethod
    def _actions(evidence: Sequence[EvidenceSpan]) -> list[ActionNode]:
        actions: list[ActionNode] = []
        for span in evidence:
            text = " ".join(span.text.split())
            optional = bool(re.search(r"\bmay\b|optional|for (?:their|your) records|वैकल्पिक|कर सकते हैं|ఐచ్ఛిక|చేయవచ్చు", text, re.I))
            categories = list(dict.fromkeys(match.group(1).upper() for match in _CATEGORIES.finditer(text)))
            conditional = bool(categories and re.search(r"\bif\b|only|candidates must|यदि|केवल|అభ్యర్థులు|మాత్రమే", text, re.I))
            obtain_matches = list(re.finditer(
                r"(?:obtain|get|procure|प्राप्त|बनवायें|పొందండి|తీసుకోండి?)\s+[^,;।]{0,30}?(?:certificate|document|प्रमाण.?पत्र|दस्तावेज|సర్టిఫికెట్|పత్రం)",
                text,
                re.I,
            ))
            matched: list[ActionType] = []
            for action_type, pattern in _ACTION_PATTERNS:
                if pattern.search(text) and action_type not in matched:
                    if action_type == ActionType.OBTAIN_DOCUMENT and obtain_matches:
                        continue
                    if action_type == ActionType.DOWNLOAD and ActionType.DOWNLOAD_ADMIT_CARD in matched:
                        continue
                    matched.append(action_type)
            span_actions: list[ActionNode] = []
            for match in obtain_matches:
                span_actions.append(ActionNode(
                    action_id=f"nlp4_action_{len(actions) + len(span_actions) + 1:03d}",
                    action_type=ActionType.OBTAIN_DOCUMENT,
                    description=match.group(0),
                    is_optional=optional,
                    evidence_ids=[span.evidence_id],
                ))
            for action_type in matched:
                action = ActionNode(
                    action_id=f"nlp4_action_{len(actions) + len(span_actions) + 1:03d}",
                    action_type=action_type,
                    description=text,
                    is_optional=optional,
                    evidence_ids=[span.evidence_id],
                )
                if conditional:
                    action = action.model_copy(update={"applies_when": _category_guard(900 + len(actions) + len(span_actions), span, categories)})
                span_actions.append(action)

            ordered = bool(re.search(r"then|after|before|only after|इसके बाद|के बाद|से पहले|తర్వాత|ముందు|అనంతరం", text, re.I))
            if ordered:
                by_type = {kind: [item for item in span_actions if item.action_type == kind] for kind in ActionType}
                register = by_type[ActionType.REGISTER]
                obtains = by_type[ActionType.OBTAIN_DOCUMENT]
                upload = by_type[ActionType.UPLOAD_DOCUMENT]
                pay = by_type[ActionType.PAY_FEE]
                submit = by_type[ActionType.SUBMIT_APPLICATION]
                for current in obtains:
                    if register:
                        span_actions[span_actions.index(current)] = current.model_copy(update={"depends_on": [register[-1].action_id]})
                if upload:
                    prerequisites = [item.action_id for item in obtains] or [item.action_id for item in register[-1:]]
                    if prerequisites:
                        current = upload[0]
                        span_actions[span_actions.index(current)] = current.model_copy(update={"depends_on": prerequisites})
                if pay:
                    prerequisites = [item.action_id for item in upload[-1:] or register[-1:]]
                    if prerequisites:
                        current = pay[0]
                        span_actions[span_actions.index(current)] = current.model_copy(update={"depends_on": prerequisites})
                if submit:
                    prerequisites = [item.action_id for item in pay[-1:] or upload[-1:] or register[-1:]]
                    if prerequisites:
                        current = submit[0]
                        span_actions[span_actions.index(current)] = current.model_copy(update={"depends_on": prerequisites})
            actions.extend(span_actions)
        return actions
