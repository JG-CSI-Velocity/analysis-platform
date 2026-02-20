"""Layer 3: Temporal signal analysis for referral data."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ics_toolkit.settings import ReferralSettings


def add_temporal_signals(df: pd.DataFrame, settings: ReferralSettings) -> pd.DataFrame:
    """Add time-based signals to the enriched referral DataFrame.

    Added columns: Days Since Last Referral, Is Burst, Days Since Latest, Is New Referrer
    """
    df = df.sort_values(["Referrer", "Issue Date"]).copy()

    df["Days Since Last Referral"] = df.groupby("Referrer")["Issue Date"].diff().dt.days

    df["Is Burst"] = df["Days Since Last Referral"].between(0, settings.burst_window_days)

    max_date = df["Issue Date"].max()
    if pd.notna(max_date):
        df["Days Since Latest"] = (max_date - df["Issue Date"]).dt.days
        first_dates = df.groupby("Referrer")["Issue Date"].transform("min")
        df["Is New Referrer"] = (max_date - first_dates).dt.days <= settings.emerging_lookback_days
    else:
        df["Days Since Latest"] = pd.NA
        df["Is New Referrer"] = False

    return df
