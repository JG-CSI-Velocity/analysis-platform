"""M20: Spending segment profile -- Low / Medium / High tier classification.

Classifies accounts into tercile-based spending tiers and computes
summary statistics per tier.  When ODD is available, cross-tabulates
tier distribution against ARS segments (Responder/Non-Responder/Control).
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import (
    TIER_ORDER,
    classify_spending_tiers,
    merge_segments_to_txn,
)
from txn_analysis.settings import Settings


def analyze_spending_profile(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Classify accounts into spending tiers and profile each tier."""
    if df.empty or "amount" not in df.columns:
        return AnalysisResult.from_df(
            "spending_profile",
            "Spending Segment Profile",
            pd.DataFrame(),
            error="No transaction data available",
        )

    tiered = classify_spending_tiers(df)

    # Per-tier summary
    acct_stats = (
        tiered.groupby(["primary_account_num", "spending_tier"])
        .agg(total_spend=("amount", "sum"), txn_count=("amount", "count"))
        .reset_index()
    )

    rows: list[dict] = []
    for tier in TIER_ORDER:
        subset = acct_stats[acct_stats["spending_tier"] == tier]
        if subset.empty:
            continue
        # Top MCC for this tier's accounts
        tier_accts = set(subset["primary_account_num"])
        tier_txns = tiered[tiered["primary_account_num"].isin(tier_accts)]
        top_mcc = "N/A"
        if "mcc_description" in tier_txns.columns and not tier_txns.empty:
            top_mcc = tier_txns.groupby("mcc_description")["amount"].sum().idxmax()

        rows.append(
            {
                "Spending Tier": tier,
                "Accounts": len(subset),
                "Mean Spend": round(subset["total_spend"].mean(), 2),
                "Median Spend": round(subset["total_spend"].median(), 2),
                "Max Spend": round(subset["total_spend"].max(), 2),
                "Avg Txn Count": round(subset["txn_count"].mean(), 1),
                "Top Category": top_mcc,
            }
        )

    profile_df = pd.DataFrame(rows)

    # Cross-tab with ARS segments if ODD available
    ctx = context or {}
    odd_df = ctx.get("odd_df")
    data: dict[str, pd.DataFrame] = {"main": profile_df}

    if odd_df is not None and isinstance(odd_df, pd.DataFrame) and not odd_df.empty:
        merged = merge_segments_to_txn(tiered, odd_df)
        merged_known = merged[merged["ars_segment"] != "Unknown"]
        if not merged_known.empty:
            ct = (
                merged_known.groupby(["primary_account_num", "spending_tier", "ars_segment"])
                .size()
                .reset_index(name="count")
                .drop_duplicates(subset=["primary_account_num", "spending_tier", "ars_segment"])
            )
            crosstab = (
                ct.groupby(["spending_tier", "ars_segment"])
                .size()
                .unstack(fill_value=0)
                .reindex(index=TIER_ORDER)
                .fillna(0)
                .astype(int)
            )
            data["segment_crosstab"] = crosstab.reset_index()

    summary_parts = []
    if not profile_df.empty:
        total_accts = profile_df["Accounts"].sum()
        high = profile_df[profile_df["Spending Tier"] == "High Spender"]
        if not high.empty:
            pct = round(high["Accounts"].iloc[0] / total_accts * 100, 1) if total_accts else 0
            summary_parts.append(f"High Spenders: {pct}% of accounts")

    return AnalysisResult(
        name="spending_profile",
        title="Spending Segment Profile",
        data=data,
        metadata={
            "sheet_name": "M20 Profile",
            "category": "Spending Intelligence",
            "chart_id": "M20",
        },
        summary="; ".join(summary_parts) if summary_parts else "Spending tier classification",
    )
