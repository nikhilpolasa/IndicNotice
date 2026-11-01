"""Non-routing text-integrity diagnostics for native and OCR output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import unicodedata


_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â‚", "à¤", "à°", "ï¿½")


def _script(character: str) -> str | None:
    code = ord(character)
    if 0x0900 <= code <= 0x097F:
        return "Devanagari"
    if 0x0C00 <= code <= 0x0C7F:
        return "Telugu"
    if character.isalpha() and "LATIN" in unicodedata.name(character, ""):
        return "Latin"
    return None


@dataclass(frozen=True, slots=True)
class TextQualityDiagnostics:
    character_count: int
    replacement_character_rate: float
    suspicious_glyph_ratio: float
    alphanumeric_ratio: float
    dominant_script: str | None
    script_consistency: float | None
    url_count: int
    url_corruption_rate: float
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def diagnose_text_quality(text: str) -> TextQualityDiagnostics:
    """Return observable integrity signals without changing extraction routing."""
    size = len(text)
    denominator = max(size, 1)
    replacement_rate = text.count("\ufffd") / denominator
    suspicious_count = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    suspicious_ratio = suspicious_count / denominator
    alphanumeric_ratio = sum(character.isalnum() for character in text) / denominator

    scripts: dict[str, int] = {}
    for character in text:
        label = _script(character)
        if label:
            scripts[label] = scripts.get(label, 0) + 1
    dominant_script = max(scripts, key=scripts.get) if scripts else None
    script_total = sum(scripts.values())
    script_consistency = scripts[dominant_script] / script_total if dominant_script and script_total else None

    urls = _URL.findall(text)
    corrupt_urls = [url for url in urls if "\ufffd" in url or any(marker in url for marker in _MOJIBAKE_MARKERS)]
    url_corruption_rate = len(corrupt_urls) / len(urls) if urls else 0.0
    warnings: list[str] = []
    if replacement_rate:
        warnings.append("replacement characters detected")
    if suspicious_ratio:
        warnings.append("possible mojibake sequences detected")
    if url_corruption_rate:
        warnings.append("possible URL text corruption detected")
    if size and alphanumeric_ratio < 0.15:
        warnings.append("low alphanumeric density")
    return TextQualityDiagnostics(
        character_count=size,
        replacement_character_rate=replacement_rate,
        suspicious_glyph_ratio=suspicious_ratio,
        alphanumeric_ratio=alphanumeric_ratio,
        dominant_script=dominant_script,
        script_consistency=script_consistency,
        url_count=len(urls),
        url_corruption_rate=url_corruption_rate,
        warnings=tuple(warnings),
    )
