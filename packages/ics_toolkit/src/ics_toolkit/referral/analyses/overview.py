"""R08: Overview KPIs -- summary metrics across all layers."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_overview(
    ctx: ReferralContext,
    prior_results: list[AnalysisResult] | None = None,
) -> AnalysisResult:
    """Produce headline KPIs for the referral program."""
    name = "Overview KPIs"
    df = ctx.df
    m = ctx.referrer_metrics
    s = ctx.staff_metrics

    kpis: list[tuple[str, object]] = []

    # Volume metrics
    kpis.append(("Total Referrals", len(df)))
    kpis.append(("Unique Referrers", m["Referrer"].nunique() if not m.empty else 0))
    kpis.append(("Unique New Accounts", df["MRDB Account Hash"].nunique()))

    # Referrer behavior
    if not m.empty:
        repeat_count = (m["total_referrals"] >= 2).sum()
        kpis.append(("Repeat Referrer %", safe_percentage(repeat_count, len(m))))
        kpis.append(("Avg Referrals per Referrer", round(m["total_referrals"].mean(), 1)))
        kpis.append(("Top Referrer Score", m["Influence Score"].max()))
        kpis.append(("Median Influence Score", round(m["Influence Score"].median(), 1)))
    else:
        kpis.extend(
            [
                ("Repeat Referrer %", 0.0),
                ("Avg Referrals per Referrer", 0.0),
                ("Top Referrer Score", 0.0),
                ("Median Influence Score", 0.0),
            ]
        )

    # Temporal
    if "Days Since Last Referral" in df.columns:
        avg_gap = df["Days Since Last Referral"].mean()
        gap_val = round(avg_gap, 1) if pd.notna(avg_gap) else "N/A"
        kpis.append(("Avg Days Between Referrals", gap_val))
    if "Is Burst" in df.columns:
        burst_pct = safe_percentage(df["Is Burst"].sum(), len(df))
        kpis.append(("Burst Referral %", burst_pct))

    # Staff
    if not s.empty:
        top_staff = s.loc[s["Multiplier Score"].idxmax(), "Staff"]
        kpis.append(("Top Staff (Multiplier)", top_staff))
    else:
        kpis.append(("Top Staff (Multiplier)", "N/A"))

    # Branch
    if "Branch Code" in df.columns:
        top_branch = df["Branch Code"].value_counts().index[0] if len(df) > 0 else "N/A"
        kpis.append(("Most Active Branch", top_branch))

    # Code health
    if "Referral Channel" in df.columns:
        top_channel = df["Referral Channel"].value_counts().index[0] if len(df) > 0 else "N/A"
        kpis.append(("Dominant Channel", top_channel))
    if "Referral Type" in df.columns:
        manual_pct = safe_percentage((df["Referral Type"] == "Manual").sum(), len(df))
        exception_pct = safe_percentage((df["Referral Type"] == "Exception").sum(), len(df))
        kpis.append(("Manual Code %", manual_pct))
        kpis.append(("Exception Code %", exception_pct))

    # Network
    if "Network Size" in df.columns:
        avg_net = df.groupby("Referrer")["Network Size"].max().mean()
        kpis.append(("Avg Network Size", round(avg_net, 1) if pd.notna(avg_net) else "N/A"))

    out = pd.DataFrame(kpis, columns=["Metric", "Value"])
    return AnalysisResult(name=name, title=name, df=out, sheet_name="R08_Overview")
