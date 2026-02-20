"""R05: Staff Multipliers -- processing reach, NOT influence."""

from __future__ import annotations

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.base import ReferralContext


def analyze_staff_multipliers(ctx: ReferralContext) -> AnalysisResult:
    """Produce the staff multiplier ranking table."""
    name = "Staff Multipliers"
    s = ctx.staff_metrics.copy()

    if s.empty:
        return AnalysisResult.from_df(name, name, s, sheet_name="R05_Staff")

    cols = {
        "Staff": "Staff",
        "Multiplier Score": "Multiplier Score",
        "referrals_processed": "Referrals Processed",
        "unique_referrers": "Unique Referrers",
        "avg_referrer_score": "Avg Referrer Score",
        "unique_branches": "Unique Branches",
    }
    available = {k: v for k, v in cols.items() if k in s.columns}
    out = s[list(available.keys())].rename(columns=available)
    out["Avg Referrer Score"] = out["Avg Referrer Score"].round(1)
    out = out.sort_values("Multiplier Score", ascending=False).reset_index(drop=True)

    return AnalysisResult.from_df(name, name, out, sheet_name="R05_Staff")
