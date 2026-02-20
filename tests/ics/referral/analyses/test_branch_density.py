"""Tests for R06: Branch Influence Density analysis."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.branch_density import analyze_branch_density


class TestAnalyzeBranchDensity:
    """Tests for analyze_branch_density."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_branch_density(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Branch Influence Density"
        assert result.sheet_name == "R06_Branch"

    def test_excludes_unknown_branches(self, referral_context):
        result = analyze_branch_density(referral_context)
        if not result.df.empty:
            assert "UNKNOWN" not in result.df["Branch"].values

    def test_sorted_by_avg_influence_score(self, referral_context):
        result = analyze_branch_density(referral_context)
        if len(result.df) > 1:
            scores = result.df["Avg Influence Score"].values
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_output_columns(self, referral_context):
        result = analyze_branch_density(referral_context)
        if not result.df.empty:
            expected = {"Branch", "Total Referrals", "Unique Referrers", "Avg Influence Score"}
            assert expected.issubset(set(result.df.columns))

    def test_avg_influence_score_rounded(self, referral_context):
        result = analyze_branch_density(referral_context)
        if not result.df.empty:
            for val in result.df["Avg Influence Score"]:
                if pd.notna(val):
                    assert val == round(val, 1)

    def test_has_top_referrer_per_branch(self, referral_context):
        result = analyze_branch_density(referral_context)
        if not result.df.empty:
            assert "Top Referrer" in result.df.columns

    def test_empty_data_returns_empty(self, empty_context):
        result = analyze_branch_density(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty

    def test_index_is_reset(self, referral_context):
        result = analyze_branch_density(referral_context)
        if not result.df.empty:
            assert list(result.df.index) == list(range(len(result.df)))
