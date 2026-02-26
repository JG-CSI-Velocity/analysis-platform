"""Tests for the consultant-grade chart system."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import (
    ACCENT,
    CORAL,
    GRAY_BASE,
    NAVY,
    add_source_footer,
    set_insight_title,
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
    return AnalysisResult.from_df(
        "top_merchants_by_spend",
        "Top Merchants by Spend",
        df,
        sheet_name="M1 Top Spend",
    )


@pytest.fixture()
def empty_result() -> AnalysisResult:
    return AnalysisResult.from_df(
        "top_merchants_by_spend",
        "Top Merchants by Spend",
        pd.DataFrame(),
        sheet_name="M1 Top Spend",
    )


# -- Theme tests ---------------------------------------------------------------


class TestTheme:
    def test_theme_colors(self):
        assert ACCENT == "#005EB8"
        assert GRAY_BASE == "#C4C4C4"
        assert CORAL == "#E4573D"
        assert NAVY == "#051C2C"


# -- Insight title tests -------------------------------------------------------


class TestInsightTitle:
    def test_basic_title(self):
        fig, ax = plt.subplots()
        try:
            set_insight_title(ax, "Top 5 capture 62% of spend")
            assert ax.get_title(loc="left") == "Top 5 capture 62% of spend"
        finally:
            plt.close(fig)

    def test_title_with_subtitle(self):
        fig, ax = plt.subplots()
        try:
            set_insight_title(ax, "Main Title", "Some context")
            assert ax.get_title(loc="left") == "Main Title"
            texts = [t.get_text() for t in ax.texts]
            assert "Some context" in texts
        finally:
            plt.close(fig)

    def test_title_color(self):
        fig, ax = plt.subplots()
        try:
            set_insight_title(ax, "Test")
            assert ax.get_title(loc="left") == "Test"
        finally:
            plt.close(fig)


# -- Source footer tests -------------------------------------------------------


class TestSourceFooter:
    def test_adds_text(self):
        fig, ax = plt.subplots()
        try:
            ax.plot([1, 2], [3, 4])
            add_source_footer(fig, "Test CU", "2025-07 to 2025-12")
            texts = [t.get_text() for t in fig.texts]
            assert any("Test CU" in t for t in texts)
            assert any("2025-07 to 2025-12" in t for t in texts)
        finally:
            plt.close(fig)

    def test_no_text_when_empty(self):
        fig, ax = plt.subplots()
        try:
            ax.plot([1, 2], [3, 4])
            add_source_footer(fig)
            assert len(fig.texts) == 0
        finally:
            plt.close(fig)

    def test_partial_footer(self):
        fig, ax = plt.subplots()
        try:
            ax.plot([1], [1])
            add_source_footer(fig, client_name="Test CU")
            texts = [t.get_text() for t in fig.texts]
            assert any("Test CU" in t for t in texts)
        finally:
            plt.close(fig)


# -- Lollipop chart tests ------------------------------------------------------


class TestLollipopChart:
    def test_returns_figure(self, spend_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(spend_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_has_artists(self, spend_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(spend_result, chart_config)
        ax = fig.get_axes()[0]
        # Lollipop chart should have line collections and scatter points
        assert len(ax.collections) > 0 or len(ax.lines) > 0
        plt.close(fig)

    def test_empty_result_returns_empty_fig(self, empty_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(empty_result, chart_config)
        assert len(fig.get_axes()) == 0
        plt.close(fig)

    def test_business_chart_returns_figure(self, spend_result, chart_config):
        from txn_analysis.charts.business import chart_business_top_by_spend

        fig = chart_business_top_by_spend(spend_result, chart_config)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_personal_chart_returns_figure(self, spend_result, chart_config):
        from txn_analysis.charts.personal import chart_personal_top_by_spend

        fig = chart_personal_top_by_spend(spend_result, chart_config)
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_insight_title_on_spend(self, spend_result, chart_config):
        from txn_analysis.charts.overall import chart_top_by_spend

        fig = chart_top_by_spend(spend_result, chart_config)
        ax = fig.get_axes()[0]
        title_text = ax.get_title(loc="left")
        assert title_text  # Should have a non-empty title
        plt.close(fig)


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
        return AnalysisResult.from_df("monthly_rank_tracking", "Rank", df, sheet_name="M5A")

    @pytest.fixture()
    def growth_result(self):
        df = pd.DataFrame(
            {
                "merchant_consolidated": [f"Merch {i}" for i in range(6)],
                "spend_change_pct": [50.0, 30.0, 10.0, -5.0, -20.0, -40.0],
            }
        )
        return AnalysisResult.from_df("growth_leaders_decliners", "Growth", df, sheet_name="M5B")

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
        return AnalysisResult.from_df("new_vs_declining_merchants", "Cohort", df, sheet_name="M5D")

    def test_rank_trajectory_fig(self, rank_result, chart_config):
        from txn_analysis.charts.trends import chart_rank_trajectory

        fig = chart_rank_trajectory(rank_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_rank_trajectory_has_lines(self, rank_result, chart_config):
        from txn_analysis.charts.trends import chart_rank_trajectory

        fig = chart_rank_trajectory(rank_result, chart_config)
        ax = fig.get_axes()[0]
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_growth_leaders_fig(self, growth_result, chart_config):
        from txn_analysis.charts.trends import chart_growth_leaders

        fig = chart_growth_leaders(growth_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_cohort_summary_fig(self, cohort_result, chart_config):
        from txn_analysis.charts.trends import chart_cohort_summary

        fig = chart_cohort_summary(cohort_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_empty_rank_returns_empty(self, chart_config):
        from txn_analysis.charts.trends import chart_rank_trajectory

        empty = AnalysisResult.from_df("x", "x", pd.DataFrame(), sheet_name="x")
        fig = chart_rank_trajectory(empty, chart_config)
        assert len(fig.get_axes()) == 0
        plt.close(fig)


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
        return AnalysisResult.from_df("competitor_threat_assessment", "Threat", df, sheet_name="M6")

    def test_threat_scatter_fig(self, threat_result, chart_config):
        from txn_analysis.charts.competitor import chart_threat_scatter

        fig = chart_threat_scatter(threat_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_threat_scatter_has_quadrant_labels(self, threat_result, chart_config):
        from txn_analysis.charts.competitor import chart_threat_scatter

        fig = chart_threat_scatter(threat_result, chart_config)
        ax = fig.get_axes()[0]
        text_labels = [t.get_text() for t in ax.texts]
        assert "High Threat" in text_labels
        assert "Monitor" in text_labels
        plt.close(fig)

    def test_empty_threat_returns_empty(self, chart_config):
        from txn_analysis.charts.competitor import chart_threat_scatter

        empty = AnalysisResult.from_df("x", "x", pd.DataFrame(), sheet_name="x")
        fig = chart_threat_scatter(empty, chart_config)
        assert len(fig.get_axes()) == 0
        plt.close(fig)


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
        return AnalysisResult.from_df("portfolio_scorecard", "Scorecard", df, sheet_name="M9")

    def test_returns_figure(self, scorecard_result, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        fig = chart_scorecard_bullets(scorecard_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_has_3_kpi_axes(self, scorecard_result, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        fig = chart_scorecard_bullets(scorecard_result, chart_config)
        # 3 KPIs with benchmarks -> 3 subplots
        assert len(fig.get_axes()) == 3
        plt.close(fig)

    def test_empty_returns_empty(self, chart_config):
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        empty = AnalysisResult.from_df("x", "x", pd.DataFrame(), sheet_name="x")
        fig = chart_scorecard_bullets(empty, chart_config)
        assert len(fig.get_axes()) == 0
        plt.close(fig)

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
        result = AnalysisResult.from_df("x", "x", df, sheet_name="x")
        fig = chart_scorecard_bullets(result, chart_config)
        assert len(fig.get_axes()) == 0
        plt.close(fig)


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
        return AnalysisResult.from_df("mcc_by_accounts", "MCC", df, sheet_name="M2")

    def test_mcc_comparison_fig(self, mcc_result, chart_config):
        from txn_analysis.charts.mcc import chart_mcc_comparison

        fig = chart_mcc_comparison(mcc_result, mcc_result, mcc_result, chart_config)
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) == 3  # one subplot per metric
        plt.close(fig)


# -- Chart registry + create_charts tests -------------------------------------


class TestCreateCharts:
    def test_create_charts_returns_dict(self, spend_result, chart_config):
        from txn_analysis.charts import create_charts

        charts = create_charts([spend_result], chart_config)
        assert isinstance(charts, dict)
        assert "top_merchants_by_spend" in charts
        for fig in charts.values():
            plt.close(fig)

    def test_source_footer_applied(self, spend_result, chart_config):
        from txn_analysis.charts import create_charts

        charts = create_charts(
            [spend_result],
            chart_config,
            client_name="Test CU",
            date_range="2025-07 to 2025-12",
        )
        fig = charts["top_merchants_by_spend"]
        footer_texts = [t.get_text() for t in fig.texts]
        assert any("Test CU" in t for t in footer_texts)
        for fig in charts.values():
            plt.close(fig)

    def test_empty_results_produce_no_charts(self, chart_config):
        from txn_analysis.charts import create_charts

        empty = AnalysisResult.from_df(
            "top_merchants_by_spend", "x", pd.DataFrame(), sheet_name="x"
        )
        charts = create_charts([empty], chart_config)
        assert len(charts) == 0
