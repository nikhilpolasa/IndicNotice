"""
Indian numeric normalization utilities for IndicNotice.

Handles formats common in Indian government notices:
  "₹2.5 lakh"    -> 250000.0
  "Rs. 2,50,000" -> 250000.0
  "₹2,50,000/-"  -> 250000.0
  "2.5 लाख"      -> 250000.0  (Hindi)
  "2.5 లక్షలు"   -> 250000.0  (Telugu)
  "5 crore"      -> 50000000.0
  "75%"          -> 75.0
  "7.5 CGPA"     -> 7.5

These utilities are used by the validation layer and baseline extractor.

Design rules:
  - Never mutate the source text.
  - Return None if the input cannot be parsed.
  - Never invent a value.
"""

from __future__ import annotations

import re
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Internal patterns
# ---------------------------------------------------------------------------

# Strip common currency/noise prefixes
_CURRENCY_PREFIX = re.compile(
    r"^[₹Rs\.]+\s*",
    re.IGNORECASE,
)
_SUFFIX_JUNK = re.compile(r"[/\-\s]+$")

# Lakh / लाख / లక్ష multiplier
_LAKH_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*"
    r"(?:lakh|lakhs?|lacs?|लाख|లక్షలు|లక్ష)",
    re.IGNORECASE,
)

# Crore multiplier
_CRORE_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*"
    r"(?:crores?|కోట్లు|కోటి|करोड़?)",
    re.IGNORECASE,
)

# Thousand multiplier (हजार / వేలు / thousand)
_THOUSAND_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*"
    r"(?:thousands?|हजार|వేలు|వేల)",
    re.IGNORECASE,
)

# Plain numeric (Indian comma formatting: 2,50,000 or 250,000)
_PLAIN_NUM_RE = re.compile(r"^[\d,]+(?:\.\d+)?$")

# Percentage
_PERCENT_RE = re.compile(
    r"([-]?\d+(?:\.\d+)?)\s*(?:%|percent|प्रतिशत|శాతం)",
    re.IGNORECASE,
)

# CGPA / GPA
_CGPA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:cgpa|gpa)", re.IGNORECASE)


def _strip_commas(s: str) -> float:
    """Remove Indian-style grouping commas and parse as float."""
    return float(s.replace(",", ""))


class ParsedAmount(NamedTuple):
    value: float
    source_text: str


def normalize_inr(text: str) -> float | None:
    """
    Parse an Indian Rupee amount string and return a normalized float.

    Returns None if the text cannot be parsed.

    Examples
    --------
    >>> normalize_inr("₹2.5 lakh")
    250000.0
    >>> normalize_inr("Rs. 2,50,000/-")
    250000.0
    >>> normalize_inr("5 crore")
    5000000.0
    >>> normalize_inr("garbage")
    None
    """
    if not text:
        return None

    t = text.strip()
    # Remove currency symbols/prefixes
    t = _CURRENCY_PREFIX.sub("", t)
    t = _SUFFIX_JUNK.sub("", t)
    t = t.strip()

    # Parse one or more scale terms. Multiple terms are accepted only when
    # they cover the whole input (apart from whitespace), preventing a range
    # such as "2 lakh to 3 lakh" from being silently read as one amount.
    scaled_matches: list[tuple[int, int, float]] = []
    for pattern, multiplier in (
        (_CRORE_RE, 1_00_00_000),
        (_LAKH_RE, 1_00_000),
        (_THOUSAND_RE, 1_000),
    ):
        for match in pattern.finditer(t):
            try:
                scaled_matches.append(
                    (match.start(), match.end(), _strip_commas(match.group(1)) * multiplier)
                )
            except ValueError:
                return None

    if scaled_matches:
        scaled_matches.sort()
        # Reject overlapping matches and any non-whitespace material between
        # terms. This keeps ambiguous prose out of deterministic normalization.
        cursor = 0
        total = 0.0
        for start, end, value in scaled_matches:
            if start < cursor or t[cursor:start].strip():
                return None
            total += value
            cursor = end
        if t[cursor:].strip():
            return None
        return total

    # Try plain number (with optional Indian commas)
    if _PLAIN_NUM_RE.match(t):
        try:
            return _strip_commas(t)
        except ValueError:
            return None

    return None


def normalize_percentage(text: str) -> float | None:
    """
    Parse a percentage string and return a float in [0, 100].

    Returns None if the text cannot be parsed.

    Examples
    --------
    >>> normalize_percentage("75%")
    75.0
    >>> normalize_percentage("75.5 percent")
    75.5
    """
    if not text:
        return None
    m = _PERCENT_RE.search(text)
    if m:
        try:
            v = float(m.group(1))
            if 0.0 <= v <= 100.0:
                return v
        except ValueError:
            pass
    # Try bare number
    t = text.strip().rstrip("%").strip()
    try:
        v = float(t)
        if 0.0 <= v <= 100.0:
            return v
    except ValueError:
        pass
    return None


def normalize_cgpa(text: str) -> float | None:
    """
    Parse a CGPA/GPA string and return a float.

    Returns None if unparseable.

    Examples
    --------
    >>> normalize_cgpa("7.5 CGPA")
    7.5
    >>> normalize_cgpa("6.0 GPA")
    6.0
    """
    if not text:
        return None
    m = _CGPA_RE.search(text)
    if m:
        try:
            value = float(m.group(1))
            if 0.0 <= value <= 10.0:
                return value
        except ValueError:
            pass
    return None
