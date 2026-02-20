"""Tests for R08: Overview KPIs analysis."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.overview import analyze_overview


class TestAnalyzeOverview:
    """Tests for analyze_overview."""

    def test_returns_analysis_result(self, referral_context):
        result = analyze_overview(referral_context)
        assert isinstance(result, AnalysisResult)
        assert result.name == "Overview KPIs"
        assert result.sheet_name == "R08_Overview"

    def test_output_has_metric_value_columns(self, referral_context):
        result = analyze_overview(referral_context)
        assert list(result.df.columns) == ["Metric", "Value"]

    def test_contains_core_kpis(self, referral_context):
        result = analyze_overview(referral_context)
        metrics = set(result.df["Metric"].values)
        assert "Total Referrals" in metrics
        assert "Unique Referrers" in metrics
        assert "Unique New Accounts" in metrics

    def test_contains_referrer_behavior_kpis(self, referral_context):
        result = analyze_overview(referral_context)
        metrics = set(result.df["Metric"].values)
        assert "Repeat Referrer %" in metrics
        assert "Avg Referrals per Referrer" in metrics
        assert "Top Referrer Score" in metrics

    def test_total_referrals_matches_df_length(self, referral_context):
        result = analyze_overview(referral_context)
        total_row = result.df[result.df["Metric"] == "Total Referrals"]
        assert total_row["Value"].values[0] == len(referral_context.df)

    def test_unique_accounts_matches_nunique(self, referral_context):
        result = analyze_overview(referral_context)
        row = result.df[result.df["Metric"] == "Unique New Accounts"]
        expected = referral_context.df["MRDB Account Hash"].nunique()
        assert row["Value"].values[0] == expected

    def test_accepts_prior_results(self, referral_context):
        prior = [
            AnalysisResult.from_df("dummy", "dummy", pd.DataFrame()),
        ]
        result = analyze_overview(referral_context, prior_results=prior)
        assert isinstance(result, AnalysisResult)

    def test_empty_metrics_still_produces_kpis(self, empty_context):
        result = analyze_overview(empty_context)
        assert isinstance(result, AnalysisResult)
        metrics = set(result.df["Metric"].values)
        assert "Total Referrals" in metrics

    def test_empty_metrics_defaults_to_zero(self, empty_context):
        result = analyze_overview(empty_context)
        row = result.df[result.df["Metric"] == "Repeat Referrer %"]
        assert row["Value"].values[0] == 0.0
