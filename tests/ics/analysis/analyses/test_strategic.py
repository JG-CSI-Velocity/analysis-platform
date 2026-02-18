"""Tests for analyses/strategic.py -- Activation Funnel and Revenue Impact."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.strategic import (
    analyze_activation_funnel,
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

    def test_has_five_stages(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 5
        assert list(result.df["Stage"]) == [
            "Total Accounts",
            "ICS Accounts",
            "Stat Code O",
            "With Debit Card",
            "Active in L12M",
        ]

    def test_columns(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert list(result.df.columns) == ["Stage", "Count", "% of Total", "Drop-off %"]

    def test_first_stage_is_total(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_funnel(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df.iloc[0]["Count"] == len(sample_df)
        assert result.df.iloc[0]["% of Total"] == 100.0

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
