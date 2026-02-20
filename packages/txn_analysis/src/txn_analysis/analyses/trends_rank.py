"""M5A: Monthly merchant rank tracking."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings


def analyze_monthly_rank_tracking(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Track merchant rank positions month-over-month."""
    monthly = df.groupby(["merchant_consolidated", "year_month"])["amount"].sum().reset_index()
    monthly["rank"] = (
        monthly.groupby("year_month")["amount"].rank(ascending=False, method="min").astype(int)
    )

    pivot = monthly.pivot_table(index="merchant_consolidated", columns="year_month", values="rank")

    # Only merchants that appeared in top 50 at least once
    top_mask = (pivot <= 50).any(axis=1)
    pivot = pivot[top_mask]

    months = sorted(pivot.columns)
    result = pd.DataFrame({"merchant_consolidated": pivot.index})
    for m in months:
        result[m] = pivot[m].values

    rank_cols = months
    result["avg_rank"] = result[rank_cols].mean(axis=1).round(1)
    result["months_in_top_50"] = (result[rank_cols] <= 50).sum(axis=1).astype(int)

    result = result.sort_values("avg_rank").head(settings.top_n).reset_index(drop=True)

    return AnalysisResult.from_df(
        "monthly_rank_tracking",
        "Monthly Merchant Rank Tracking",
        result,
        sheet_name="M5A Rank Tracking",
    )
