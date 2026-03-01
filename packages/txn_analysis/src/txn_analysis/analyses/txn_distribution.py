"""M21: Transaction amount distribution by spending tier.

Computes descriptive statistics and raw distribution data per spending
tier (Low/Medium/High) for violin-plot visualisation.  Outliers are
capped at the 99th percentile to keep the plot readable.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import TIER_ORDER, classify_spending_tiers
from txn_analysis.settings import Settings


def analyze_txn_distribution(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Compute transaction-amount distribution stats per spending tier."""
    if df.empty or "amount" not in df.columns:
        return AnalysisResult.from_df(
            "txn_distribution",
            "Transaction Distribution",
            pd.DataFrame(),
            error="No transaction data available",
        )

    tiered = classify_spending_tiers(df)

    # Cap outliers at 99th percentile
    cap = tiered["amount"].quantile(0.99)
    tiered["amount_capped"] = tiered["amount"].clip(upper=cap)

    rows: list[dict] = []
    raw_parts: list[pd.DataFrame] = []

    for tier in TIER_ORDER:
        subset = tiered[tiered["spending_tier"] == tier]
        if subset.empty:
            continue

        amounts = subset["amount_capped"]
        q1 = amounts.quantile(0.25)
        q3 = amounts.quantile(0.75)
        rows.append(
            {
                "Spending Tier": tier,
                "Count": len(amounts),
                "Mean": round(amounts.mean(), 2),
                "Median": round(amounts.median(), 2),
                "Std Dev": round(amounts.std(), 2) if len(amounts) > 1 else 0.0,
                "Q1": round(q1, 2),
                "Q3": round(q3, 2),
                "IQR": round(q3 - q1, 2),
                "Skewness": round(float(amounts.skew()), 2) if len(amounts) > 2 else 0.0,
                "99th Pct Cap": round(cap, 2),
            }
        )

        raw_part = subset[["spending_tier", "amount_capped"]].copy()
        raw_part.columns = ["spending_tier", "amount"]
        raw_parts.append(raw_part)

    stats_df = pd.DataFrame(rows)
    raw_df = pd.concat(raw_parts, ignore_index=True) if raw_parts else pd.DataFrame()

    data: dict[str, pd.DataFrame] = {"main": stats_df}
    if not raw_df.empty:
        data["raw_amounts"] = raw_df

    summary = ""
    if not stats_df.empty:
        median_vals = stats_df.set_index("Spending Tier")["Median"]
        if "High Spender" in median_vals.index and "Low Spender" in median_vals.index:
            ratio = (
                median_vals["High Spender"] / median_vals["Low Spender"]
                if median_vals["Low Spender"]
                else 0
            )
            summary = f"High Spender median txn is {ratio:.1f}x Low Spender"

    return AnalysisResult(
        name="txn_distribution",
        title="Transaction Amount Distribution",
        data=data,
        metadata={
            "sheet_name": "M21 Distribution",
            "category": "Spending Intelligence",
            "chart_id": "M21",
        },
        summary=summary or "Transaction amount distribution by spending tier",
    )
