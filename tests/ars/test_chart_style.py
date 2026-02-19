"""Tests for ars_analysis.chart_style -- shared color + size constants."""

from ars_analysis.chart_style import (
    ANNOTATION_SIZE,
    AXIS_LABEL_SIZE,
    BAR_ALPHA,
    BAR_EDGE,
    BUSINESS,
    DATA_LABEL_SIZE,
    HISTORICAL,
    LEGEND_SIZE,
    NEGATIVE,
    NEUTRAL,
    PCT_FORMATTER,
    PERSONAL,
    POSITIVE,
    SILVER,
    TEAL,
    TICK_SIZE,
    TITLE_SIZE,
    TTM,
)


class TestSemanticColors:
    def test_all_hex(self):
        for name, val in [
            ("PERSONAL", PERSONAL),
            ("BUSINESS", BUSINESS),
            ("HISTORICAL", HISTORICAL),
            ("TTM", TTM),
            ("POSITIVE", POSITIVE),
            ("NEGATIVE", NEGATIVE),
            ("NEUTRAL", NEUTRAL),
            ("SILVER", SILVER),
            ("TEAL", TEAL),
        ]:
            assert val.startswith("#"), f"{name} not hex: {val}"
            assert len(val) == 7, f"{name} wrong length: {val}"


class TestFontSizes:
    def test_positive_ints(self):
        for name, val in [
            ("TITLE_SIZE", TITLE_SIZE),
            ("AXIS_LABEL_SIZE", AXIS_LABEL_SIZE),
            ("DATA_LABEL_SIZE", DATA_LABEL_SIZE),
            ("TICK_SIZE", TICK_SIZE),
            ("LEGEND_SIZE", LEGEND_SIZE),
            ("ANNOTATION_SIZE", ANNOTATION_SIZE),
        ]:
            assert isinstance(val, int) and val > 0, f"{name} invalid: {val}"


class TestBarDefaults:
    def test_alpha_in_range(self):
        assert 0 < BAR_ALPHA <= 1

    def test_edge_is_string(self):
        assert isinstance(BAR_EDGE, str)


class TestPctFormatter:
    def test_formats_percent(self):
        result = PCT_FORMATTER(50, None)
        assert result == "50%"

    def test_formats_zero(self):
        assert PCT_FORMATTER(0, None) == "0%"
