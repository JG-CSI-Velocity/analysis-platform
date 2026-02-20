"""R07: Referral Code Health Report."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_code_health(ctx: ReferralContext) -> AnalysisResult:
    """Produce referral code distribution by channel, type, and reliability."""
    name = "Code Health Report"
    df = ctx.df.copy()

    if df.empty:
        empty = pd.DataFrame()
        return AnalysisResult.from_df(
            name,
            name,
            empty,
            sheet_name="R07_Code_Health",
        )

    summary = (
        df.groupby(["Referral Channel", "Referral Type", "Referral Reliability"])
        .agg(
            Count=("MRDB Account Hash", "count"),
        )
        .reset_index()
    )

    total = summary["Count"].sum()
    summary["% of Total"] = summary["Count"].apply(lambda x: safe_percentage(x, total))

    # Known code % (reliability != Low)
    known_total = summary.loc[summary["Referral Reliability"] != "Low", "Count"].sum()
    summary["Known Code %"] = safe_percentage(known_total, total)

    summary = summary.sort_values("Count", ascending=False).reset_index(drop=True)

    # Rename for output
    summary.rename(
        columns={
            "Referral Channel": "Channel",
            "Referral Type": "Type",
            "Referral Reliability": "Reliability",
        },
        inplace=True,
    )

    return AnalysisResult.from_df(name, name, summary, sheet_name="R07_Code_Health")
