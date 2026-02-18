"""Tests for analyses/performance.py -- Days to First Use, Branch Performance Index."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.performance import (
    analyze_branch_performance_index,
    analyze_days_to_first_use,
)


class TestAnalyzeDaysToFirstUse:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_days_to_first_use(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Days to First Use"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_days_to_first_use(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert list(result.df.columns) == ["Days Bucket", "Count", "% of Total"]

    def test_has_six_buckets(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_days_to_first_use(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 6
        assert result.df.iloc[-1]["Days Bucket"] == "Never Used"

    def test_counts_sum_to_total(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_days_to_first_use(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert result.df["Count"].sum() == len(ics_stat_o_debit)

    def test_empty_debit(self, sample_df, ics_all, ics_stat_o, sample_settings):
        empty = pd.DataFrame(columns=sample_df.columns)
        result = analyze_days_to_first_use(sample_df, ics_all, ics_stat_o, empty, sample_settings)
        assert result.df.empty


class TestAnalyzeBranchPerformanceIndex:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_performance_index(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Branch Performance Index"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_performance_index(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {
            "Branch",
            "Accounts",
            "Activation Index",
            "Swipes Index",
            "Spend Index",
            "Balance Index",
            "Composite Score",
        }
        assert set(result.df.columns) == expected

    def test_composite_is_average_of_indices(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_performance_index(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            row = result.df.iloc[0]
            avg = round(
                (
                    row["Activation Index"]
                    + row["Swipes Index"]
                    + row["Spend Index"]
                    + row["Balance Index"]
                )
                / 4,
                1,
            )
            assert row["Composite Score"] == avg

    def test_sorted_by_composite_desc(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_performance_index(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        scores = list(result.df["Composite Score"])
        assert scores == sorted(scores, reverse=True)

    def test_empty_debit(self, sample_df, ics_all, ics_stat_o, sample_settings):
        empty = pd.DataFrame(columns=sample_df.columns)
        result = analyze_branch_performance_index(
            sample_df, ics_all, ics_stat_o, empty, sample_settings
        )
        assert result.df.empty
