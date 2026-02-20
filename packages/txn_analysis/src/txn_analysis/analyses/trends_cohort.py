"""M5D: New vs declining merchants cohort analysis."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings


def analyze_new_vs_declining(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Track first/last appearance; classify new/returning/lost per month."""
    monthly = (
        df.groupby(["merchant_consolidated", "year_month"])
        .agg(spend=("amount", "sum"), txn_count=("amount", "count"))
        .reset_index()
    )

    months = sorted(monthly["year_month"].unique())
    merchant_first = monthly.groupby("merchant_consolidated")["year_month"].min()

    rows: list[dict] = []
    prev_merchants: set = set()

    for m in months:
        current = monthly[monthly["year_month"] == m]
        current_merchants = set(current["merchant_consolidated"])

        new = {mc for mc in current_merchants if merchant_first.get(mc) == m}
        lost = prev_merchants - current_merchants
        returning = current_merchants - new - prev_merchants if len(prev_merchants) > 0 else set()

        new_spend = current[current["merchant_consolidated"].isin(new)]["spend"].sum()
        returning_spend = current[current["merchant_consolidated"].isin(returning)]["spend"].sum()
        total_spend = current["spend"].sum()

        rows.append(
            {
                "month": m,
                "total_merchants": len(current_merchants),
                "new_merchants": len(new),
                "returning_merchants": len(returning),
                "lost_merchants": len(lost),
                "new_spend": round(new_spend, 2),
                "returning_spend": round(returning_spend, 2),
                "total_spend": round(total_spend, 2),
            }
        )

        prev_merchants = current_merchants

    result = pd.DataFrame(rows)
    return AnalysisResult.from_df(
        "new_vs_declining_merchants",
        "New vs Declining Merchants",
        result,
        sheet_name="M5D Cohorts",
    )
