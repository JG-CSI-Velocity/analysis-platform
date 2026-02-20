"""R03: Dormant High-Value Referrers -- previously active, now inactive."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_dormant_referrers(ctx: ReferralContext) -> AnalysisResult:
    """Identify referrers who were historically high-value but are now dormant.

    Dormant = no referral in last dormancy_days.
    High-value = unique_accounts >= high_value_min_referrals OR
    Influence Score in top quartile.
    """
    name = "Dormant High-Value Referrers"
    m = ctx.referrer_metrics.copy()

    if m.empty:
        return AnalysisResult.from_df(name, name, m, sheet_name="R03_Dormant")

    max_date = ctx.df["Issue Date"].max()
    if pd.isna(max_date):
        return AnalysisResult.from_df(name, name, pd.DataFrame(), sheet_name="R03_Dormant")

    dormancy_cutoff = max_date - pd.Timedelta(days=ctx.settings.dormancy_days)

    # Dormant: last referral before cutoff
    dormant = m[m["last_referral"] < dormancy_cutoff].copy()

    if dormant.empty:
        return AnalysisResult.from_df(name, name, pd.DataFrame(), sheet_name="R03_Dormant")

    # High-value: meets min referrals OR top quartile influence
    score_q75 = m["Influence Score"].quantile(0.75) if len(m) >= 4 else 0
    high_value = dormant[
        (dormant["unique_accounts"] >= ctx.settings.high_value_min_referrals)
        | (dormant["Influence Score"] >= score_q75)
    ].copy()

    high_value["Days Dormant"] = (max_date - high_value["last_referral"]).dt.days

    cols = {
        "Referrer": "Referrer",
        "Influence Score": "Historical Score",
        "total_referrals": "Total Referrals",
        "unique_accounts": "Unique Accounts",
        "last_referral": "Last Referral",
        "Days Dormant": "Days Dormant",
    }
    available = {k: v for k, v in cols.items() if k in high_value.columns}
    out = high_value[list(available.keys())].rename(columns=available)
    out = out.sort_values("Historical Score", ascending=False).reset_index(drop=True)

    return AnalysisResult.from_df(name, name, out, sheet_name="R03_Dormant")
