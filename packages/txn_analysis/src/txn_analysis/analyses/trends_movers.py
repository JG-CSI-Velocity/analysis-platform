"""M5E+F: Business and personal monthly movers."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings


def _compute_movers(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    """Compute rank + spend changes across consecutive months."""
    if df.empty:
        return pd.DataFrame()

    monthly = (
        df.groupby(["merchant_consolidated", "year_month"])
        .agg(spend=("amount", "sum"), txn_count=("amount", "count"))
        .reset_index()
    )
    monthly["rank"] = (
        monthly.groupby("year_month")["spend"].rank(ascending=False, method="min").astype(int)
    )

    months = sorted(monthly["year_month"].unique())
    rows: list[dict] = []

    for i in range(1, len(months)):
        prev_m, curr_m = months[i - 1], months[i]
        prev = monthly[monthly["year_month"] == prev_m].set_index("merchant_consolidated")
        curr = monthly[monthly["year_month"] == curr_m].set_index("merchant_consolidated")

        common = prev.index.intersection(curr.index)
        for merchant in common:
            prev_rank = int(prev.loc[merchant, "rank"])
            curr_rank = int(curr.loc[merchant, "rank"])
            if prev_rank > 100 and curr_rank > 100:
                continue
            prev_spend = float(prev.loc[merchant, "spend"])
            curr_spend = float(curr.loc[merchant, "spend"])
            spend_change = curr_spend - prev_spend
            spend_pct = (spend_change / prev_spend * 100) if prev_spend else 0

            rows.append(
                {
                    "month_transition": f"{prev_m} -> {curr_m}",
                    "merchant_consolidated": merchant,
                    "prev_rank": prev_rank,
                    "curr_rank": curr_rank,
                    "rank_change": prev_rank - curr_rank,
                    "prev_spend": round(prev_spend, 2),
                    "curr_spend": round(curr_spend, 2),
                    "spend_change": round(spend_change, 2),
                    "spend_change_pct": round(spend_pct, 2),
                }
            )

    return pd.DataFrame(rows)


def analyze_business_movers(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = _compute_movers(business_df, top_n=settings.top_n)
    return AnalysisResult(
        name="business_monthly_movers",
        title="Business Monthly Movers",
        df=result,
        sheet_name="M5E Biz Movers",
    )


def analyze_personal_movers(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = _compute_movers(personal_df, top_n=settings.top_n)
    return AnalysisResult(
        name="personal_monthly_movers",
        title="Personal Monthly Movers",
        df=result,
        sheet_name="M5F Personal Movers",
    )
