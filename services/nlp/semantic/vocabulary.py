"""Controlled, source-justified eligibility attribute vocabulary."""

from __future__ import annotations

import re


ATTRIBUTE_DEFINITIONS = {
    "current_class": "Class/grade in which the candidate is currently studying.",
    "current_school_type": "Normalized institution type of the candidate's current school.",
    "previous_class": "Class/grade the candidate previously completed or passed.",
    "previous_school_type": "Normalized institution type of the school for the prior class.",
    "attempt_count": "Number of times the candidate has attempted the stated examination.",
    "selection_status": "Whether the candidate has reached a stated selection stage.",
}

INSTITUTION_VALUES = (
    "government",
    "government_aided",
    "private",
    "kendriya_vidyalaya",
    "jawahar_navodaya_vidyalaya",
    "kgbv",
    "residential",
)

_SCHOOL_PATTERNS = {
    "government_aided": re.compile(r"government[ -]?aided|aided school|अनुदान\s*प्राप्त|సహాయ\s*ప్రభుత్వ", re.I),
    "government": re.compile(r"\bgovernment\b|सरकारी|ప్రభుత్వ", re.I),
    "private": re.compile(r"\bprivate\b|निजी|ప్రైవేట్", re.I),
    "kendriya_vidyalaya": re.compile(r"kendriya vidyalaya|केंद्रीय\s*वव?द्यालय|కేంద్రీయ\s*విద్యాలయ", re.I),
    "jawahar_navodaya_vidyalaya": re.compile(r"jawahar navodaya|जवाहर\s*नवोदय|జవహర్\s*నవోదయ", re.I),
    "kgbv": re.compile(r"\bKGBV\b", re.I),
    "residential": re.compile(r"residential school|आवासीय\s*वव?द्यालय|రెసిడెన్షియల్|నివాస", re.I),
}

_CLASS_VALUES = {
    7: re.compile(r"\b(?:class\s*)?(?:VII|7(?:th)?)\b|सातवीं\s*कक्षा|कक्षा\s*सातवीं|ఏడవ\s*తరగతి", re.I),
    8: re.compile(r"\b(?:class\s*)?(?:VIII|8(?:th)?)\b|आठवीं\s*कक्षा|कक्षा\s*आठवी|ఎనిమిదవ\s*తరగతి", re.I),
}


def institution_types(text: str) -> list[str]:
    """Return normalized institution types explicitly named in source text."""
    found = [value for value, pattern in _SCHOOL_PATTERNS.items() if pattern.search(text)]
    # “government aided” contains “government”; preserve both only when source
    # separately presents government/aided as alternatives.
    if "government_aided" in found and "government" in found and not re.search(
        r"government\s*(?:/|or)\s*(?:government[ -]?)?aided|सरकारी\s*/\s*अनुदान", text, re.I
    ):
        found.remove("government")
    return found


def class_values(text: str) -> list[int]:
    return [value for value, pattern in _CLASS_VALUES.items() if pattern.search(text)]


def controlled_value_supported(attribute: str, value: object, text: str) -> bool | None:
    """Return support for controlled values, or ``None`` for other attributes."""
    if attribute in {"current_school_type", "previous_school_type"}:
        available = set(institution_types(text))
        requested = set(value if isinstance(value, (list, tuple, set)) else [value])
        return bool(requested) and requested <= available
    if attribute in {"current_class", "previous_class"}:
        return value in class_values(text)
    if attribute == "attempt_count":
        if value != 1:
            return False
        return bool(re.search(r"\bonly once\b|\bone time\b|केवल\s*एक\s*बार|ఒక్కసారి\s*మాత్రమే", text, re.I))
    if attribute == "selection_status":
        normalized = str(value).casefold()
        if normalized == "selected":
            return bool(re.search(r"selected|selection|चयनित|मेरिट.?सूची|ఎంపిక", text, re.I))
        return False
    return None
