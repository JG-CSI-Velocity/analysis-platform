"""Tests for analyses/strategic.py -- Funnel, Revenue Impact, Revenue by Branch/Source."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.strategic import (
    analyze_activation_funnel,
    analyze_dormant_high_balance,
    analyze_revenue_by_branch,
    analyze_revenue_by_source,
    analyze_revenue_impact,
)


class TestAnalyzeActivationFunnel:
    """Activation Funnel analysis."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Activation Funnel"

    def test_has_four_stages(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 4
        assert list(result.df["Stage"]) == [
            "ICS Accounts",
            "Stat Code O",
            "With Debit Card",
            "Active in L12M",
        ]

    def test_columns(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert list(result.df.columns) == ["Stage", "Count", "% of ICS", "Drop-off %"]

    def test_first_stage_is_ics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df.iloc[0]["Count"] == len(ics_all)
        assert result.df.iloc[0]["% of ICS"] == 100.0

    def test_first_dropoff_is_zero(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df.iloc[0]["Drop-off %"] == 0.0

    def test_counts_decrease_monotonically(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        counts = list(result.df["Count"])
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i - 1]


class TestAnalyzeRevenueImpact:
    """Revenue Impact analysis."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_impact(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Revenue Impact"

    def test_has_kpi_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_impact(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert list(result.df.columns) == ["Metric", "Value"]

    def test_has_five_metrics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_impact(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 5

    def test_interchange_is_positive(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_impact(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        mask = result.df["Metric"] == "Estimated Annual Interchange"
        interchange = result.df[mask]["Value"].iloc[0]
        assert interchange > 0

    def test_empty_debit(self, sample_df, ics_all, ics_stat_o, sample_settings):
        empty = pd.DataFrame(columns=sample_df.columns)
        result = analyze_revenue_impact(sample_df, ics_all, ics_stat_o, empty, sample_settings)
        assert isinstance(result, AnalysisResult)


class TestAnalyzeRevenueByBranch:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Revenue by Branch"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Branch", "Accounts", "Total L12M Spend", "Est. Interchange", "Avg Spend"}
        assert expected.issubset(set(result.df.columns))

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_revenue_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Branch"].values

    def test_interchange_is_positive(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        data = result.df[result.df["Branch"] != "Total"]
        assert (data["Est. Interchange"] >= 0).all()


class TestAnalyzeRevenueBySource:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Revenue by Source"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_revenue_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Source", "Accounts", "Total L12M Spend", "Est. Interchange", "Avg Spend"}
        assert expected.issubset(set(result.df.columns))

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_revenue_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Source"].values


class TestAnalyzeDormantHighBalance:
    """ax84: Dormant high-balance accounts."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_dormant_high_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Dormant High-Balance"

    def test_has_kpi_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_dormant_high_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert list(result.df.columns) == ["Metric", "Value"]

    def test_contains_expected_metrics(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_dormant_high_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = result.df["Metric"].tolist()
        assert "Total Debit Accounts" in metrics
        assert "Inactive Accounts" in metrics

    def test_sheet_name(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_dormant_high_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.sheet_name == "84_Dormant_HiBal"

    def test_empty_debit(self, sample_df, ics_all, ics_stat_o, sample_settings):
        empty = pd.DataFrame(columns=sample_df.columns)
        result = analyze_dormant_high_balance(
            sample_df, ics_all, ics_stat_o, empty, sample_settings
        )
        assert isinstance(result, AnalysisResult)
