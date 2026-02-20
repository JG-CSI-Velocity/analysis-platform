"""R04: One-time vs Repeat Referrers -- comparison table."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_onetime_vs_repeat(ctx: ReferralContext) -> AnalysisResult:
    """Compare one-time (1 referral) vs repeat (2+) referrers.

    Output: 2-row comparison table with Grand Total.
    """
    name = "One-time vs Repeat Referrers"
    m = ctx.referrer_metrics.copy()

    if m.empty:
        return AnalysisResult.from_df(name, name, pd.DataFrame(), sheet_name="R04_Repeat")

    m["Category"] = m["total_referrals"].apply(lambda x: "Repeat" if x >= 2 else "One-time")

    summary = (
        m.groupby("Category")
        .agg(
            Count=("Referrer", "count"),
            **{"Avg Unique Accounts": ("unique_accounts", "mean")},
            **{"Avg Influence Score": ("Influence Score", "mean")},
            **{"Avg Active Days": ("active_days", "mean")},
        )
        .reset_index()
    )

    total_count = summary["Count"].sum()
    summary["% of Total"] = summary["Count"].apply(lambda x: safe_percentage(x, total_count))

    # Reorder columns
    summary = summary[
        [
            "Category",
            "Count",
            "% of Total",
            "Avg Unique Accounts",
            "Avg Influence Score",
            "Avg Active Days",
        ]
    ]

    # Round floats
    for col in ["Avg Unique Accounts", "Avg Influence Score", "Avg Active Days"]:
        summary[col] = summary[col].round(1)

    # Grand Total row
    total_row = pd.DataFrame(
        [
            {
                "Category": "Grand Total",
                "Count": total_count,
                "% of Total": 100.0,
                "Avg Unique Accounts": m["unique_accounts"].mean().round(1),
                "Avg Influence Score": m["Influence Score"].mean().round(1),
                "Avg Active Days": m["active_days"].mean().round(1),
            }
        ]
    )
    summary = pd.concat([summary, total_row], ignore_index=True)

    return AnalysisResult.from_df(name, name, summary, sheet_name="R04_Repeat")
