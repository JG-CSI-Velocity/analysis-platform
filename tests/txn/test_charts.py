"""Tests for the consultant-grade chart system."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import (
    ACCENT,
    CORAL,
    GRAY_BASE,
    NAVY,
    add_source_footer,
    ensure_theme,
    insight_title,
)
from txn_analysis.settings import ChartConfig


@pytest.fixture()
def chart_config() -> ChartConfig:
    return ChartConfig()


@pytest.fixture()
def spend_result() -> AnalysisResult:
    """A minimal spend analysis result for chart tests."""
    df = pd.DataFrame(
        {
            "merchant_consolidated": [f"Merchant {i}" for i in range(10)],
            "total_amount": [10000 - i * 800 for i in range(10)],
            "transaction_count": [500 - i * 40 for i in range(10)],
            "unique_accounts": [200 - i * 15 for i in range(10)],
            "pct_of_total_amount": [20.0, 15.0, 12.0, 10.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0],
        }
    )
    return AnalysisResult(
        name="top_merchants_by_spend",
        title="Top Merchants by Spend",
        df=df,
        sheet_name="M1 Top Spend",
    )


@pytest.fixture()
def empty_result() -> AnalysisResult:
    return AnalysisResult(
        name="top_merchants_by_spend",
        title="Top Merchants by Spend",
        df=pd.DataFrame(),
        sheet_name="M1 Top Spend",
    )


# -- Theme tests ---------------------------------------------------------------


class TestTheme:
    def test_ensure_theme_registers(self):
        ensure_theme()
        import plotly.io as pio

        assert "consultant" in pio.templates

    def test_ensure_theme_idempotent(self):
        ensure_theme()
        ensure_theme()  # should not raise

    def test_theme_has_no_gridlines_on_x(self):
        ensure_theme()
        import plotly.io as pio

        tpl = pio.templates["consultant"]
        assert tpl.layout.xaxis.showgrid is False

    def test_theme_colors(self):
        assert ACCENT == "#005EB8"
        assert GRAY_BASE == "#C4C4C4"
        assert CORAL == "#E4573D"
        assert NAVY == "#051C2C"


# -- Insight title tests -------------------------------------------------------


class TestInsightTitle:
    def test_basic_title(self):
        result = insight_title("Top 5 capture 62% of spend")
        assert result["text"] == "Top 5 capture 62% of spend"
        assert "Georgia" in result["font"]["family"]

    def test_title_with_subtitle(self):
        result = insight_title("Main Title", "Some context")
        assert "Main Title" in result["text"]
        assert "Some context" in result["text"]
        assert "<br>" in result["text"]

    def test_title_color(self):
        result = insight_title("Test")
        assert result["font"]["color"] == NAVY


# -- Source footer tests -------------------------------------------------------


class TestSourceFooter:
    def test_adds_annotation(self):
        fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
        add_source_footer(fig, "Test CU", "2025-07 to 2025-12")
        annotations = fig.layout.annotations
        assert len(annotations) == 1
        assert "Test CU" in annotations[0].text
        assert "2025-07 to 2025-12" in annotations[0].text

    def test_no_annotation_when_empty(self):
        fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
        add_source_footer(fig)
        assert len(fig.layout.annotations) == 0

    def test_partial_footer(self):
        fig = go.Figure(go.Scatter(x=[1], y=[1]))
        add_source_footer(fig, client_name="Test CU")
        assert len(fig.layout.annotations) == 1
        assert "Test CU" in fig.layout.annotations[0].text


# -- Lollipop chart tests ------------------------------------------------------


class TestLollipopChart:
    def test_returns_figure(self, spend_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(spend_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_has_exactly_2_traces(self, spend_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(spend_result, chart_config)
        assert len(fig.data) == 2  # stems + dots

    def test_empty_result_returns_empty_fig(self, empty_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(empty_result, chart_config)
        assert len(fig.data) == 0

    def test_business_chart_returns_figure(self, spend_result, chart_config):
        from txn_analysis.charts.business import chart_business_top_by_spend

        fig = chart_business_top_by_spend(spend_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_personal_chart_returns_figure(self, spend_result, chart_config):
        from txn_analysis.charts.personal import chart_personal_top_by_spend

        fig = chart_personal_top_by_spend(spend_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_insight_title_on_spend(self, spend_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(spend_result, chart_config)
        title_text = fig.layout.title.text
        assert "capture" in title_text or "Top" in title_text


# -- Trend chart tests ---------------------------------------------------------


class TestTrendCharts:
    @pytest.fixture()
    def rank_result(self):
        df = pd.DataFrame(
            {
                "merchant_consolidated": [f"Merch {i}" for i in range(5)],
                "avg_rank": [1, 2, 3, 4, 5],
                "2025-07": [1, 2, 3, 4, 5],
                "2025-08": [1, 3, 2, 5, 4],
                "2025-09": [2, 1, 3, 4, 5],
            }
        )
        return AnalysisResult(name="monthly_rank_tracking", title="Rank", df=df, sheet_name="M5A")

    @pytest.fixture()
    def growth_result(self):
        df = pd.DataFrame(
            {
                "merchant_consolidated": [f"Merch {i}" for i in range(6)],
                "spend_change_pct": [50.0, 30.0, 10.0, -5.0, -20.0, -40.0],
            }
        )
        return AnalysisResult(
            name="growth_leaders_decliners", title="Growth", df=df, sheet_name="M5B"
        )

    @pytest.fixture()
    def cohort_result(self):
        df = pd.DataFrame(
            {
                "year_month": ["2025-07", "2025-08", "2025-09"],
                "new_merchants": [10, 8, 12],
                "lost_merchants": [3, 5, 2],
                "returning_merchants": [2, 4, 6],
            }
        )
        return AnalysisResult(
            name="new_vs_declining_merchants", title="Cohort", df=df, sheet_name="M5D"
        )

    def test_rank_trajectory_fig(self, rank_result, chart_config):
        from txn_analysis.charts.trends import chart_rank_trajectory

        fig = chart_rank_trajectory(rank_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_rank_trajectory_top3_colored(self, rank_result, chart_config):
        from txn_analysis.charts.trends import chart_rank_trajectory

        fig = chart_rank_trajectory(rank_result, chart_config)
        # Top 3 traces should have accent colors
        assert fig.data[0].line.color == ACCENT

    def test_growth_leaders_fig(self, growth_result, chart_config):
        from txn_analysis.charts.trends import chart_growth_leaders

        fig = chart_growth_leaders(growth_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_cohort_summary_fig(self, cohort_result, chart_config):
        from txn_analysis.charts.trends import chart_cohort_summary

        fig = chart_cohort_summary(cohort_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # new, lost, returning

    def test_empty_rank_returns_empty(self, chart_config):
        from txn_analysis.charts.trends import chart_rank_trajectory

        empty = AnalysisResult(name="x", title="x", df=pd.DataFrame(), sheet_name="x")
        fig = chart_rank_trajectory(empty, chart_config)
        assert len(fig.data) == 0


# -- Competitor chart tests ----------------------------------------------------


class TestCompetitorCharts:
    @pytest.fixture()
    def threat_result(self):
        df = pd.DataFrame(
            {
                "competitor": ["Venmo", "PayPal", "CashApp"],
                "penetration_pct": [25.0, 15.0, 10.0],
                "total_spend": [50000, 30000, 15000],
                "growth_rate": [10.0, -5.0, 20.0],
                "threat_score": [80, 60, 45],
            }
        )
        return AnalysisResult(
            name="competitor_threat_assessment", title="Threat", df=df, sheet_name="M6"
        )

    def test_threat_scatter_fig(self, threat_result, chart_config):
        from txn_analysis.charts.competitor import chart_threat_scatter

        fig = chart_threat_scatter(threat_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_threat_scatter_has_quadrant_annotations(self, threat_result, chart_config):
        from txn_analysis.charts.competitor import chart_threat_scatter

        fig = chart_threat_scatter(threat_result, chart_config)
        annotation_texts = [a.text for a in fig.layout.annotations]
        assert "High Threat" in annotation_texts
        assert "Monitor" in annotation_texts

    def test_empty_threat_returns_empty(self, chart_config):
        from txn_analysis.charts.competitor import chart_threat_scatter

        empty = AnalysisResult(name="x", title="x", df=pd.DataFrame(), sheet_name="x")
        fig = chart_threat_scatter(empty, chart_config)
        assert len(fig.data) == 0


# -- Scorecard bullet chart tests ---------------------------------------------


class TestScorecardBullets:
    @pytest.fixture()
    def scorecard_result(self):
        df = pd.DataFrame(
            {
                "metric": [
                    "Active Accounts",
                    "Avg Spend/Account/Month",
                    "Avg Txn/Account/Month",
                    "Average Ticket",
                ],
                "value": [500, 850.0, 22.5, 45.0],
                "benchmark": ["", 774.25, 20.2, 40.0],
                "status": ["", "Above", "Above", "Above"],
                "format": ["", "$", "", "$"],
            }
        )
        return AnalysisResult(name="portfolio_scorecard", title="Scorecard", df=df, sheet_name="M9")

    def test_returns_figure(self, scorecard_result, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        fig = chart_scorecard_bullets(scorecard_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_has_3_kpi_sections(self, scorecard_result, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        fig = chart_scorecard_bullets(scorecard_result, chart_config)
        # 3 KPIs * (3 bands + 1 actual bar + 1 benchmark marker) = 15 traces
        assert len(fig.data) >= 3

    def test_empty_returns_empty(self, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        empty = AnalysisResult(name="x", title="x", df=pd.DataFrame(), sheet_name="x")
        fig = chart_scorecard_bullets(empty, chart_config)
        assert len(fig.data) == 0

    def test_no_benchmarks_returns_empty(self, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        df = pd.DataFrame(
            {
                "metric": ["Active Accounts"],
                "value": [500],
                "benchmark": [""],
                "status": [""],
                "format": [""],
            }
        )
        result = AnalysisResult(name="x", title="x", df=df, sheet_name="x")
        fig = chart_scorecard_bullets(result, chart_config)
        assert len(fig.data) == 0


# -- MCC comparison chart tests ------------------------------------------------


class TestMCCChart:
    @pytest.fixture()
    def mcc_result(self):
        df = pd.DataFrame(
            {
                "mcc_description": ["Grocery", "Gas Stations", "Restaurants"],
                "unique_accounts": [100, 80, 60],
                "transaction_count": [500, 300, 200],
                "total_amount": [50000, 30000, 20000],
            }
        )
        return AnalysisResult(name="mcc_by_accounts", title="MCC", df=df, sheet_name="M2")

    def test_mcc_comparison_fig(self, mcc_result, chart_config):
        from txn_analysis.charts.mcc import chart_mcc_comparison

        fig = chart_mcc_comparison(mcc_result, mcc_result, mcc_result, chart_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # one bar per subplot


# -- Chart registry + create_charts tests -------------------------------------


class TestCreateCharts:
    def test_create_charts_returns_dict(self, spend_result, chart_config):
        from txn_analysis.charts import create_charts

        charts = create_charts([spend_result], chart_config)
        assert isinstance(charts, dict)
        assert "top_merchants_by_spend" in charts

    def test_source_footer_applied(self, spend_result, chart_config):
        from txn_analysis.charts import create_charts

        charts = create_charts(
            [spend_result],
            chart_config,
            client_name="Test CU",
            date_range="2025-07 to 2025-12",
        )
        fig = charts["top_merchants_by_spend"]
        annotation_texts = [a.text for a in fig.layout.annotations]
        assert any("Test CU" in t for t in annotation_texts)

    def test_empty_results_produce_no_charts(self, chart_config):
        from txn_analysis.charts import create_charts

        empty = AnalysisResult(
            name="top_merchants_by_spend", title="x", df=pd.DataFrame(), sheet_name="x"
        )
        charts = create_charts([empty], chart_config)
        assert len(charts) == 0
