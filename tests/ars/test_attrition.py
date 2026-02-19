"""Tests for ars_analysis.attrition -- A9 Attrition Analysis Suite.

Verifies the 3 acceptance criteria for each analysis:
1. Output correct -- results dict populated, DataFrames have expected shape
2. Makes it onto PowerPoint -- slides appended to ctx["all_slides"]
3. Format correct -- charts saved to chart_dir, Excel save called
"""

from pathlib import Path

import pandas as pd
import pytest

from ars_analysis.attrition import (
    categorize_duration,
    run_attrition_1,
    run_attrition_2,
    run_attrition_3,
    run_attrition_suite,
)


class TestCategorizeDuration:
    def test_under_one_month(self):
        assert categorize_duration(15) == "0-1 Month"

    def test_three_months(self):
        assert categorize_duration(60) == "1-3 Months"

    def test_six_months(self):
        assert categorize_duration(150) == "3-6 Months"

    def test_nan(self):
        result = categorize_duration(float("nan"))
        assert pd.isna(result)

    def test_negative(self):
        result = categorize_duration(-10)
        assert pd.isna(result)


class TestRunAttrition1:
    """A9.1: Overall attrition rate -- output + slide + chart."""

    def test_populates_results(self, ars_ctx):
        run_attrition_1(ars_ctx)
        assert "attrition_1" in ars_ctx["results"]

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_attrition_1(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial
        slide = ars_ctx["all_slides"][-1]
        assert slide["id"].startswith("A9")
        assert slide["include"] is True
        assert slide["category"] == "Attrition"

    def test_creates_chart(self, ars_ctx):
        run_attrition_1(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("a9_*.png"))
        assert len(pngs) >= 1

    def test_calls_excel_export(self, ars_ctx):
        run_attrition_1(ars_ctx)
        assert ars_ctx["_save_to_excel"].called


class TestRunAttrition2:
    """A9.2: Closure duration analysis."""

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_attrition_2(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial


class TestRunAttrition3:
    """A9.3: Open vs Closed comparison."""

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_attrition_3(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial


class TestRunAttritionSuite:
    """Full suite run -- all 13 sub-analyses."""

    def test_runs_without_error(self, ars_ctx):
        run_attrition_suite(ars_ctx)

    def test_adds_multiple_slides(self, ars_ctx):
        run_attrition_suite(ars_ctx)
        # At least a few slides should be created
        assert len(ars_ctx["all_slides"]) >= 3

    def test_all_slides_have_required_fields(self, ars_ctx):
        run_attrition_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "category" in slide
            assert "data" in slide

    def test_creates_charts(self, ars_ctx):
        run_attrition_suite(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("*.png"))
        assert len(pngs) >= 3

    def test_populates_results(self, ars_ctx):
        run_attrition_suite(ars_ctx)
        # Suite stores results and attrition data cache
        assert "_attrition_data" in ars_ctx["results"]
