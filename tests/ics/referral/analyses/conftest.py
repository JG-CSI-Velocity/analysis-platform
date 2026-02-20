"""Shared fixtures for referral analysis artifact tests."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.referral.analyses.base import ReferralContext
from ics_toolkit.referral.code_decoder import decode_referral_codes
from ics_toolkit.referral.network import infer_networks
from ics_toolkit.referral.normalizer import normalize_entities
from ics_toolkit.referral.scoring import (
    compute_influence_scores,
    compute_referrer_metrics,
    compute_staff_multipliers,
)
from ics_toolkit.referral.temporal import add_temporal_signals


@pytest.fixture
def referral_context(sample_referral_df, sample_referral_settings):
    """Fully-processed ReferralContext ready for analysis functions."""
    df = sample_referral_df.copy()
    settings = sample_referral_settings

    # Run full pipeline: normalize -> decode -> temporal -> network -> scoring
    df = normalize_entities(df, settings)
    df = decode_referral_codes(df, settings)
    df = add_temporal_signals(df, settings)
    df = infer_networks(df)

    metrics = compute_referrer_metrics(df)
    metrics = compute_influence_scores(metrics, settings.scoring_weights)
    staff = compute_staff_multipliers(df, metrics, settings.staff_weights)

    return ReferralContext(
        df=df,
        referrer_metrics=metrics,
        staff_metrics=staff,
        settings=settings,
    )


@pytest.fixture
def empty_context(sample_referral_settings):
    """ReferralContext with empty DataFrames for edge-case testing."""
    return ReferralContext(
        df=pd.DataFrame(
            columns=[
                "Referrer",
                "New Account",
                "Staff",
                "Branch Code",
                "Issue Date",
                "MRDB Account Hash",
                "Referral Channel",
                "Referral Type",
                "Referral Reliability",
                "Days Since Last Referral",
                "Is Burst",
                "Network ID",
                "Network Size",
            ]
        ),
        referrer_metrics=pd.DataFrame(
            columns=[
                "Referrer",
                "total_referrals",
                "unique_accounts",
                "active_days",
                "burst_count",
                "avg_days_between",
                "channels_used",
                "branches_used",
                "first_referral",
                "last_referral",
                "Influence Score",
            ]
        ),
        staff_metrics=pd.DataFrame(
            columns=[
                "Staff",
                "referrals_processed",
                "unique_referrers",
                "unique_branches",
                "avg_referrer_score",
                "Multiplier Score",
            ]
        ),
        settings=sample_referral_settings,
    )
