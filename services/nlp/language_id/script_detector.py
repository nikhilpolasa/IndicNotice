"""Deterministic Telugu, Devanagari, and Latin script detection."""

from __future__ import annotations

import unicodedata


class ScriptHeuristicDetector:
    """A transparent script detector; `hi` means Devanagari, not semantic Hindi."""

    def __init__(self, *, dominant_threshold: float = 0.75, mixed_threshold: float = 0.15, min_letters: int = 3):
        self.dominant_threshold = dominant_threshold
        self.mixed_threshold = mixed_threshold
        self.min_letters = min_letters

    @staticmethod
    def _script(char: str) -> str | None:
        code = ord(char)
        if 0x0C00 <= code <= 0x0C7F and char.isalpha():
            return "te"
        if 0x0900 <= code <= 0x097F and char.isalpha():
            return "hi"
        if char.isalpha() and "LATIN" in unicodedata.name(char, ""):
            return "en"
        return None

    def detect(self, text: str) -> dict[str, float]:
        counts = {"te": 0, "hi": 0, "en": 0}
        for char in text or "":
            script = self._script(char)
            if script:
                counts[script] += 1
        total = sum(counts.values())
        if total < self.min_letters:
            return {key: 0.0 for key in counts}
        return {key: value / total for key, value in counts.items()}

    def detect_primary(self, text: str) -> tuple[str, float]:
        scores = self.detect(text)
        code, score = max(scores.items(), key=lambda item: item[1])
        if score == 0.0:
            return "unknown", 0.0
        significant = sum(value >= self.mixed_threshold for value in scores.values())
        if significant >= 2:
            return "mixed", score
        return code, score
