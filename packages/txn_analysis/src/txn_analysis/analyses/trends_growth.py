"""M5B: Growth leaders and decliners (MoM spend change)."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings


def analyze_growth_leaders_decliners(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Month-over-month spend change, min threshold, top 50 each direction."""
    threshold = settings.growth_min_threshold

    monthly = (
        df.groupby(["merchant_consolidated", "year_month"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "spend"})
    )
    monthly = monthly.sort_values(["merchant_consolidated", "year_month"])

    months = sorted(monthly["year_month"].unique())
    rows: list[dict] = []

    for i in range(1, len(months)):
        prev_m, curr_m = months[i - 1], months[i]
        prev = monthly[monthly["year_month"] == prev_m].set_index("merchant_consolidated")
        curr = monthly[monthly["year_month"] == curr_m].set_index("merchant_consolidated")

        common = prev.index.intersection(curr.index)
        for merchant in common:
            prev_spend = prev.loc[merchant, "spend"]
            curr_spend = curr.loc[merchant, "spend"]
            if max(prev_spend, curr_spend) < threshold:
                continue
            change_amount = curr_spend - prev_spend
            change_pct = (change_amount / prev_spend * 100) if prev_spend else 0
            rows.append(
                {
                    "merchant_consolidated": merchant,
                    "month_pair": f"{prev_m} -> {curr_m}",
                    "prev_spend": round(prev_spend, 2),
                    "curr_spend": round(curr_spend, 2),
                    "change_amount": round(change_amount, 2),
                    "change_pct": round(change_pct, 2),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return AnalysisResult.from_df(
            "growth_leaders_decliners",
            "Growth Leaders and Decliners",
            result,
            sheet_name="M5B Growth",
        )

    leaders = result.nlargest(settings.top_n, "change_amount")
    decliners = result.nsmallest(settings.top_n, "change_amount")
    combined = pd.concat([leaders, decliners], ignore_index=True).drop_duplicates()

    return AnalysisResult.from_df(
        "growth_leaders_decliners",
        "Growth Leaders and Decliners",
        combined,
        sheet_name="M5B Growth",
    )
