"""Conservative Unicode normalization for extracted source text."""

from __future__ import annotations

import re
import unicodedata

_HORIZONTAL_SPACE = re.compile(r"[^\S\r\n]+")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")
_REMOVABLE_FORMAT_CHARACTERS = {"\u200b", "\ufeff"}


def normalize_extracted_text(text: str) -> str:
    """Normalize representation without spelling correction or translation."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(
        char
        for char in text
        if char in "\n\t"
        or (unicodedata.category(char) != "Cc" and char not in _REMOVABLE_FORMAT_CHARACTERS)
    )
    lines = [_HORIZONTAL_SPACE.sub(" ", line).strip() for line in text.split("\n")]
    return _EXCESS_NEWLINES.sub("\n\n", "\n".join(lines)).strip()
