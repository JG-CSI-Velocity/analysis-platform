"""M16: Time-of-day, day-of-week, and day-of-month transaction patterns.

Analyzes when members transact -- peak days, weekend vs weekday spend,
day-of-week and day-of-month distribution, and whether larger transactions
cluster early or late in the month. Useful for marketing timing decisions.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

_DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Day-of-month buckets
_DOM_LABELS = ["Days 1-7", "Days 8-14", "Days 15-21", "Days 22-31"]


def _bucket_day_of_month(day: int) -> str:
    """Assign day-of-month to a weekly bucket."""
    if day <= 7:
        return "Days 1-7"
    if day <= 14:
        return "Days 8-14"
    if day <= 21:
        return "Days 15-21"
    return "Days 22-31"


def analyze_time_patterns(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Analyze day-of-week and day-of-month transaction patterns.

    Produces:
      - main: Day-of-week breakdown (spend, txns, avg ticket)
      - day_of_month: Day-of-month bucket analysis (early vs late month)
    """
    if "transaction_date" not in df.columns:
        return AnalysisResult.from_df(
            "time_patterns",
            "Transaction Timing Patterns",
            pd.DataFrame(),
            error="Missing transaction_date column",
        )

    dt = pd.to_datetime(df["transaction_date"], errors="coerce", format="mixed")
    valid_mask = dt.notna()
    if valid_mask.sum() == 0:
        return AnalysisResult.from_df(
            "time_patterns",
            "Transaction Timing Patterns",
            pd.DataFrame(),
            error="No valid transaction dates",
        )

    work_df = df[valid_mask].copy()
    work_df["day_name"] = dt[valid_mask].dt.day_name()
    work_df["is_weekend"] = dt[valid_mask].dt.dayofweek >= 5
    work_df["day_of_month"] = dt[valid_mask].dt.day
    work_df["dom_bucket"] = work_df["day_of_month"].apply(_bucket_day_of_month)

    # --- Sheet 1: Day-of-week breakdown ---
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

    # --- Sheet 2: Day-of-month bucket breakdown ---
    dom = (
        work_df.groupby("dom_bucket")
        .agg(
            transactions=("amount", "count"),
            total_spend=("amount", "sum"),
            avg_ticket=("amount", "mean"),
            unique_accounts=("primary_account_num", "nunique"),
        )
        .reindex(_DOM_LABELS)
        .reset_index()
    )

    dom["pct_of_spend"] = (dom["total_spend"] / dom["total_spend"].sum() * 100).round(1)
    dom["total_spend"] = dom["total_spend"].round(2)
    dom["avg_ticket"] = dom["avg_ticket"].round(2)

    dom.columns = [
        "Period",
        "Transactions",
        "Total Spend",
        "Avg Ticket",
        "Unique Accounts",
        "% of Spend",
    ]

    # --- Sheet 3: Week-of-month x day-of-week heatmap ---
    _WOM_LABELS = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
    work_df["week_of_month"] = (work_df["day_of_month"] - 1) // 7
    work_df["week_of_month"] = work_df["week_of_month"].clip(upper=4)
    work_df["week_label"] = work_df["week_of_month"].map(
        {i: _WOM_LABELS[i] for i in range(5)}
    )

    heatmap_data = (
        work_df.groupby(["week_label", "day_name"])
        .agg(transactions=("amount", "count"), total_spend=("amount", "sum"))
        .reset_index()
    )
    # Pivot for heatmap: rows = week, cols = day
    heat_txns = heatmap_data.pivot_table(
        index="week_label", columns="day_name", values="transactions", fill_value=0,
    )
    # Reorder axes
    heat_txns = heat_txns.reindex(index=_WOM_LABELS, columns=_DAY_ORDER).fillna(0).astype(int)

    # Weekend vs weekday summary
    weekend_txns = work_df[work_df["is_weekend"]]["amount"]
    weekday_txns = work_df[~work_df["is_weekend"]]["amount"]

    weekend_spend = weekend_txns.sum()
    weekday_spend = weekday_txns.sum()
    total_spend = weekend_spend + weekday_spend
    weekend_pct = (weekend_spend / total_spend * 100) if total_spend else 0

    peak_day = dow.loc[dow["Transactions"].idxmax(), "Day"] if not dow.empty else "--"

    # Day-of-month insights
    early_avg = dom.iloc[0]["Avg Ticket"] if not dom.empty else 0
    late_avg = dom.iloc[-1]["Avg Ticket"] if not dom.empty else 0
    early_pct = dom.iloc[0]["% of Spend"] if not dom.empty else 0
    peak_period = dom.loc[dom["Transactions"].idxmax(), "Period"] if not dom.empty else "--"

    # Auto-detect busiest day/time
    if not heat_txns.empty:
        max_val = heat_txns.values.max()
        peak_wom_idx, peak_dow_idx = divmod(heat_txns.values.argmax(), len(_DAY_ORDER))
        peak_combo = f"{_WOM_LABELS[peak_wom_idx]} {_DAY_ORDER[peak_dow_idx]}"
    else:
        peak_combo = "--"
        max_val = 0

    meta = {
        "sheet_name": "M16 Time Patterns",
        "peak_day": peak_day,
        "peak_period": peak_period,
        "peak_wom_dow": peak_combo,
        "weekend_spend_pct": round(weekend_pct, 1),
        "weekend_avg_ticket": round(weekend_txns.mean(), 2) if len(weekend_txns) else 0,
        "weekday_avg_ticket": round(weekday_txns.mean(), 2) if len(weekday_txns) else 0,
        "early_month_avg_ticket": round(float(early_avg), 2),
        "late_month_avg_ticket": round(float(late_avg), 2),
        "early_month_spend_pct": round(float(early_pct), 1),
    }

    data: dict[str, pd.DataFrame] = {"main": dow}
    if not dom.empty:
        data["day_of_month"] = dom
    if not heat_txns.empty:
        data["wom_dow_heatmap"] = heat_txns.reset_index()

    summary_parts = [
        f"Peak day: {peak_day}",
        f"Weekend spend: {weekend_pct:.1f}% of total",
        f"Early month (Days 1-7) avg ticket: ${early_avg:.2f} vs "
        f"late month (Days 22-31): ${late_avg:.2f}",
        f"Busiest slot: {peak_combo} ({int(max_val):,} txns)",
    ]

    return AnalysisResult(
        name="time_patterns",
        title="Transaction Timing Patterns",
        data=data,
        metadata=meta,
        summary=". ".join(summary_parts),
    )
