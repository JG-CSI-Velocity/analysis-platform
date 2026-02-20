"""Tests for analyses/portfolio.py -- Engagement Decay, Net Growth, Concentration, Closures."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.portfolio import (
    analyze_closure_by_account_age,
    analyze_closure_by_branch,
    analyze_closure_by_source,
    analyze_closure_rate_trend,
    analyze_concentration,
    analyze_engagement_decay,
    analyze_net_growth_by_source,
    analyze_net_portfolio_growth,
)


class TestAnalyzeEngagementDecay:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_engagement_decay(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Engagement Decay"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_engagement_decay(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Decay Category" in result.df.columns
        assert "Count" in result.df.columns
        assert "% of Total" in result.df.columns

    def test_categories_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_engagement_decay(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        cats = set(result.df["Decay Category"].values)
        assert cats.issubset({"Active", "Decayed", "Late Activator", "Never Active"})

    def test_insufficient_months(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        sample_settings.last_12_months = ["Jan26"]
        result = analyze_engagement_decay(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df["Metric"].iloc[0] == "Status"


class TestAnalyzeNetPortfolioGrowth:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_net_portfolio_growth(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Net Portfolio Growth"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_net_portfolio_growth(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Month", "Opens", "Closes", "Net", "Cumulative"}
        assert set(result.df.columns) == expected

    def test_cumulative_sums_correctly(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_net_portfolio_growth(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert result.df["Cumulative"].iloc[-1] == result.df["Net"].sum()

    def test_empty_without_date_opened(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        no_dates = ics_all.drop(columns=["Date Opened"])
        result = analyze_net_portfolio_growth(
            sample_df, no_dates, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df.empty


class TestAnalyzeConcentration:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_concentration(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Spend Concentration"

    def test_has_three_percentiles(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_concentration(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 3
        assert list(result.df["Percentile"]) == ["Top 10%", "Top 20%", "Top 50%"]

    def test_spend_share_increases(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_concentration(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        shares = list(result.df["Spend Share %"])
        for i in range(1, len(shares)):
            assert shares[i] >= shares[i - 1]

    def test_empty_debit(self, sample_df, ics_all, ics_stat_o, sample_settings):
        empty = pd.DataFrame(columns=sample_df.columns)
        result = analyze_concentration(sample_df, ics_all, ics_stat_o, empty, sample_settings)
        assert result.df.empty


class TestAnalyzeClosureBySource:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Closure by Source"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Source", "Closed Count", "% of Closures"}
        assert expected.issubset(set(result.df.columns))

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_closure_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert "Total" in result.df["Source"].values


class TestAnalyzeClosureByBranch:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Closure by Branch"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Branch", "Closed Count", "% of Closures"}
        assert expected.issubset(set(result.df.columns))

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_closure_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert "Total" in result.df["Branch"].values


class TestAnalyzeClosureByAccountAge:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_account_age(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Closure by Account Age"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_account_age(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Age Range", "Closed Count", "% of Closures"}
        assert expected.issubset(set(result.df.columns))

    def test_non_negative_counts(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_by_account_age(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert (result.df["Closed Count"] >= 0).all()


class TestAnalyzeNetGrowthBySource:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_net_growth_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Net Growth by Source"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_net_growth_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Source", "Opens", "Closes", "Net"}
        assert expected.issubset(set(result.df.columns))

    def test_net_equals_opens_minus_closes(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_net_growth_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        data = result.df[result.df["Source"] != "Total"]
        if not data.empty:
            assert (data["Net"] == data["Opens"] - data["Closes"]).all()

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_net_growth_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert "Total" in result.df["Source"].values


class TestAnalyzeClosureRateTrend:
    """ax82: Monthly closure rate trend."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_rate_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Closure Rate Trend"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_rate_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            expected = {"Month", "Closures", "Portfolio Size", "Closure Rate %"}
            assert expected.issubset(set(result.df.columns))

    def test_closure_rate_between_0_and_100(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closure_rate_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            rates = pd.to_numeric(result.df["Closure Rate %"], errors="coerce").dropna()
            assert (rates >= 0).all()
            assert (rates <= 100).all()

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_closure_rate_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "82_Closure_Rate"
