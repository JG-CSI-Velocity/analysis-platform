"""Tests for R04: One-time vs Repeat Referrers analysis."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.onetime_vs_repeat import analyze_onetime_vs_repeat


class TestAnalyzeOnetimeVsRepeat:
    """Tests for analyze_onetime_vs_repeat."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "One-time vs Repeat Referrers"
        assert result.sheet_name == "R04_Repeat"

    def test_has_expected_categories(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        categories = set(result.df["Category"].values)
        assert "Grand Total" in categories
        # Should have at least one of One-time or Repeat
        assert categories.intersection({"One-time", "Repeat"})

    def test_grand_total_row_sums_correctly(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        df = result.df
        grand = df[df["Category"] == "Grand Total"]
        detail = df[df["Category"] != "Grand Total"]
        assert grand["Count"].values[0] == detail["Count"].sum()

    def test_grand_total_pct_is_100(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        grand = result.df[result.df["Category"] == "Grand Total"]
        assert grand["% of Total"].values[0] == 100.0

    def test_output_columns(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        expected = {
            "Category",
            "Count",
            "% of Total",
            "Avg Unique Accounts",
            "Avg Influence Score",
            "Avg Active Days",
        }
        assert expected.issubset(set(result.df.columns))

    def test_float_columns_rounded(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        for col in ["Avg Unique Accounts", "Avg Influence Score", "Avg Active Days"]:
            if col in result.df.columns:
                for val in result.df[col]:
                    if pd.notna(val):
                        assert val == round(val, 1)

    def test_empty_metrics_returns_empty(self, empty_context):
        result = analyze_onetime_vs_repeat(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty

    def test_pct_of_total_sums_to_100(self, referral_context):
        result = analyze_onetime_vs_repeat(referral_context)
        detail = result.df[result.df["Category"] != "Grand Total"]
        total_pct = detail["% of Total"].sum()
        assert abs(total_pct - 100.0) < 0.1
