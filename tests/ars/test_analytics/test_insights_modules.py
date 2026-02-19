"""Tests for insights synthesis and conclusions modules."""

import pytest

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.analytics.insights.conclusions import InsightsConclusions
from ars_analysis.analytics.insights.synthesis import InsightsSynthesis

# ---------------------------------------------------------------------------
# Module attributes
# ---------------------------------------------------------------------------


class TestModuleAttributes:
    """Both insights modules have correct class attributes."""

    def test_synthesis_module_id(self):
        assert InsightsSynthesis().module_id == "insights.synthesis"

    def test_synthesis_section(self):
        assert InsightsSynthesis().section == "insights"

    def test_conclusions_module_id(self):
        assert InsightsConclusions().module_id == "insights.conclusions"

    def test_conclusions_section(self):
        assert InsightsConclusions().section == "insights"

    def test_display_names(self):
        assert InsightsSynthesis.display_name
        assert InsightsConclusions.display_name

    def test_no_required_columns(self):
        assert InsightsSynthesis.required_columns == ()
        assert InsightsConclusions.required_columns == ()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    """validate() passes without data since insights reads ctx.results."""

    def test_synthesis_passes(self, insights_ctx):
        assert InsightsSynthesis().validate(insights_ctx) == []

    def test_conclusions_passes(self, insights_ctx):
        assert InsightsConclusions().validate(insights_ctx) == []

    def test_synthesis_passes_no_data(self, insights_ctx):
        insights_ctx.data = None
        assert InsightsSynthesis().validate(insights_ctx) == []

    def test_conclusions_passes_no_data(self, insights_ctx):
        insights_ctx.data = None
        assert InsightsConclusions().validate(insights_ctx) == []


# ---------------------------------------------------------------------------
# InsightsSynthesis (S1-S5)
# ---------------------------------------------------------------------------


class TestInsightsSynthesis:
    """InsightsSynthesis.run() produces S1-S5 slides."""

    def test_run_returns_results(self, insights_ctx):
        results = InsightsSynthesis().run(insights_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, insights_ctx):
        results = InsightsSynthesis().run(insights_ctx)
        ids = {r.slide_id for r in results}
        assert "S1" in ids
        assert "S2" in ids
        assert "S3" in ids
        assert "S4" in ids
        assert "S5" in ids

    def test_all_success(self, insights_ctx):
        results = InsightsSynthesis().run(insights_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, insights_ctx):
        results = InsightsSynthesis().run(insights_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_notes_contain_dollars(self, insights_ctx):
        results = InsightsSynthesis().run(insights_ctx)
        for r in results:
            assert "$" in r.notes, f"{r.slide_id} notes missing $ amounts"

    def test_s1_stores_results(self, insights_ctx):
        InsightsSynthesis().run(insights_ctx)
        s1 = insights_ctx.results.get("impact_s1", {})
        assert s1["total_gap"] > 0
        assert s1["realistic_capture"] > 0

    def test_s2_stores_results(self, insights_ctx):
        InsightsSynthesis().run(insights_ctx)
        s2 = insights_ctx.results.get("impact_s2", {})
        assert s2["revenue_destroyed"] > 0

    def test_s5_cascade_sum(self, insights_ctx):
        InsightsSynthesis().run(insights_ctx)
        s5 = insights_ctx.results.get("impact_s5", {})
        expected = s5["stream_1"] + s5["stream_2"] + s5["stream_3"]
        assert s5["total_cascade"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# InsightsConclusions (S6-S8)
# ---------------------------------------------------------------------------


class TestInsightsConclusions:
    """InsightsConclusions.run() produces S6-S8 slides."""

    def test_run_returns_results(self, insights_ctx):
        results = InsightsConclusions().run(insights_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, insights_ctx):
        results = InsightsConclusions().run(insights_ctx)
        ids = {r.slide_id for r in results}
        assert "S6" in ids
        assert "S7" in ids
        assert "S8" in ids

    def test_all_success(self, insights_ctx):
        results = InsightsConclusions().run(insights_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, insights_ctx):
        results = InsightsConclusions().run(insights_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_notes_contain_dollars(self, insights_ctx):
        results = InsightsConclusions().run(insights_ctx)
        for r in results:
            assert "$" in r.notes, f"{r.slide_id} notes missing $ amounts"

    def test_s6_stores_results(self, insights_ctx):
        InsightsConclusions().run(insights_ctx)
        s6 = insights_ctx.results.get("impact_s6", {})
        assert s6["total_addressable"] > 0
        assert s6["total_realistic"] > 0

    def test_s7_stores_results(self, insights_ctx):
        InsightsConclusions().run(insights_ctx)
        s7 = insights_ctx.results.get("impact_s7", {})
        assert s7["new_debit_accounts"] > 0
        assert s7["total_annual_gain"] > 0

    def test_s8_combined(self, insights_ctx):
        InsightsConclusions().run(insights_ctx)
        s8 = insights_ctx.results.get("impact_s8", {})
        expected = s8["action_1"] + s8["action_2"] + s8["action_3"]
        assert s8["combined"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Edge cases -- graceful failure when upstream data missing
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Modules fail gracefully when upstream results are missing."""

    def test_synthesis_empty_results(self, insights_ctx):
        insights_ctx.results.clear()
        results = InsightsSynthesis().run(insights_ctx)
        assert isinstance(results, list)
        assert len(results) == 5
        for r in results:
            assert not r.success

    def test_conclusions_empty_results(self, insights_ctx):
        insights_ctx.results.clear()
        results = InsightsConclusions().run(insights_ctx)
        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert not r.success
