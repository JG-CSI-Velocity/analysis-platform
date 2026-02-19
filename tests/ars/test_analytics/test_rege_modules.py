"""Tests for the 3 Reg E analysis modules: status, branches, dimensions."""

import pytest

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.analytics.rege.branches import RegEBranches
from ars_analysis.analytics.rege.dimensions import RegEDimensions
from ars_analysis.analytics.rege.status import RegEStatus

# ---------------------------------------------------------------------------
# Module attributes
# ---------------------------------------------------------------------------

class TestModuleAttributes:
    """All 3 modules have correct class attributes."""

    @pytest.mark.parametrize("cls, mid, section", [
        (RegEStatus, "rege.status", "rege"),
        (RegEBranches, "rege.branches", "rege"),
        (RegEDimensions, "rege.dimensions", "rege"),
    ])
    def test_module_id_and_section(self, cls, mid, section):
        m = cls()
        assert m.module_id == mid
        assert m.section == section

    @pytest.mark.parametrize("cls", [RegEStatus, RegEBranches, RegEDimensions])
    def test_has_display_name(self, cls):
        assert cls.display_name

    @pytest.mark.parametrize("cls", [RegEStatus, RegEBranches, RegEDimensions])
    def test_required_columns(self, cls):
        m = cls()
        assert "Date Opened" in m.required_columns
        assert "Debit?" in m.required_columns
        assert "Business?" in m.required_columns


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    """validate() checks prerequisites."""

    @pytest.mark.parametrize("cls", [RegEStatus, RegEBranches, RegEDimensions])
    def test_passes_with_valid_data(self, cls, rege_ctx):
        m = cls()
        errors = m.validate(rege_ctx)
        assert errors == []

    @pytest.mark.parametrize("cls", [RegEStatus, RegEBranches, RegEDimensions])
    def test_fails_without_data(self, cls, rege_ctx):
        rege_ctx.data = None
        m = cls()
        errors = m.validate(rege_ctx)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# RegEStatus
# ---------------------------------------------------------------------------

class TestRegEStatus:
    """RegEStatus.run() produces A8.1, A8.2, A8.3, A8.12."""

    def test_run_returns_results(self, rege_ctx):
        results = RegEStatus().run(rege_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)
        assert len(results) == 4

    def test_slide_ids(self, rege_ctx):
        results = RegEStatus().run(rege_ctx)
        ids = {r.slide_id for r in results}
        assert ids == {"A8.1", "A8.2", "A8.3", "A8.12"}

    def test_all_success(self, rege_ctx):
        results = RegEStatus().run(rege_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, rege_ctx):
        results = RegEStatus().run(rege_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_stores_ctx_results(self, rege_ctx):
        RegEStatus().run(rege_ctx)
        assert "reg_e_1" in rege_ctx.results
        assert "reg_e_2" in rege_ctx.results
        assert "reg_e_3" in rege_ctx.results
        assert "reg_e_12" in rege_ctx.results

    def test_overall_rate(self, rege_ctx):
        RegEStatus().run(rege_ctx)
        r1 = rege_ctx.results["reg_e_1"]
        assert 0 < r1["opt_in_rate"] < 1
        assert r1["total_base"] > 0


# ---------------------------------------------------------------------------
# RegEBranches
# ---------------------------------------------------------------------------

class TestRegEBranches:
    """RegEBranches.run() produces A8.4a, A8.4b, A8.4c, A8.13."""

    def test_run_returns_results(self, rege_ctx):
        results = RegEBranches().run(rege_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)
        assert len(results) == 4

    def test_slide_ids(self, rege_ctx):
        results = RegEBranches().run(rege_ctx)
        ids = {r.slide_id for r in results}
        assert ids == {"A8.4a", "A8.4b", "A8.4c", "A8.13"}

    def test_all_success(self, rege_ctx):
        results = RegEBranches().run(rege_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_stores_comparison(self, rege_ctx):
        RegEBranches().run(rege_ctx)
        assert "reg_e_4" in rege_ctx.results
        comp = rege_ctx.results["reg_e_4"]["comparison"]
        assert len(comp) > 0

    def test_pivot_stored(self, rege_ctx):
        RegEBranches().run(rege_ctx)
        assert "reg_e_13" in rege_ctx.results
        assert "pivot" in rege_ctx.results["reg_e_13"]


# ---------------------------------------------------------------------------
# RegEDimensions
# ---------------------------------------------------------------------------

class TestRegEDimensions:
    """RegEDimensions.run() produces A8.5, A8.6, A8.7, A8.10, A8.11."""

    def test_run_returns_results(self, rege_ctx):
        results = RegEDimensions().run(rege_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)
        assert len(results) == 5

    def test_slide_ids(self, rege_ctx):
        results = RegEDimensions().run(rege_ctx)
        ids = {r.slide_id for r in results}
        assert ids == {"A8.5", "A8.6", "A8.7", "A8.10", "A8.11"}

    def test_all_success(self, rege_ctx):
        results = RegEDimensions().run(rege_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_funnel_charts(self, rege_ctx):
        results = RegEDimensions().run(rege_ctx)
        funnel_results = [r for r in results if r.slide_id in {"A8.10", "A8.11"}]
        for r in funnel_results:
            assert r.chart_path is not None
            assert r.chart_path.exists()

    def test_stores_results(self, rege_ctx):
        RegEDimensions().run(rege_ctx)
        assert "reg_e_5" in rege_ctx.results
        assert "reg_e_6" in rege_ctx.results
        assert "reg_e_7" in rege_ctx.results
        assert "reg_e_10" in rege_ctx.results
        assert "reg_e_11" in rege_ctx.results

    def test_account_age_data(self, rege_ctx):
        RegEDimensions().run(rege_ctx)
        data = rege_ctx.results["reg_e_5"]["data"]
        assert "TOTAL" in data["Account Age"].values

    def test_product_code_data(self, rege_ctx):
        RegEDimensions().run(rege_ctx)
        data = rege_ctx.results["reg_e_7"]["data"]
        assert "DDA" in data["Product Code"].values
