"""Tests for DCTR analysis modules -- registration, validation, run output."""

import pytest

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.analytics.dctr.branches import DCTRBranches
from ars_analysis.analytics.dctr.funnel import DCTRFunnel
from ars_analysis.analytics.dctr.overlays import DCTROverlays
from ars_analysis.analytics.dctr.penetration import DCTRPenetration
from ars_analysis.analytics.dctr.trends import DCTRTrends

# -- Module Attribute Tests ---------------------------------------------------


class TestDCTRModuleAttributes:
    """All 5 DCTR modules have correct attributes and registration."""

    @pytest.mark.parametrize("cls, mod_id, section", [
        (DCTRPenetration, "dctr.penetration", "dctr"),
        (DCTRTrends, "dctr.trends", "dctr"),
        (DCTRBranches, "dctr.branches", "dctr"),
        (DCTRFunnel, "dctr.funnel", "dctr"),
        (DCTROverlays, "dctr.overlays", "dctr"),
    ])
    def test_module_id_and_section(self, cls, mod_id, section):
        mod = cls()
        assert mod.module_id == mod_id
        assert mod.section == section

    @pytest.mark.parametrize("cls", [
        DCTRPenetration, DCTRTrends, DCTRBranches, DCTRFunnel, DCTROverlays,
    ])
    def test_has_required_columns(self, cls):
        mod = cls()
        assert "Date Opened" in mod.required_columns
        assert "Debit?" in mod.required_columns

    @pytest.mark.parametrize("cls", [
        DCTRPenetration, DCTRTrends, DCTRBranches, DCTRFunnel, DCTROverlays,
    ])
    def test_has_display_name(self, cls):
        mod = cls()
        assert mod.display_name != ""


# -- Validation Tests ---------------------------------------------------------


class TestDCTRValidation:
    def test_penetration_validates_with_correct_data(self, dctr_ctx):
        mod = DCTRPenetration()
        errors = mod.validate(dctr_ctx)
        assert errors == []

    def test_penetration_fails_without_debit_column(self, dctr_ctx):
        dctr_ctx.data = dctr_ctx.data.drop(columns=["Debit?"])
        mod = DCTRPenetration()
        errors = mod.validate(dctr_ctx)
        assert len(errors) > 0
        assert "Debit?" in errors[0]

    def test_branches_validates_with_correct_data(self, dctr_ctx):
        mod = DCTRBranches()
        errors = mod.validate(dctr_ctx)
        assert errors == []


# -- Run Tests ----------------------------------------------------------------


class TestDCTRPenetrationRun:
    def test_returns_analysis_results(self, dctr_ctx):
        mod = DCTRPenetration()
        results = mod.run(dctr_ctx)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, AnalysisResult)

    def test_results_have_slide_ids(self, dctr_ctx):
        mod = DCTRPenetration()
        results = mod.run(dctr_ctx)
        slide_ids = {r.slide_id for r in results}
        assert "DCTR-1" in slide_ids

    def test_results_have_excel_data(self, dctr_ctx):
        mod = DCTRPenetration()
        results = mod.run(dctr_ctx)
        # At least DCTR-1 should have excel data
        dctr_1 = [r for r in results if r.slide_id == "DCTR-1"]
        assert len(dctr_1) == 1
        assert dctr_1[0].excel_data is not None

    def test_all_results_marked_success(self, dctr_ctx):
        mod = DCTRPenetration()
        results = mod.run(dctr_ctx)
        for r in results:
            assert r.success is True, f"{r.slide_id} failed: {r.error}"

    def test_stores_results_in_context(self, dctr_ctx):
        mod = DCTRPenetration()
        mod.run(dctr_ctx)
        assert "dctr_1" in dctr_ctx.results


class TestDCTRTrendsRun:
    def test_returns_analysis_results(self, dctr_ctx):
        # Trends depends on penetration results
        DCTRPenetration().run(dctr_ctx)
        mod = DCTRTrends()
        results = mod.run(dctr_ctx)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, AnalysisResult)

    def test_all_results_marked_success(self, dctr_ctx):
        DCTRPenetration().run(dctr_ctx)
        mod = DCTRTrends()
        results = mod.run(dctr_ctx)
        for r in results:
            assert r.success is True, f"{r.slide_id} failed: {r.error}"


class TestDCTRBranchesRun:
    def test_returns_analysis_results(self, dctr_ctx):
        mod = DCTRBranches()
        results = mod.run(dctr_ctx)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, AnalysisResult)

    def test_all_results_marked_success(self, dctr_ctx):
        mod = DCTRBranches()
        results = mod.run(dctr_ctx)
        for r in results:
            assert r.success is True, f"{r.slide_id} failed: {r.error}"

    def test_branch_dctr_has_excel_data(self, dctr_ctx):
        mod = DCTRBranches()
        results = mod.run(dctr_ctx)
        dctr_9 = [r for r in results if r.slide_id == "DCTR-9"]
        assert len(dctr_9) == 1
        assert dctr_9[0].excel_data is not None


class TestDCTRFunnelRun:
    def test_returns_analysis_results(self, dctr_ctx):
        mod = DCTRFunnel()
        results = mod.run(dctr_ctx)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, AnalysisResult)

    def test_all_results_marked_success(self, dctr_ctx):
        mod = DCTRFunnel()
        results = mod.run(dctr_ctx)
        for r in results:
            assert r.success is True, f"{r.slide_id} failed: {r.error}"


class TestDCTROverlaysRun:
    def test_returns_analysis_results(self, dctr_ctx):
        mod = DCTROverlays()
        results = mod.run(dctr_ctx)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, AnalysisResult)

    def test_all_results_marked_success(self, dctr_ctx):
        mod = DCTROverlays()
        results = mod.run(dctr_ctx)
        for r in results:
            assert r.success is True, f"{r.slide_id} failed: {r.error}"

    def test_account_age_has_chart(self, dctr_ctx):
        mod = DCTROverlays()
        results = mod.run(dctr_ctx)
        dctr_10 = [r for r in results if r.slide_id == "DCTR-10"]
        assert len(dctr_10) == 1
        # Chart should be generated since charts_dir is set
        assert dctr_10[0].chart_path is not None


class TestDCTRChartGeneration:
    """Verify charts are created in the charts_dir."""

    def test_penetration_generates_charts(self, dctr_ctx):
        charts_dir = dctr_ctx.paths.charts_dir
        charts_dir.mkdir(parents=True, exist_ok=True)
        mod = DCTRPenetration()
        results = mod.run(dctr_ctx)
        chart_results = [r for r in results if r.chart_path is not None]
        assert len(chart_results) > 0

    def test_branches_top10_chart(self, dctr_ctx):
        charts_dir = dctr_ctx.paths.charts_dir
        charts_dir.mkdir(parents=True, exist_ok=True)
        mod = DCTRBranches()
        results = mod.run(dctr_ctx)
        dctr_9 = [r for r in results if r.slide_id == "DCTR-9"]
        if dctr_9:
            assert dctr_9[0].chart_path is not None
