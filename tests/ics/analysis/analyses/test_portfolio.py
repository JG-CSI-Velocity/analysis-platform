"""Tests for analyses/portfolio.py -- Engagement Decay, Net Growth, Concentration."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.portfolio import (
    analyze_concentration,
    analyze_engagement_decay,
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
