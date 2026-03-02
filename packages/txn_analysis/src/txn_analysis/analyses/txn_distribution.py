"""M21: Transaction amount distribution by spending tier.

Computes descriptive statistics and raw distribution data per spending
tier (Low/Medium/High) for violin-plot visualisation.  Outliers are
capped at the 99th percentile to keep the plot readable.

Also includes:
  - Ticket size tier breakdown (Micro/Small/Medium/Large)
  - Monthly average ticket trend line
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import TIER_ORDER, classify_spending_tiers
from txn_analysis.settings import Settings

# Ticket size tier thresholds
TICKET_TIERS = [
    ("Micro (<$10)", 0, 10),
    ("Small ($10-50)", 10, 50),
    ("Medium ($50-200)", 50, 200),
    ("Large ($200+)", 200, float("inf")),
]
TICKET_TIER_ORDER = [t[0] for t in TICKET_TIERS]


def _classify_ticket_tier(amount: float) -> str:
    """Assign a single transaction amount to a ticket size tier."""
    for label, low, high in TICKET_TIERS:
        if low <= amount < high:
            return label
    return TICKET_TIER_ORDER[-1]


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

    # --- Sheet 3: Ticket size tier breakdown ---
    ticket_tier_col = df["amount"].apply(_classify_ticket_tier)
    tier_rows: list[dict] = []
    total_txns = len(df)
    total_spend = df["amount"].sum()
    for label in TICKET_TIER_ORDER:
        mask = ticket_tier_col == label
        count = mask.sum()
        spend = df.loc[mask, "amount"].sum()
        avg_ticket = df.loc[mask, "amount"].mean() if count > 0 else 0
        tier_rows.append(
            {
                "Ticket Tier": label,
                "Transactions": count,
                "% of Transactions": round(count / total_txns * 100, 1) if total_txns else 0,
                "Total Spend": round(spend, 2),
                "% of Spend": round(spend / total_spend * 100, 1) if total_spend else 0,
                "Avg Ticket": round(avg_ticket, 2),
            }
        )
    ticket_df = pd.DataFrame(tier_rows)
    if not ticket_df.empty:
        data["ticket_tiers"] = ticket_df

    # --- Sheet 4: Monthly average ticket trend ---
    trend_df = pd.DataFrame()
    if "transaction_date" in df.columns:
        dt = pd.to_datetime(df["transaction_date"], errors="coerce", format="mixed")
        valid = dt.notna()
        if valid.sum() > 0:
            work = df[valid].copy()
            work["txn_month"] = dt[valid].dt.to_period("M").astype(str)
            monthly = (
                work.groupby("txn_month")
                .agg(
                    avg_ticket=("amount", "mean"),
                    median_ticket=("amount", "median"),
                    transactions=("amount", "count"),
                    total_spend=("amount", "sum"),
                )
                .reset_index()
            )
            monthly["avg_ticket"] = monthly["avg_ticket"].round(2)
            monthly["median_ticket"] = monthly["median_ticket"].round(2)
            monthly["total_spend"] = monthly["total_spend"].round(2)
            monthly.columns = [
                "Month",
                "Avg Ticket",
                "Median Ticket",
                "Transactions",
                "Total Spend",
            ]
            trend_df = monthly
            if not trend_df.empty:
                data["monthly_trend"] = trend_df

    # Summary
    summary_parts: list[str] = []
    if not stats_df.empty:
        median_vals = stats_df.set_index("Spending Tier")["Median"]
        if "High Spender" in median_vals.index and "Low Spender" in median_vals.index:
            ratio = (
                median_vals["High Spender"] / median_vals["Low Spender"]
                if median_vals["Low Spender"]
                else 0
            )
            summary_parts.append(f"High Spender median txn is {ratio:.1f}x Low Spender")

    if not ticket_df.empty:
        dominant = ticket_df.loc[ticket_df["Transactions"].idxmax()]
        summary_parts.append(
            f"Most common: {dominant['Ticket Tier']} ({dominant['% of Transactions']:.0f}% of txns)"
        )

    if not trend_df.empty and len(trend_df) >= 2:
        first_avg = trend_df.iloc[0]["Avg Ticket"]
        last_avg = trend_df.iloc[-1]["Avg Ticket"]
        if first_avg > 0:
            change = (last_avg - first_avg) / first_avg * 100
            direction = "up" if change > 0 else "down"
            summary_parts.append(f"Avg ticket {direction} {abs(change):.1f}% over period")

    meta: dict = {
        "sheet_name": "M21 Distribution",
        "category": "Spending Intelligence",
        "chart_id": "M21",
    }
    if not ticket_df.empty:
        meta["dominant_tier"] = ticket_df.loc[ticket_df["Transactions"].idxmax(), "Ticket Tier"]
    if not trend_df.empty:
        meta["latest_avg_ticket"] = float(trend_df.iloc[-1]["Avg Ticket"])

    summary = ". ".join(summary_parts) if summary_parts else "Transaction amount distribution by spending tier"

    return AnalysisResult(
        name="txn_distribution",
        title="Transaction Amount Distribution",
        data=data,
        metadata=meta,
        summary=summary,
    )
