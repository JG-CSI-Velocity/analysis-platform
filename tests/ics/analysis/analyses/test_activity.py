"""Tests for analyses/activity.py -- ax22 through ax26."""

from ics_toolkit.analysis.analyses.activity import (
    analyze_activity_by_balance,
    analyze_activity_by_branch,
    analyze_activity_by_debit_source,
    analyze_activity_summary,
    analyze_monthly_trends,
)
from ics_toolkit.analysis.analyses.base import AnalysisResult


class TestAnalyzeActivitySummary:
    """ax22: L12M Activity KPIs."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_metric_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_expected_kpi_metrics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = set(result.df["Metric"].values)
        assert "Total Accounts" in metrics
        assert "Active Accounts" in metrics
        assert "% Active" in metrics
        assert "Total Swipes" in metrics
        assert "Total Spend" in metrics
        assert "Avg Swipes per Account" in metrics
        assert "Avg Spend per Account" in metrics
        assert "Avg Swipes per Active Account" in metrics
        assert "Avg Spend per Active Account" in metrics
        assert "Avg Spend per Swipe" in metrics
        assert "Avg Current Balance (All)" in metrics
        assert "Avg Current Balance (Active)" in metrics

    def test_total_accounts_matches_input(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        total_row = result.df[result.df["Metric"] == "Total Accounts"]
        assert total_row["Value"].iloc[0] == len(ics_stat_o_debit)


class TestAnalyzeActivityByDebitSource:
    """ax23: Activity by Debit+Source."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_debit_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_debit_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Source", "Count", "Active Count", "Activation Rate", "Avg Swipes", "Avg Spend"}
        assert expected.issubset(set(result.df.columns))

    def test_source_values_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_debit_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        # Should have at least one source + Total row
        assert len(result.df) >= 2


class TestAnalyzeActivityByBalance:
    """ax24: Activity by Balance Tier."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Balance Tier", "Count", "Active Count", "Activation Rate", "Avg Swipes"}
        assert expected.issubset(set(result.df.columns))

    def test_balance_tiers_populated(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) > 0


class TestAnalyzeActivityByBranch:
    """ax25: Activity by Branch."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Branch", "Count", "Active Count", "Activation %", "Avg Swipes", "Avg Spend"}
        assert expected.issubset(set(result.df.columns))

    def test_branches_from_data(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        # Should have branch rows + Total row
        assert len(result.df) >= 2


class TestAnalyzeMonthlyTrends:
    """ax26: Monthly Trends."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Month", "Total Swipes", "Total Spend", "Active Accounts"}
        assert expected.issubset(set(result.df.columns))

    def test_has_12_months(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 12

    def test_months_match_settings(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        months = list(result.df["Month"])
        assert months == sample_settings.last_12_months

    def test_swipes_are_non_negative(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert (result.df["Total Swipes"] >= 0).all()
        assert (result.df["Active Accounts"] >= 0).all()
