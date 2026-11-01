"""
Unit tests for the normalization utilities.

Tests cover Indian-format INR amounts (lakh, crore, Indian commas),
percentage normalization, and CGPA normalization.
"""

import pytest

from services.nlp.validation.normalizers import (
    normalize_inr,
    normalize_percentage,
    normalize_cgpa,
)


class TestNormalizeINR:
    def test_lakh_symbol(self):
        assert normalize_inr("₹2.5 lakh") == 250000.0

    def test_lakh_rs_prefix(self):
        assert normalize_inr("Rs. 2.5 lakh") == 250000.0

    def test_lakh_text_only(self):
        assert normalize_inr("2.5 lakh") == 250000.0

    def test_lakh_hindi(self):
        assert normalize_inr("2.5 लाख") == 250000.0

    def test_lakh_telugu(self):
        assert normalize_inr("2.5 లక్షలు") == 250000.0

    def test_indian_comma_format(self):
        assert normalize_inr("₹2,50,000/-") == 250000.0

    def test_western_comma_format(self):
        assert normalize_inr("Rs. 2,50,000") == 250000.0

    def test_plain_integer(self):
        assert normalize_inr("250000") == 250000.0

    def test_crore(self):
        assert normalize_inr("5 crore") == 5_00_00_000.0

    def test_symbol_only_fails_gracefully(self):
        assert normalize_inr("₹") is None

    def test_garbage_returns_none(self):
        assert normalize_inr("not a number") is None

    def test_empty_string(self):
        assert normalize_inr("") is None

    def test_500_rupees(self):
        assert normalize_inr("₹500/-") == 500.0

    def test_1_lakh(self):
        assert normalize_inr("₹1 lakh") == 100000.0

    def test_300000_inr(self):
        assert normalize_inr("3,00,000") == 300000.0


class TestNormalizePercentage:
    def test_75_percent(self):
        assert normalize_percentage("75%") == 75.0

    def test_decimal_percent(self):
        assert normalize_percentage("75.5%") == 75.5

    def test_bare_number(self):
        assert normalize_percentage("82") == 82.0

    def test_out_of_range_returns_none(self):
        assert normalize_percentage("150%") is None

    def test_negative_returns_none(self):
        assert normalize_percentage("-5%") is None

    def test_empty(self):
        assert normalize_percentage("") is None

    def test_garbage(self):
        assert normalize_percentage("marks are high") is None

    def test_zero(self):
        assert normalize_percentage("0%") == 0.0

    def test_100(self):
        assert normalize_percentage("100%") == 100.0


class TestNormalizeCGPA:
    def test_cgpa_upper(self):
        assert normalize_cgpa("7.5 CGPA") == 7.5

    def test_cgpa_lower(self):
        assert normalize_cgpa("6.0 cgpa") == 6.0

    def test_gpa(self):
        assert normalize_cgpa("3.8 GPA") == 3.8

    def test_empty(self):
        assert normalize_cgpa("") is None

    def test_no_match(self):
        assert normalize_cgpa("excellent marks") is None
