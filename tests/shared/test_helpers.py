"""Tests for shared.helpers module."""

from shared.helpers import safe_percentage, safe_ratio


class TestSafePercentage:
    def test_normal(self):
        assert safe_percentage(25, 100) == 25.0

    def test_zero_denominator(self):
        assert safe_percentage(10, 0) == 0.0

    def test_nan_denominator(self):
        assert safe_percentage(10, float("nan")) == 0.0

    def test_rounds_to_two_decimals(self):
        assert safe_percentage(1, 3) == 33.33

    def test_zero_numerator(self):
        assert safe_percentage(0, 100) == 0.0

    def test_full_percentage(self):
        assert safe_percentage(50, 50) == 100.0

    def test_over_100(self):
        assert safe_percentage(200, 100) == 200.0


class TestSafeRatio:
    def test_normal(self):
        assert safe_ratio(25, 100) == 0.25

    def test_zero_denominator(self):
        assert safe_ratio(10, 0) == 0.0

    def test_nan_denominator(self):
        assert safe_ratio(10, float("nan")) == 0.0

    def test_custom_decimals(self):
        assert safe_ratio(1, 3, decimals=4) == 0.3333

    def test_default_two_decimals(self):
        assert safe_ratio(1, 3) == 0.33

    def test_zero_numerator(self):
        assert safe_ratio(0, 100) == 0.0
