"""Tests for R05: Staff Multipliers analysis."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.staff_multipliers import analyze_staff_multipliers


class TestAnalyzeStaffMultipliers:
    """Tests for analyze_staff_multipliers."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_staff_multipliers(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Staff Multipliers"
        assert result.sheet_name == "R05_Staff"

    def test_sorted_by_multiplier_score_descending(self, referral_context):
        result = analyze_staff_multipliers(referral_context)
        if len(result.df) > 1:
            scores = result.df["Multiplier Score"].values
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_output_columns(self, referral_context):
        result = analyze_staff_multipliers(referral_context)
        if not result.df.empty:
            assert "Staff" in result.df.columns
            assert "Multiplier Score" in result.df.columns

    def test_avg_referrer_score_rounded(self, referral_context):
        result = analyze_staff_multipliers(referral_context)
        if not result.df.empty and "Avg Referrer Score" in result.df.columns:
            for val in result.df["Avg Referrer Score"]:
                if pd.notna(val):
                    assert val == round(val, 1)

    def test_empty_metrics_returns_empty(self, empty_context):
        result = analyze_staff_multipliers(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty

    def test_index_is_reset(self, referral_context):
        result = analyze_staff_multipliers(referral_context)
        if not result.df.empty:
            assert list(result.df.index) == list(range(len(result.df)))
