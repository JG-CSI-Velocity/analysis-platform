"""Tests for temporal signal analysis."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.referral.code_decoder import decode_referral_codes
from ics_toolkit.referral.normalizer import normalize_entities
from ics_toolkit.referral.temporal import add_temporal_signals
from ics_toolkit.settings import ReferralSettings


@pytest.fixture
def settings():
    return ReferralSettings()


@pytest.fixture
def enriched_df(sample_referral_df, settings):
    """Sample df with normalization and decoding applied."""
    df = normalize_entities(sample_referral_df, settings)
    df = decode_referral_codes(df, settings)
    return df


class TestAddTemporalSignals:
    def test_adds_expected_columns(self, enriched_df, settings):
        result = add_temporal_signals(enriched_df, settings)
        expected = ["Days Since Last Referral", "Is Burst", "Days Since Latest", "Is New Referrer"]
        for col in expected:
            assert col in result.columns, f"Missing: {col}"

    def test_first_referral_per_referrer_has_null_gap(self, enriched_df, settings):
        result = add_temporal_signals(enriched_df, settings)
        for referrer, group in result.groupby("Referrer"):
            first_idx = group.index[0]
            assert pd.isna(result.loc[first_idx, "Days Since Last Referral"])

    def test_is_burst_boolean(self, enriched_df, settings):
        result = add_temporal_signals(enriched_df, settings)
        assert result["Is Burst"].dtype == bool

    def test_days_since_latest_non_negative(self, enriched_df, settings):
        result = add_temporal_signals(enriched_df, settings)
        valid = result["Days Since Latest"].dropna()
        assert (valid >= 0).all()

    def test_burst_window_configurable(self, enriched_df):
        short_window = ReferralSettings(burst_window_days=3)
        wide_window = ReferralSettings(burst_window_days=365)
        short = add_temporal_signals(enriched_df, short_window)
        wide = add_temporal_signals(enriched_df, wide_window)
        assert short["Is Burst"].sum() <= wide["Is Burst"].sum()

    def test_is_new_referrer_reflects_lookback(self, enriched_df):
        # With a very long lookback, all referrers should be "new"
        long_lookback = ReferralSettings(emerging_lookback_days=9999)
        result = add_temporal_signals(enriched_df, long_lookback)
        assert result["Is New Referrer"].all()

    def test_handles_all_nat_dates(self, settings):
        df = pd.DataFrame(
            {
                "Referrer": ["A", "B"],
                "Issue Date": [pd.NaT, pd.NaT],
                "Referral Channel": ["X", "Y"],
            }
        )
        result = add_temporal_signals(df, settings)
        assert "Days Since Last Referral" in result.columns
