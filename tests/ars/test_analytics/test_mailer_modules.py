"""Tests for all three mailer analysis modules."""

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.analytics.mailer.impact import MailerImpact
from ars_analysis.analytics.mailer.insights import MailerInsights
from ars_analysis.analytics.mailer.response import MailerResponse

# ---------------------------------------------------------------------------
# Module attributes
# ---------------------------------------------------------------------------


class TestModuleAttributes:
    """All mailer modules have correct class attributes."""

    def test_insights_module_id(self):
        assert MailerInsights().module_id == "mailer.insights"

    def test_insights_section(self):
        assert MailerInsights().section == "mailer"

    def test_response_module_id(self):
        assert MailerResponse().module_id == "mailer.response"

    def test_response_section(self):
        assert MailerResponse().section == "mailer"

    def test_impact_module_id(self):
        assert MailerImpact().module_id == "mailer.impact"

    def test_impact_section(self):
        assert MailerImpact().section == "mailer"

    def test_display_names(self):
        assert MailerInsights.display_name
        assert MailerResponse.display_name
        assert MailerImpact.display_name


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    """validate() checks prerequisites."""

    def test_insights_passes(self, mailer_ctx):
        assert MailerInsights().validate(mailer_ctx) == []

    def test_response_passes(self, mailer_ctx):
        assert MailerResponse().validate(mailer_ctx) == []

    def test_impact_passes(self, mailer_ctx):
        assert MailerImpact().validate(mailer_ctx) == []

    def test_fails_without_data(self, mailer_ctx):
        mailer_ctx.data = None
        for cls in [MailerInsights, MailerResponse, MailerImpact]:
            errors = cls().validate(mailer_ctx)
            assert len(errors) > 0


# ---------------------------------------------------------------------------
# MailerInsights (A12)
# ---------------------------------------------------------------------------


class TestMailerInsights:
    """MailerInsights.run() produces per-month spend/swipe slides."""

    def test_run_returns_results(self, mailer_ctx):
        results = MailerInsights().run(mailer_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_count(self, mailer_ctx):
        """2 months x 2 metrics (Swipes + Spend) = 4 slides."""
        results = MailerInsights().run(mailer_ctx)
        assert len(results) == 4

    def test_slide_ids_contain_month(self, mailer_ctx):
        results = MailerInsights().run(mailer_ctx)
        ids = {r.slide_id for r in results}
        assert "A12.Apr24.Swipes" in ids
        assert "A12.Apr24.Spend" in ids
        assert "A12.May24.Swipes" in ids
        assert "A12.May24.Spend" in ids

    def test_all_success(self, mailer_ctx):
        results = MailerInsights().run(mailer_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, mailer_ctx):
        results = MailerInsights().run(mailer_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_stores_per_month_results(self, mailer_ctx):
        MailerInsights().run(mailer_ctx)
        assert "a12_apr24" in mailer_ctx.results
        assert mailer_ctx.results["a12_apr24"]["nu_resp"] == 8


# ---------------------------------------------------------------------------
# MailerResponse (A13 + A14)
# ---------------------------------------------------------------------------


class TestMailerResponse:
    """MailerResponse.run() produces summaries, trends, and age chart."""

    def test_run_returns_results(self, mailer_ctx):
        results = MailerResponse().run(mailer_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, mailer_ctx):
        results = MailerResponse().run(mailer_ctx)
        ids = {r.slide_id for r in results}
        # Per-month summaries
        assert "A13.Apr24" in ids
        assert "A13.May24" in ids
        # Aggregate
        assert "A13.Agg" in ids
        # Trends (2+ months)
        assert "A13.5" in ids
        assert "A13.6" in ids
        # Account age
        assert "A14.2" in ids

    def test_all_success(self, mailer_ctx):
        results = MailerResponse().run(mailer_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_monthly_charts_generated(self, mailer_ctx):
        results = MailerResponse().run(mailer_ctx)
        monthly = [r for r in results if r.slide_id.startswith("A13.") and "Apr" in r.slide_id]
        assert len(monthly) == 1
        assert monthly[0].chart_path is not None

    def test_stores_monthly_summaries(self, mailer_ctx):
        MailerResponse().run(mailer_ctx)
        ms = mailer_ctx.results.get("monthly_summaries", {})
        assert "Apr24" in ms
        assert "May24" in ms

    def test_stores_rate_trend(self, mailer_ctx):
        MailerResponse().run(mailer_ctx)
        assert "rate_trend" in mailer_ctx.results

    def test_excel_data_on_monthly(self, mailer_ctx):
        results = MailerResponse().run(mailer_ctx)
        monthly = [r for r in results if r.slide_id == "A13.Apr24"][0]
        assert monthly.excel_data is not None
        assert "Response" in monthly.excel_data


# ---------------------------------------------------------------------------
# MailerImpact (A15)
# ---------------------------------------------------------------------------


class TestMailerImpact:
    """MailerImpact.run() produces market reach, spend share, revenue, delta."""

    def test_run_returns_results(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_slide_ids(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        ids = {r.slide_id for r in results}
        assert "A15.1" in ids
        assert "A15.2" in ids
        assert "A15.3" in ids
        assert "A15.4" in ids

    def test_a15_1_success(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        a15_1 = [r for r in results if r.slide_id == "A15.1"][0]
        assert a15_1.success, f"A15.1 failed: {a15_1.error}"

    def test_a15_2_success(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        a15_2 = [r for r in results if r.slide_id == "A15.2"][0]
        assert a15_2.success, f"A15.2 failed: {a15_2.error}"

    def test_a15_3_success(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        a15_3 = [r for r in results if r.slide_id == "A15.3"][0]
        assert a15_3.success, f"A15.3 failed: {a15_3.error}"

    def test_a15_4_success(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        a15_4 = [r for r in results if r.slide_id == "A15.4"][0]
        assert a15_4.success, f"A15.4 failed: {a15_4.error}"

    def test_charts_generated(self, mailer_ctx):
        results = MailerImpact().run(mailer_ctx)
        successful = [r for r in results if r.success]
        for r in successful:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_stores_market_reach(self, mailer_ctx):
        MailerImpact().run(mailer_ctx)
        mr = mailer_ctx.results.get("market_reach", {})
        assert mr["n_eligible"] > 0
        assert mr["n_responders"] > 0

    def test_stores_revenue_attribution(self, mailer_ctx):
        MailerImpact().run(mailer_ctx)
        ra = mailer_ctx.results.get("revenue_attribution", {})
        assert "resp_ic" in ra
        assert "incremental_total" in ra

    def test_no_ic_rate_skips_a15_3(self, mailer_ctx):
        mailer_ctx.client.ic_rate = 0.0
        results = MailerImpact().run(mailer_ctx)
        a15_3 = [r for r in results if r.slide_id == "A15.3"][0]
        assert not a15_3.success


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestMailerEdgeCases:
    """Edge case handling across mailer modules."""

    def test_no_mailer_columns(self, mailer_ctx):
        """Remove all mail columns -> graceful failure."""
        cols_to_drop = [c for c in mailer_ctx.data.columns if "Mail" in c or "Resp" in c]
        mailer_ctx.data = mailer_ctx.data.drop(columns=cols_to_drop)
        # Clear cached pairs
        mailer_ctx.results.pop("_mailer_pairs", None)

        results = MailerInsights().run(mailer_ctx)
        assert len(results) == 1
        assert not results[0].success

    def test_no_eligible_debit(self, mailer_ctx):
        """No eligible_with_debit -> A15.1 fails gracefully."""
        mailer_ctx.subsets.eligible_with_debit = None
        results = MailerImpact().run(mailer_ctx)
        a15_1 = [r for r in results if r.slide_id == "A15.1"][0]
        assert not a15_1.success
