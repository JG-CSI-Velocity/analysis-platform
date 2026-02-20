"""Tests for R07: Code Health Report analysis."""

from __future__ import annotations

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.code_health import analyze_code_health


class TestAnalyzeCodeHealth:
    """Tests for analyze_code_health."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_code_health(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Code Health Report"
        assert result.sheet_name == "R07_Code_Health"

    def test_output_columns(self, referral_context):
        result = analyze_code_health(referral_context)
        if not result.df.empty:
            expected = {"Channel", "Type", "Reliability", "Count", "% of Total"}
            assert expected.issubset(set(result.df.columns))

    def test_pct_of_total_sums_to_100(self, referral_context):
        result = analyze_code_health(referral_context)
        if not result.df.empty:
            total_pct = result.df["% of Total"].sum()
            assert abs(total_pct - 100.0) < 0.5

    def test_sorted_by_count_descending(self, referral_context):
        result = analyze_code_health(referral_context)
        if len(result.df) > 1:
            counts = result.df["Count"].values
            assert all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))

    def test_known_code_pct_column_present(self, referral_context):
        result = analyze_code_health(referral_context)
        if not result.df.empty:
            assert "Known Code %" in result.df.columns

    def test_known_code_pct_in_valid_range(self, referral_context):
        result = analyze_code_health(referral_context)
        if not result.df.empty:
            for val in result.df["Known Code %"]:
                assert 0 <= val <= 100

    def test_empty_data_returns_empty(self, empty_context):
        result = analyze_code_health(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty
