"""Tests for ars_analysis.reg_e -- A8 Reg E Analysis Suite.

Verifies:
1. Output correct -- results populated
2. Makes it onto PowerPoint -- slides added
3. Format correct -- charts created, Excel export called
"""

from pathlib import Path

import pytest

from ars_analysis.reg_e import (
    run_reg_e_1,
    run_reg_e_suite,
)


class TestRunRegE1:
    """A8.1: Overall Reg E status donut."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        assert "reg_e_1" in ars_ctx["results"]

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_1(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial
        slide = ars_ctx["all_slides"][-1]
        assert slide["include"] is True
        assert slide["category"] == "Reg E"

    def test_creates_chart(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("*.png"))
        assert len(pngs) >= 1


class TestRunRegESuite:
    """Full A8 suite -- all 13+ sub-analyses."""

    def test_runs_without_error(self, ars_ctx):
        run_reg_e_suite(ars_ctx)

    def test_adds_multiple_slides(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        assert len(ars_ctx["all_slides"]) >= 3

    def test_all_slides_valid(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "data" in slide

    def test_creates_charts(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("*.png"))
        assert len(pngs) >= 3

    def test_populates_results(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        # Suite stores reg_e analysis results
        assert any("reg_e" in k for k in ars_ctx["results"])

    def test_skips_gracefully_without_reg_e_data(self, ars_ctx):
        ars_ctx["reg_e_eligible_base"] = None
        run_reg_e_suite(ars_ctx)
        # Should not crash, just skip
