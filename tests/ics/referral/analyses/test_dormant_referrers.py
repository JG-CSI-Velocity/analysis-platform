"""Tests for R03: Dormant High-Value Referrers analysis."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.dormant_referrers import analyze_dormant_referrers


class TestAnalyzeDormantReferrers:
    """Tests for analyze_dormant_referrers."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_dormant_referrers(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Dormant High-Value Referrers"
        assert result.sheet_name == "R03_Dormant"

    def test_dormant_means_last_referral_before_cutoff(self, referral_context):
        result = analyze_dormant_referrers(referral_context)
        if not result.df.empty:
            max_date = referral_context.df["Issue Date"].max()
            dormancy_days = referral_context.settings.dormancy_days
            cutoff = max_date - pd.Timedelta(days=dormancy_days)
            assert (result.df["Last Referral"] < cutoff).all()

    def test_days_dormant_is_positive(self, referral_context):
        result = analyze_dormant_referrers(referral_context)
        if not result.df.empty:
            assert (result.df["Days Dormant"] > 0).all()

    def test_sorted_by_historical_score(self, referral_context):
        result = analyze_dormant_referrers(referral_context)
        if len(result.df) > 1:
            scores = result.df["Historical Score"].values
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_output_columns(self, referral_context):
        result = analyze_dormant_referrers(referral_context)
        if not result.df.empty:
            expected = {
                "Referrer",
                "Historical Score",
                "Total Referrals",
                "Unique Accounts",
                "Last Referral",
                "Days Dormant",
            }
            assert expected.issubset(set(result.df.columns))

    def test_empty_metrics_returns_empty(self, empty_context):
        result = analyze_dormant_referrers(empty_context)
        assert isinstance(result, AnalysisResult)
        assert result.df.empty

    def test_all_nat_dates_returns_empty(self, referral_context):
        referral_context.df["Issue Date"] = pd.NaT
        result = analyze_dormant_referrers(referral_context)
        assert result.df.empty

    def test_no_dormant_referrers_returns_empty(self, referral_context):
        """When all referrers are recent, result should be empty."""
        # Set dormancy to a very large window so nobody qualifies
        referral_context.settings = referral_context.settings.model_copy(
            update={"dormancy_days": 9999}
        )
        result = analyze_dormant_referrers(referral_context)
        assert result.df.empty
