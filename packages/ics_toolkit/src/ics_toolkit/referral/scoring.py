"""Layer 5: Influence scoring and staff multiplier computation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ics_toolkit.settings import ReferralScoringWeights, ReferralStaffWeights

logger = logging.getLogger(__name__)


def compute_referrer_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-referrer metrics for influence scoring.

    Excludes referrers where Referrer == 'UNKNOWN'.
    """
    scored_df = df[df["Referrer"] != "UNKNOWN"].copy()
    if scored_df.empty:
        return pd.DataFrame(
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
                "network_count",
                "max_network_size",
            ]
        )

    metrics = (
        scored_df.groupby("Referrer")
        .agg(
            total_referrals=("New Account", "count"),
            unique_accounts=("MRDB Account Hash", "nunique"),
            active_days=(
                "Issue Date",
                lambda x: (x.max() - x.min()).days + 1 if x.notna().any() else 0,
            ),
            burst_count=("Is Burst", "sum"),
            avg_days_between=("Days Since Last Referral", "mean"),
            channels_used=("Referral Channel", "nunique"),
            branches_used=("Branch Code", "nunique"),
            first_referral=("Issue Date", "min"),
            last_referral=("Issue Date", "max"),
            network_count=("Network ID", "nunique"),
            max_network_size=("Network Size", "max"),
        )
        .reset_index()
    )
    return metrics


def compute_influence_scores(
    metrics: pd.DataFrame,
    weights: ReferralScoringWeights,
) -> pd.DataFrame:
    """Compute weighted composite influence score (0-100)."""
    if metrics.empty:
        metrics["Influence Score"] = pd.Series(dtype=float)
        return metrics

    m = metrics.copy()
    m["avg_days_between"] = m["avg_days_between"].fillna(0)

    logger.info(
        "Scoring weights: accounts=%.2f burst=%.2f channels=%.2f velocity=%.2f longevity=%.2f",
        weights.unique_accounts,
        weights.burst_count,
        weights.channels_used,
        weights.velocity,
        weights.longevity,
    )

    m["score"] = (
        weights.unique_accounts * _safe_minmax(m["unique_accounts"])
        + weights.burst_count * _safe_minmax(m["burst_count"])
        + weights.channels_used * _safe_minmax(m["channels_used"])
        + weights.velocity * _safe_minmax(1 / (m["avg_days_between"] + 1))
        + weights.longevity * _safe_minmax(m["active_days"])
    )
    m["Influence Score"] = (_safe_minmax(m["score"]) * 100).round(1)
    return m


def compute_staff_multipliers(
    df: pd.DataFrame,
    referrer_metrics: pd.DataFrame,
    weights: ReferralStaffWeights,
) -> pd.DataFrame:
    """Compute staff multiplier scores (processing reach, NOT influence)."""
    scored_df = df[df["Staff"] != "UNASSIGNED"].copy()
    if scored_df.empty or referrer_metrics.empty:
        return pd.DataFrame(
            columns=[
                "Staff",
                "referrals_processed",
                "unique_referrers",
                "unique_branches",
                "avg_referrer_score",
                "Multiplier Score",
            ]
        )

    influence_lookup = referrer_metrics.set_index("Referrer")["Influence Score"]

    staff = (
        scored_df.groupby("Staff")
        .agg(
            referrals_processed=("New Account", "count"),
            unique_referrers=("Referrer", "nunique"),
            unique_branches=("Branch Code", "nunique"),
        )
        .reset_index()
    )

    staff["avg_referrer_score"] = (
        scored_df.groupby("Staff")["Referrer"]
        .apply(lambda refs: influence_lookup.reindex(refs.unique(), fill_value=0).mean())
        .values
    )

    staff["Multiplier Score"] = weights.avg_referrer_score * _safe_minmax(
        staff["avg_referrer_score"]
    ) + weights.unique_referrers * _safe_minmax(staff["unique_referrers"])
    staff["Multiplier Score"] = (staff["Multiplier Score"] * 100).round(1)
    return staff


def _safe_minmax(series: pd.Series) -> pd.Series:
    """Min-max normalize to 0-1. Returns 0.5 for constant series."""
    min_val, max_val = series.min(), series.max()
    if max_val - min_val == 0:
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val)
