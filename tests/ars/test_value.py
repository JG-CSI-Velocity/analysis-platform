"""Tests for ars_analysis.value -- A11 Value Analysis Suite.

Verifies:
1. Output correct -- value comparison data populated
2. Makes it onto PowerPoint -- slides added
3. Format correct -- charts created, Excel export called
"""

from pathlib import Path

import pytest

from ars_analysis.value import (
    _find_col,
    run_value_1,
    run_value_2,
    run_value_suite,
)


class TestFindCol:
    def test_finds_spend_col(self, ars_ctx):
        df = ars_ctx["eligible_personal"]
        result = _find_col(df, "spend")
        assert result == "L12M Spend"

    def test_finds_items_col(self, ars_ctx):
        df = ars_ctx["eligible_personal"]
        result = _find_col(df, "items")
        assert result == "L12M Items"

    def test_returns_none_for_missing(self, ars_ctx):
        df = ars_ctx["eligible_personal"]
        assert _find_col(df, "nonexistent_xyz") is None


class TestRunValue1:
    """A11.1: Value of a Debit Card."""

    def test_populates_results(self, ars_ctx):
        run_value_1(ars_ctx)
        assert "value_1" in ars_ctx["results"]

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_value_1(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial
        slide = ars_ctx["all_slides"][-1]
        assert slide["include"] is True
        assert slide["category"] == "Value"

    def test_creates_chart(self, ars_ctx):
        run_value_1(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("*.png"))
        assert len(pngs) >= 1

    def test_calls_excel_export(self, ars_ctx):
        run_value_1(ars_ctx)
        assert ars_ctx["_save_to_excel"].called


class TestRunValue2:
    """A11.2: Value of Reg E Opt-In."""

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_value_2(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial


class TestRunValueSuite:
    """Full A11 suite."""

    def test_runs_without_error(self, ars_ctx):
        run_value_suite(ars_ctx)

    def test_adds_slides(self, ars_ctx):
        run_value_suite(ars_ctx)
        assert len(ars_ctx["all_slides"]) >= 1

    def test_all_slides_valid(self, ars_ctx):
        run_value_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "data" in slide
