"""Tests for R01: Top Referrers analysis."""

from __future__ import annotations

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.top_referrers import analyze_top_referrers


class TestAnalyzeTopReferrers:
    """Tests for analyze_top_referrers."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_top_referrers(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Top Referrers"
        assert result.sheet_name == "R01_Top_Referrers"

    def test_excludes_single_referral_referrers(self, referral_context):
        result = analyze_top_referrers(referral_context)
        if not result.df.empty:
            assert (result.df["Total Referrals"] > 1).all()

    def test_sorted_by_influence_score_descending(self, referral_context):
        result = analyze_top_referrers(referral_context)
        if len(result.df) > 1:
            scores = result.df["Influence Score"].values
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_respects_top_n_limit(self, referral_context):
        result = analyze_top_referrers(referral_context)
        assert len(result.df) <= referral_context.settings.top_n_referrers

    def test_output_columns(self, referral_context):
        result = analyze_top_referrers(referral_context)
        if not result.df.empty:
            assert "Referrer" in result.df.columns
            assert "Influence Score" in result.df.columns
            assert "Total Referrals" in result.df.columns

    def test_empty_metrics_returns_empty(self, empty_context):
        result = analyze_top_referrers(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty

    def test_index_is_reset(self, referral_context):
        result = analyze_top_referrers(referral_context)
        if not result.df.empty:
            assert list(result.df.index) == list(range(len(result.df)))
