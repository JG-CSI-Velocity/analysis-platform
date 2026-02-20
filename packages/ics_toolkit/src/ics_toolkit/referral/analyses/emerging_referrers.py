"""R02: Emerging Referrers -- new and accelerating referrers."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_emerging_referrers(ctx: ReferralContext) -> AnalysisResult:
    """Identify referrers who are new AND accelerating.

    Emerging = first appeared within emerging_lookback_days AND
    burst_count >= emerging_min_burst_count.
    """
    name = "Emerging Referrers"
    m = ctx.referrer_metrics.copy()
    df = ctx.df

    if m.empty:
        return AnalysisResult(name=name, title=name, df=m, sheet_name="R02_Emerging")

    max_date = df["Issue Date"].max()
    if pd.isna(max_date):
        return AnalysisResult(name=name, title=name, df=pd.DataFrame(), sheet_name="R02_Emerging")

    lookback_cutoff = max_date - pd.Timedelta(days=ctx.settings.emerging_lookback_days)

    # Filter to new referrers (first referral within lookback window)
    emerging = m[
        (m["first_referral"] >= lookback_cutoff)
        & (m["burst_count"] >= ctx.settings.emerging_min_burst_count)
    ].copy()

    cols = {
        "Referrer": "Referrer",
        "Influence Score": "Influence Score",
        "burst_count": "Burst Count",
        "active_days": "Days Active",
        "first_referral": "First Referral",
        "last_referral": "Last Referral",
        "total_referrals": "Total Referrals",
    }
    available = {k: v for k, v in cols.items() if k in emerging.columns}
    out = emerging[list(available.keys())].rename(columns=available)
    out = out.sort_values("Influence Score", ascending=False).reset_index(drop=True)

    return AnalysisResult(name=name, title=name, df=out, sheet_name="R02_Emerging")
