"""M10: Simplified member segmentation by spend tier."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult, safe_percentage
from txn_analysis.settings import Settings


def analyze_member_segments(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Classify accounts into spend tiers: High Value, Active, Low Activity, Dormant.

    Uses a waterfall priority: Dormant (90+ days since last txn) first,
    then spend-based tiers using quartile thresholds on total spend.

    Stores segment counts in context for M9 scorecard.
    """
    if df.empty or "primary_account_num" not in df.columns:
        return _empty_result()

    # Build per-account summary (flat output -- no account-by-merchant pivot)
    acct = (
        df.groupby("primary_account_num")
        .agg(
            total_spend=("amount", "sum"),
            txn_count=("amount", "count"),
            avg_txn=("amount", "mean"),
        )
        .reset_index()
    )

    # Recency: days since last transaction, anchored to dataset max date
    if "transaction_date" in df.columns:
        dt = pd.to_datetime(df["transaction_date"], errors="coerce")
        max_date = dt.max()
        last_txn = dt.groupby(df["primary_account_num"]).max()
        acct = acct.set_index("primary_account_num")
        acct["days_since_last_txn"] = (max_date - last_txn).dt.days
        acct = acct.reset_index()
    else:
        acct["days_since_last_txn"] = 0

    # Waterfall classification
    dormant_threshold = 90
    acct["segment"] = _classify_accounts(acct, dormant_threshold)

    # Aggregate by segment
    seg_summary = (
        acct.groupby("segment")
        .agg(
            account_count=("primary_account_num", "count"),
            total_spend=("total_spend", "sum"),
            avg_spend=("total_spend", "mean"),
            avg_txn_count=("txn_count", "mean"),
            avg_days_since_last=("days_since_last_txn", "mean"),
        )
        .reset_index()
    )

    total_accounts = len(acct)
    total_spend = acct["total_spend"].sum()
    ic_rate = settings.ic_rate

    seg_summary["pct_of_accounts"] = seg_summary["account_count"].apply(
        lambda x: safe_percentage(x, total_accounts)
    )
    seg_summary["pct_of_spend"] = seg_summary["total_spend"].apply(
        lambda x: safe_percentage(x, total_spend)
    )
    if ic_rate > 0:
        seg_summary["estimated_ic_revenue"] = (seg_summary["total_spend"] * ic_rate).round(2)

    seg_summary = seg_summary.round(2)

    # Order segments meaningfully
    seg_order = ["High Value", "Active", "Low Activity", "Dormant"]
    seg_summary["_sort"] = seg_summary["segment"].map({s: i for i, s in enumerate(seg_order)})
    seg_summary = seg_summary.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    # Store in context for M9 scorecard
    if context is not None:
        context["member_segments"] = {
            "total_accounts": total_accounts,
            "segment_counts": dict(zip(seg_summary["segment"], seg_summary["account_count"])),
            "dormant_count": int(
                seg_summary.loc[seg_summary["segment"] == "Dormant", "account_count"].sum()
            ),
        }

    return AnalysisResult.from_df(
        "member_segments",
        "Account Segmentation by Spend Tier",
        seg_summary,
        sheet_name="M10 Segments",
        metadata={"dormant_threshold_days": dormant_threshold},
    )


def _classify_accounts(acct: pd.DataFrame, dormant_days: int) -> pd.Series:
    """Waterfall: Dormant > High Value > Active > Low Activity."""
    segments = pd.Series("Low Activity", index=acct.index)

    # Spend quartile thresholds (among non-dormant accounts)
    active_mask = acct["days_since_last_txn"] < dormant_days
    if active_mask.any():
        active_spend = acct.loc[active_mask, "total_spend"]
        q75 = active_spend.quantile(0.75)
        q25 = active_spend.quantile(0.25)

        segments[active_mask & (acct["total_spend"] >= q75)] = "High Value"
        segments[active_mask & (acct["total_spend"] >= q25) & (acct["total_spend"] < q75)] = (
            "Active"
        )
        segments[active_mask & (acct["total_spend"] < q25)] = "Low Activity"

    # Dormant overrides everything
    segments[acct["days_since_last_txn"] >= dormant_days] = "Dormant"

    return segments


def _empty_result() -> AnalysisResult:
    return AnalysisResult.from_df(
        "member_segments",
        "Account Segmentation by Spend Tier",
        pd.DataFrame(),
        sheet_name="M10 Segments",
    )
