"""Tests for analyses/demographics.py -- ax14 through ax21."""

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.demographics import (
    analyze_age_comparison,
    analyze_age_dist,
    analyze_age_vs_balance,
    analyze_balance_tier_detail,
    analyze_balance_tiers,
    analyze_balance_trajectory,
    analyze_closures,
    analyze_open_vs_close,
    analyze_stat_open_close,
)


class TestAnalyzeAgeComparison:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_age_comparison(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_age_comparison(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Age Range" in result.df.columns
        assert "Count" in result.df.columns
        assert "% of Count" in result.df.columns

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_age_comparison(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "14_Age_Comparison"


class TestAnalyzeClosures:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closures(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closures(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert "Month Closed" in result.df.columns
        assert "Count" in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_closures(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert "Total" in result.df["Month Closed"].values


class TestAnalyzeOpenVsClose:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_open_vs_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_metric_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_open_vs_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_contains_expected_metrics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_open_vs_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = result.df["Metric"].tolist()
        assert "Total ICS Accounts" in metrics
        assert "Open (Stat Code O)" in metrics
        assert "Closed (Stat Code C)" in metrics

    def test_counts_add_up(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_open_vs_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        vals = dict(zip(result.df["Metric"], result.df["Value"]))
        assert (
            vals["Open (Stat Code O)"] + vals["Closed (Stat Code C)"] == vals["Total ICS Accounts"]
        )


class TestAnalyzeBalanceTiers:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_tiers(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_tiers(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Balance Tier" in result.df.columns
        assert "Count" in result.df.columns
        assert "% of Count" in result.df.columns

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_balance_tiers(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "17_Balance_Tiers"


class TestAnalyzeStatOpenClose:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_stat_open_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_stat_open_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Stat Code" in result.df.columns
        assert "Count" in result.df.columns
        assert "Avg Curr Bal" in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_stat_open_close(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Stat Code"].values


class TestAnalyzeAgeVsBalance:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_age_vs_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_age_vs_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Age Range" in result.df.columns
        assert "Count" in result.df.columns
        assert "Avg Curr Bal" in result.df.columns

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_age_vs_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "19_Age_vs_Balance"


class TestAnalyzeBalanceTierDetail:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_tier_detail(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_tier_detail(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Balance Tier" in result.df.columns
        assert "Count" in result.df.columns
        assert "Avg Swipes" in result.df.columns
        assert "Avg Spend" in result.df.columns

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_balance_tier_detail(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "20_Bal_Tier_Detail"


class TestAnalyzeAgeDist:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_age_dist(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_age_dist(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert "Age Range" in result.df.columns
        assert "Count" in result.df.columns
        assert "% of Count" in result.df.columns

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_age_dist(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert result.sheet_name == "21_Age_Dist"


class TestAnalyzeBalanceTrajectory:
    """ax83: Balance Trajectory by Branch."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_trajectory(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Balance Trajectory"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_trajectory(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Branch", "Avg Bal", "Curr Bal", "Change ($)", "Change (%)"}
        assert expected.issubset(set(result.df.columns))

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_balance_trajectory(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Branch"].values

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_balance_trajectory(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "83_Bal_Trajectory"
