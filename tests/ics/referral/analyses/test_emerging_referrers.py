"""Tests for R02: Emerging Referrers analysis."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.emerging_referrers import analyze_emerging_referrers


class TestAnalyzeEmergingReferrers:
    """Tests for analyze_emerging_referrers."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_emerging_referrers(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Emerging Referrers"
        assert result.sheet_name == "R02_Emerging"

    def test_only_recent_referrers(self, referral_context):
        result = analyze_emerging_referrers(referral_context)
        if not result.df.empty:
            max_date = referral_context.df["Issue Date"].max()
            lookback = referral_context.settings.emerging_lookback_days
            cutoff = max_date - pd.Timedelta(days=lookback)
            assert (result.df["First Referral"] >= cutoff).all()

    def test_meets_burst_minimum(self, referral_context):
        result = analyze_emerging_referrers(referral_context)
        if not result.df.empty:
            min_burst = referral_context.settings.emerging_min_burst_count
            assert (result.df["Burst Count"] >= min_burst).all()

    def test_sorted_by_influence_score(self, referral_context):
        result = analyze_emerging_referrers(referral_context)
        if len(result.df) > 1:
            scores = result.df["Influence Score"].values
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_output_columns(self, referral_context):
        result = analyze_emerging_referrers(referral_context)
        if not result.df.empty:
            assert "Referrer" in result.df.columns
            assert "Influence Score" in result.df.columns
            assert "Burst Count" in result.df.columns

    def test_empty_metrics_returns_empty(self, empty_context):
        result = analyze_emerging_referrers(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty

    def test_all_nat_dates_returns_empty(self, referral_context):
        """When all Issue Dates are NaT, should return empty."""
        referral_context.df["Issue Date"] = pd.NaT
        result = analyze_emerging_referrers(referral_context)
        assert result.df.empty
