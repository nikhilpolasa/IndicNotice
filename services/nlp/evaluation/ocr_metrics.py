"""Unicode-safe CER and whitespace-token WER implementations."""

from __future__ import annotations

from collections.abc import Sequence


def _levenshtein(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def _rate(reference: Sequence[str], hypothesis: Sequence[str]) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return _levenshtein(reference, hypothesis) / len(reference)


def character_error_rate(reference: str, hypothesis: str) -> float:
    return _rate(list(reference), list(hypothesis))


def word_error_rate(reference: str, hypothesis: str) -> float:
    return _rate(reference.split(), hypothesis.split())
