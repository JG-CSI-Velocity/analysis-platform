"""M16: Time-of-day and day-of-week transaction patterns.

Analyzes when members transact -- peak hours, weekend vs weekday spend,
and day-of-week distribution. Useful for marketing timing decisions.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

_DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def analyze_time_patterns(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Analyze day-of-week transaction patterns.

    Produces a summary of spend, transactions, and average ticket
    by day of the week, plus weekend vs weekday comparison.
    """
    if "transaction_date" not in df.columns:
        return AnalysisResult.from_df(
            "time_patterns",
            "Day-of-Week Transaction Patterns",
            pd.DataFrame(),
            error="Missing transaction_date column",
        )

    dt = pd.to_datetime(df["transaction_date"], errors="coerce")
    valid_mask = dt.notna()
    if valid_mask.sum() == 0:
        return AnalysisResult.from_df(
            "time_patterns",
            "Day-of-Week Transaction Patterns",
            pd.DataFrame(),
            error="No valid transaction dates",
        )

    work_df = df[valid_mask].copy()
    work_df["day_name"] = dt[valid_mask].dt.day_name()
    work_df["is_weekend"] = dt[valid_mask].dt.dayofweek >= 5

    # Day-of-week breakdown
    dow = (
        work_df.groupby("day_name")
        .agg(
            transactions=("amount", "count"),
            total_spend=("amount", "sum"),
            avg_ticket=("amount", "mean"),
            unique_accounts=("primary_account_num", "nunique"),
        )
        .reindex(_DAY_ORDER)
        .reset_index()
    )

    dow["pct_of_transactions"] = (dow["transactions"] / dow["transactions"].sum() * 100).round(1)
    dow["total_spend"] = dow["total_spend"].round(2)
    dow["avg_ticket"] = dow["avg_ticket"].round(2)

    dow.columns = [
        "Day",
        "Transactions",
        "Total Spend",
        "Avg Ticket",
        "Unique Accounts",
        "% of Transactions",
    ]

    # Weekend vs weekday summary
    weekend_txns = work_df[work_df["is_weekend"]]["amount"]
    weekday_txns = work_df[~work_df["is_weekend"]]["amount"]

    weekend_spend = weekend_txns.sum()
    weekday_spend = weekday_txns.sum()
    total_spend = weekend_spend + weekday_spend
    weekend_pct = (weekend_spend / total_spend * 100) if total_spend else 0

    peak_day = dow.loc[dow["Transactions"].idxmax(), "Day"] if not dow.empty else "--"

    meta = {
        "sheet_name": "M16 Time Patterns",
        "peak_day": peak_day,
        "weekend_spend_pct": round(weekend_pct, 1),
        "weekend_avg_ticket": round(weekend_txns.mean(), 2) if len(weekend_txns) else 0,
        "weekday_avg_ticket": round(weekday_txns.mean(), 2) if len(weekday_txns) else 0,
    }
    return AnalysisResult(
        name="time_patterns",
        title="Day-of-Week Transaction Patterns",
        data={"main": dow},
        metadata=meta,
        summary=(
            f"Peak day: {peak_day}. "
            f"Weekend spend: {weekend_pct:.1f}% of total. "
            f"Weekend avg ticket: ${weekend_txns.mean():.2f} vs "
            f"weekday ${weekday_txns.mean():.2f}"
        ),
    )
