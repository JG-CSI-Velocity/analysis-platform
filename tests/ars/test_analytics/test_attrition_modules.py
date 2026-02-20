"""Tests for all three attrition analysis modules."""

import pytest

from ars_analysis.analytics.attrition.dimensions import AttritionDimensions
from ars_analysis.analytics.attrition.impact import AttritionImpact
from ars_analysis.analytics.attrition.rates import AttritionRates
from ars_analysis.analytics.base import AnalysisResult

# ---------------------------------------------------------------------------
# Module attributes
# ---------------------------------------------------------------------------


class TestModuleAttributes:
    """All attrition modules have correct class attributes."""

    def test_rates_module_id(self):
        assert AttritionRates().module_id == "attrition.rates"

    def test_rates_section(self):
        assert AttritionRates().section == "attrition"

    def test_dimensions_module_id(self):
        assert AttritionDimensions().module_id == "attrition.dimensions"

    def test_dimensions_section(self):
        assert AttritionDimensions().section == "attrition"

    def test_impact_module_id(self):
        assert AttritionImpact().module_id == "attrition.impact"

    def test_impact_section(self):
        assert AttritionImpact().section == "attrition"

    def test_display_names(self):
        assert AttritionRates.display_name
        assert AttritionDimensions.display_name
        assert AttritionImpact.display_name

    def test_required_columns(self):
        for cls in [AttritionRates, AttritionDimensions, AttritionImpact]:
            assert "Date Opened" in cls.required_columns
            assert "Date Closed" in cls.required_columns


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    """validate() checks prerequisites."""

    def test_rates_passes(self, attrition_ctx):
        assert AttritionRates().validate(attrition_ctx) == []

    def test_dimensions_passes(self, attrition_ctx):
        assert AttritionDimensions().validate(attrition_ctx) == []

    def test_impact_passes(self, attrition_ctx):
        assert AttritionImpact().validate(attrition_ctx) == []

    def test_fails_without_data(self, attrition_ctx):
        attrition_ctx.data = None
        for cls in [AttritionRates, AttritionDimensions, AttritionImpact]:
            errors = cls().validate(attrition_ctx)
            assert len(errors) > 0


# ---------------------------------------------------------------------------
# AttritionRates (A9.1, A9.2, A9.3)
# ---------------------------------------------------------------------------


class TestAttritionRates:
    """AttritionRates.run() produces overall, duration, open-vs-closed."""

    def test_run_returns_results(self, attrition_ctx):
        results = AttritionRates().run(attrition_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, attrition_ctx):
        results = AttritionRates().run(attrition_ctx)
        ids = {r.slide_id for r in results}
        assert "A9.1" in ids
        assert "A9.2" in ids
        assert "A9.3" in ids

    def test_all_success(self, attrition_ctx):
        results = AttritionRates().run(attrition_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, attrition_ctx):
        results = AttritionRates().run(attrition_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_stores_attrition_1(self, attrition_ctx):
        AttritionRates().run(attrition_ctx)
        a1 = attrition_ctx.results.get("attrition_1", {})
        assert a1["total"] == 60
        assert a1["closed"] == 30
        assert a1["overall_rate"] == pytest.approx(0.5)

    def test_stores_first_year_pct(self, attrition_ctx):
        AttritionRates().run(attrition_ctx)
        a2 = attrition_ctx.results.get("attrition_2", {})
        assert "first_year_pct" in a2


# ---------------------------------------------------------------------------
# AttritionDimensions (A9.4, A9.5, A9.6, A9.7, A9.8)
# ---------------------------------------------------------------------------


class TestAttritionDimensions:
    """AttritionDimensions.run() produces per-dimension analyses."""

    def test_run_returns_results(self, attrition_ctx):
        results = AttritionDimensions().run(attrition_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, attrition_ctx):
        results = AttritionDimensions().run(attrition_ctx)
        ids = {r.slide_id for r in results}
        assert "A9.4" in ids
        assert "A9.5" in ids
        assert "A9.6" in ids
        assert "A9.7" in ids
        assert "A9.8" in ids

    def test_all_success(self, attrition_ctx):
        results = AttritionDimensions().run(attrition_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, attrition_ctx):
        results = AttritionDimensions().run(attrition_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_branch_count_stored(self, attrition_ctx):
        AttritionDimensions().run(attrition_ctx)
        a4 = attrition_ctx.results.get("attrition_4", {})
        assert a4["n_branches"] == 3


# ---------------------------------------------------------------------------
# AttritionImpact (A9.9, A9.10, A9.11, A9.12, A9.13)
# ---------------------------------------------------------------------------


class TestAttritionImpact:
    """AttritionImpact.run() produces retention/revenue/velocity analyses."""

    def test_run_returns_results(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        ids = {r.slide_id for r in results}
        assert "A9.9" in ids
        assert "A9.10" in ids
        assert "A9.11" in ids
        assert "A9.12" in ids
        assert "A9.13" in ids

    def test_a9_9_success(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        a9_9 = [r for r in results if r.slide_id == "A9.9"][0]
        assert a9_9.success, f"A9.9 failed: {a9_9.error}"

    def test_a9_10_success(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        a9_10 = [r for r in results if r.slide_id == "A9.10"][0]
        assert a9_10.success, f"A9.10 failed: {a9_10.error}"

    def test_a9_11_success(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        a9_11 = [r for r in results if r.slide_id == "A9.11"][0]
        assert a9_11.success, f"A9.11 failed: {a9_11.error}"

    def test_a9_12_success(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        a9_12 = [r for r in results if r.slide_id == "A9.12"][0]
        assert a9_12.success, f"A9.12 failed: {a9_12.error}"

    def test_a9_13_success(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        a9_13 = [r for r in results if r.slide_id == "A9.13"][0]
        assert a9_13.success, f"A9.13 failed: {a9_13.error}"

    def test_charts_generated(self, attrition_ctx):
        results = AttritionImpact().run(attrition_ctx)
        successful = [r for r in results if r.success]
        for r in successful:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_stores_retention_lift(self, attrition_ctx):
        AttritionImpact().run(attrition_ctx)
        a9 = attrition_ctx.results.get("attrition_9", {})
        assert "retention_lift" in a9

    def test_stores_revenue_impact(self, attrition_ctx):
        AttritionImpact().run(attrition_ctx)
        a11 = attrition_ctx.results.get("attrition_11", {})
        assert "total_lost" in a11
        assert a11["total_lost"] > 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestAttritionEdgeCases:
    """Edge case handling across attrition modules."""

    def test_no_closed_accounts(self, attrition_ctx):
        """Remove all closed accounts -> graceful failure."""
        df = attrition_ctx.data.copy()
        df["Date Closed"] = None
        attrition_ctx.data = df
        attrition_ctx.results.pop("_attrition_data", None)

        results = AttritionRates().run(attrition_ctx)
        # A9.1 should succeed (0% attrition), A9.2/A9.3 should fail gracefully
        a9_1 = [r for r in results if r.slide_id == "A9.1"][0]
        assert a9_1.success
        a9_2 = [r for r in results if r.slide_id == "A9.2"][0]
        assert not a9_2.success

    def test_no_eligibility_config(self, attrition_ctx):
        """No eligible codes -> A9.13 fails gracefully."""
        attrition_ctx.client.eligible_stat_codes = []
        attrition_ctx.client.eligible_prod_codes = []
        results = AttritionImpact().run(attrition_ctx)
        a9_13 = [r for r in results if r.slide_id == "A9.13"][0]
        assert not a9_13.success

    def test_no_date_range_skips_velocity(self, attrition_ctx):
        """No start/end date -> A9.12 fails gracefully."""
        attrition_ctx.start_date = None
        attrition_ctx.end_date = None
        results = AttritionImpact().run(attrition_ctx)
        a9_12 = [r for r in results if r.slide_id == "A9.12"][0]
        assert not a9_12.success
