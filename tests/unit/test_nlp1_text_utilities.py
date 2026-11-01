import pytest

from services.nlp.evaluation.ocr_metrics import character_error_rate, word_error_rate
from services.nlp.ingestion.quality import diagnose_text_quality
from services.nlp.ingestion.normalization import normalize_extracted_text
from services.nlp.language_id import ScriptHeuristicDetector


def test_text_quality_diagnostics_flag_replacement_and_mojibake_without_routing():
    diagnostics = diagnose_text_quality("à¤†à¤µà¥‡à¤¦à¤¨ \ufffd https://example.gov.in/à¤")
    assert diagnostics.replacement_character_rate > 0
    assert diagnostics.suspicious_glyph_ratio > 0
    assert diagnostics.url_corruption_rate == 1.0
    assert "possible mojibake sequences detected" in diagnostics.warnings


def test_text_quality_diagnostics_report_clean_indic_script_consistency():
    diagnostics = diagnose_text_quality("आवेदन की अंतिम तिथि 15 अक्टूबर 2025 है।")
    assert diagnostics.dominant_script == "Devanagari"
    assert diagnostics.script_consistency == 1.0
    assert diagnostics.replacement_character_rate == 0.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ఉద్యోగ ప్రకటన", "te"),
        ("सरकारी सूचना", "hi"),
        ("Public notice", "en"),
        ("ప్రకటన application date", "mixed"),
        ("सरकारी notice application", "mixed"),
        ("1234 --", "unknown"),
    ],
)
def test_script_detection(text: str, expected: str):
    assert ScriptHeuristicDetector().detect_primary(text)[0] == expected


def test_normalization_is_conservative_and_unicode_safe():
    raw = "  హలో\u200b   ప్రపంచం\r\n\r\n\r\n  परीक्षा  "
    assert normalize_extracted_text(raw) == "హలో ప్రపంచం\n\nपरीक्षा"
    assert normalize_extracted_text("क्\u200dष") == "क्\u200dष"  # Preserve shaping joiner.


def test_cer_and_wer():
    assert character_error_rate("notice", "notice") == 0.0
    assert character_error_rate("abc", "adc") == pytest.approx(1 / 3)
    assert word_error_rate("one two three", "one too three") == pytest.approx(1 / 3)
    assert word_error_rate("", "") == 0.0
    assert word_error_rate("", "unexpected") == 1.0
    assert character_error_rate("expected", "") == 1.0


def test_telugu_cer_counts_unicode_codepoints():
    assert character_error_rate("తెలుగు", "తెలుగ") == pytest.approx(1 / len("తెలుగు"))
