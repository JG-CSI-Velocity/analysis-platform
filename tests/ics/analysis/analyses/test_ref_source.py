"""Tests for analyses/ref_source.py -- ax73 through ax80."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.ref_source import (
    analyze_ref_activity,
    analyze_ref_activity_by_branch,
    analyze_ref_by_branch,
    analyze_ref_by_debit,
    analyze_ref_by_product,
    analyze_ref_by_year,
    analyze_ref_monthly_trends,
    analyze_ref_overview,
)


class TestAnalyzeRefOverview:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "73_REF_Overview"

    def test_has_metric_and_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_contains_expected_metrics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = result.df["Metric"].tolist()
        assert "Total REF Accounts" in metrics
        assert "% of All ICS" in metrics
        assert "Open Accounts" in metrics
        assert "Debit Card Count (Open)" in metrics

    def test_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.name == "REF Overview"


class TestAnalyzeRefByBranch:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for col in ["Branch", "Count", "% of REF", "Debit Count", "Debit %", "Avg Balance"]:
            assert col in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Branch"].values

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "74_REF_Branch"

    def test_empty_input(self, sample_settings):
        cols = ["ICS Account", "Stat Code", "Source", "Debit?", "Branch", "Curr Bal"]
        empty = pd.DataFrame(columns=cols)
        result = analyze_ref_by_branch(empty, empty, empty, empty, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty


class TestAnalyzeRefByDebit:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_debit(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_debit(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for col in ["Debit?", "Count", "%", "Avg Balance", "Total L12M Swipes"]:
            assert col in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_debit(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Debit?"].values

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_by_debit(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "75_REF_Debit"

    def test_empty_input(self, sample_settings):
        empty = pd.DataFrame(columns=["ICS Account", "Stat Code", "Source", "Debit?", "Curr Bal"])
        result = analyze_ref_by_debit(empty, empty, empty, empty, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty


class TestAnalyzeRefByProduct:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_product(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_product(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for col in ["Prod Code", "Count", "%", "Debit Count", "Debit %"]:
            assert col in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_product(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Prod Code"].values

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_by_product(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "76_REF_Product"


class TestAnalyzeRefByYear:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_year(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_year(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for col in ["Year Opened", "Count", "%", "Debit Count", "Debit %", "Avg Balance"]:
            assert col in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_by_year(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Year Opened"].values

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_by_year(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "77_REF_Year"

    def test_empty_input(self, sample_settings):
        cols = [
            "ICS Account",
            "Stat Code",
            "Source",
            "Debit?",
            "Prod Code",
            "Date Opened",
            "Curr Bal",
        ]
        empty = pd.DataFrame(columns=cols)
        result = analyze_ref_by_year(empty, empty, empty, empty, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty


class TestAnalyzeRefActivity:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_activity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_metric_and_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_activity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_contains_expected_metrics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_activity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = result.df["Metric"].tolist()
        assert "Total REF Debit Accounts" in metrics
        assert "Active Accounts (L12M)" in metrics
        assert "% Active" in metrics

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_activity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "78_REF_Activity"


class TestAnalyzeRefActivityByBranch:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for col in ["Branch", "Count", "Active Count", "Activation %", "Avg Swipes", "Avg Spend"]:
            assert col in result.df.columns

    def test_has_grand_total_row(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Branch"].values

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_activity_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "79_REF_Act_Branch"

    def test_empty_input(self, sample_settings):
        cols = ["ICS Account", "Stat Code", "Source", "Debit?", "Branch", "Curr Bal"]
        empty = pd.DataFrame(columns=cols)
        result = analyze_ref_activity_by_branch(empty, empty, empty, empty, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty


class TestAnalyzeRefMonthlyTrends:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for col in ["Month", "Total Swipes", "Total Spend", "Active Accounts"]:
            assert col in result.df.columns

    def test_has_12_rows(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 12

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_ref_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "80_REF_Monthly"

    def test_month_values_match_settings(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_ref_monthly_trends(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df["Month"].tolist() == sample_settings.last_12_months
