"""Tests for influence scoring and staff multiplier computation."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.referral.code_decoder import decode_referral_codes
from ics_toolkit.referral.network import infer_networks
from ics_toolkit.referral.normalizer import normalize_entities
from ics_toolkit.referral.scoring import (
    _safe_minmax,
    compute_influence_scores,
    compute_referrer_metrics,
    compute_staff_multipliers,
)
from ics_toolkit.referral.temporal import add_temporal_signals
from ics_toolkit.settings import ReferralScoringWeights, ReferralSettings


@pytest.fixture
def settings():
    return ReferralSettings()


@pytest.fixture
def enriched_df(sample_referral_df, settings):
    """Full pipeline enrichment through layers 1-4."""
    df = normalize_entities(sample_referral_df, settings)
    df = decode_referral_codes(df, settings)
    df = add_temporal_signals(df, settings)
    df = infer_networks(df)
    return df


class TestSafeMinmax:
    def test_normalizes_to_01(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = _safe_minmax(s)
        assert result.min() == 0.0
        assert result.max() == 1.0

    def test_constant_series_returns_05(self):
        s = pd.Series([5, 5, 5])
        result = _safe_minmax(s)
        assert (result == 0.5).all()

    def test_single_value_returns_05(self):
        s = pd.Series([42])
        result = _safe_minmax(s)
        assert result.iloc[0] == 0.5


class TestComputeReferrerMetrics:
    def test_returns_dataframe(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        assert isinstance(metrics, pd.DataFrame)
        assert len(metrics) > 0

    def test_has_expected_columns(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        expected = [
            "Referrer",
            "total_referrals",
            "unique_accounts",
            "active_days",
            "burst_count",
            "avg_days_between",
            "channels_used",
        ]
        for col in expected:
            assert col in metrics.columns, f"Missing: {col}"

    def test_excludes_unknown_referrer(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        assert "UNKNOWN" not in metrics["Referrer"].values

    def test_total_referrals_positive(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        assert (metrics["total_referrals"] > 0).all()

    def test_empty_input(self):
        df = pd.DataFrame(
            columns=[
                "Referrer",
                "New Account",
                "MRDB Account Hash",
                "Issue Date",
                "Is Burst",
                "Days Since Last Referral",
                "Referral Channel",
                "Branch Code",
                "Network ID",
                "Network Size",
            ]
        )
        metrics = compute_referrer_metrics(df)
        assert len(metrics) == 0


class TestComputeInfluenceScores:
    def test_adds_influence_score(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        weights = ReferralScoringWeights()
        scored = compute_influence_scores(metrics, weights)
        assert "Influence Score" in scored.columns

    def test_score_range_0_to_100(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        weights = ReferralScoringWeights()
        scored = compute_influence_scores(metrics, weights)
        assert scored["Influence Score"].min() >= 0
        assert scored["Influence Score"].max() <= 100

    def test_repeat_referrers_score_higher(self, enriched_df):
        metrics = compute_referrer_metrics(enriched_df)
        weights = ReferralScoringWeights()
        scored = compute_influence_scores(metrics, weights)
        # Referrers with more unique accounts should generally score higher
        top = scored.nlargest(3, "Influence Score")
        bottom = scored.nsmallest(3, "Influence Score")
        assert top["unique_accounts"].mean() >= bottom["unique_accounts"].mean()

    def test_empty_metrics(self):
        metrics = pd.DataFrame(
            columns=[
                "Referrer",
                "unique_accounts",
                "burst_count",
                "channels_used",
                "avg_days_between",
                "active_days",
            ]
        )
        weights = ReferralScoringWeights()
        scored = compute_influence_scores(metrics, weights)
        assert "Influence Score" in scored.columns
        assert len(scored) == 0


class TestComputeStaffMultipliers:
    def test_returns_dataframe(self, enriched_df, settings):
        referrer_metrics = compute_referrer_metrics(enriched_df)
        scored_metrics = compute_influence_scores(referrer_metrics, settings.scoring_weights)
        staff = compute_staff_multipliers(enriched_df, scored_metrics, settings.staff_weights)
        assert isinstance(staff, pd.DataFrame)
        assert len(staff) > 0

    def test_has_multiplier_score(self, enriched_df, settings):
        referrer_metrics = compute_referrer_metrics(enriched_df)
        scored_metrics = compute_influence_scores(referrer_metrics, settings.scoring_weights)
        staff = compute_staff_multipliers(enriched_df, scored_metrics, settings.staff_weights)
        assert "Multiplier Score" in staff.columns

    def test_score_range_0_to_100(self, enriched_df, settings):
        referrer_metrics = compute_referrer_metrics(enriched_df)
        scored_metrics = compute_influence_scores(referrer_metrics, settings.scoring_weights)
        staff = compute_staff_multipliers(enriched_df, scored_metrics, settings.staff_weights)
        assert staff["Multiplier Score"].min() >= 0
        assert staff["Multiplier Score"].max() <= 100

    def test_excludes_unassigned(self, enriched_df, settings):
        referrer_metrics = compute_referrer_metrics(enriched_df)
        scored_metrics = compute_influence_scores(referrer_metrics, settings.scoring_weights)
        staff = compute_staff_multipliers(enriched_df, scored_metrics, settings.staff_weights)
        assert "UNASSIGNED" not in staff["Staff"].values

    def test_empty_input(self, settings):
        df = pd.DataFrame(
            columns=[
                "Staff",
                "New Account",
                "Referrer",
                "Branch Code",
            ]
        )
        metrics = pd.DataFrame(columns=["Referrer", "Influence Score"])
        staff = compute_staff_multipliers(df, metrics, settings.staff_weights)
        assert len(staff) == 0
