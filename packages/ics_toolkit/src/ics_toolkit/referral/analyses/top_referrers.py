"""R01: Top Referrers -- influence-ranked referrer table."""

from __future__ import annotations

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_top_referrers(ctx: ReferralContext) -> AnalysisResult:
    """Produce the top N referrers ranked by influence score.

    Excludes single-referral referrers (total_referrals <= 1).
    """
    name = "Top Referrers"
    m = ctx.referrer_metrics.copy()

    if m.empty:
        return AnalysisResult(name=name, title=name, df=m, sheet_name="R01_Top_Referrers")

    # Exclude single-referral referrers
    m = m[m["total_referrals"] > 1].copy()

    # Select and rename columns for output
    cols = {
        "Referrer": "Referrer",
        "Influence Score": "Influence Score",
        "unique_accounts": "Unique Accounts",
        "total_referrals": "Total Referrals",
        "burst_count": "Burst Count",
        "channels_used": "Channels Used",
        "branches_used": "Branches Used",
        "max_network_size": "Network Size",
        "active_days": "Active Days",
    }
    available = {k: v for k, v in cols.items() if k in m.columns}
    out = m[list(available.keys())].rename(columns=available)
    out = out.sort_values("Influence Score", ascending=False).head(ctx.settings.top_n_referrers)
    out = out.reset_index(drop=True)

    return AnalysisResult(name=name, title=name, df=out, sheet_name="R01_Top_Referrers")
