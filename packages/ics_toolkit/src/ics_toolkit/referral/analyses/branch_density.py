"""R06: Branch-level Influence Density."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_branch_density(ctx: ReferralContext) -> AnalysisResult:
    """Compute avg influence score of referrers routed through each branch.

    This measures referrer quality per branch, NOT branch production volume.
    """
    name = "Branch Influence Density"
    df = ctx.df.copy()
    m = ctx.referrer_metrics

    if df.empty or m.empty:
        return AnalysisResult.from_df(name, name, pd.DataFrame(), sheet_name="R06_Branch")

    # Exclude unknown branches
    df = df[df["Branch Code"] != "UNKNOWN"].copy()

    influence_lookup = m.set_index("Referrer")["Influence Score"]
    df["_referrer_score"] = df["Referrer"].map(influence_lookup).fillna(0)

    branch = (
        df.groupby("Branch Code")
        .agg(
            **{"Total Referrals": ("MRDB Account Hash", "count")},
            **{"Unique Referrers": ("Referrer", "nunique")},
            **{"Avg Influence Score": ("_referrer_score", "mean")},
        )
        .reset_index()
    )
    branch.rename(columns={"Branch Code": "Branch"}, inplace=True)
    branch["Avg Influence Score"] = branch["Avg Influence Score"].round(1)

    # Add top referrer per branch
    top_by_branch = (
        df.sort_values("_referrer_score", ascending=False)
        .drop_duplicates(subset=["Branch Code"])[["Branch Code", "Referrer"]]
        .rename(columns={"Branch Code": "Branch", "Referrer": "Top Referrer"})
    )
    branch = branch.merge(top_by_branch, on="Branch", how="left")

    # Channel mix (% Standard)
    channel_counts = df.groupby("Branch Code")["Referral Type"].value_counts().unstack(fill_value=0)
    if "Standard" in channel_counts.columns:
        total_per_branch = channel_counts.sum(axis=1)
        channel_counts["Standard %"] = channel_counts["Standard"].apply(lambda x: 0.0)
        for idx in channel_counts.index:
            channel_counts.loc[idx, "Standard %"] = safe_percentage(
                channel_counts.loc[idx, "Standard"], total_per_branch[idx]
            )
        channel_pct = channel_counts[["Standard %"]].reset_index()
        channel_pct.rename(columns={"Branch Code": "Branch"}, inplace=True)
        branch = branch.merge(channel_pct, on="Branch", how="left")

    branch = branch.sort_values("Avg Influence Score", ascending=False).reset_index(drop=True)

    return AnalysisResult.from_df(name, name, branch, sheet_name="R06_Branch")
