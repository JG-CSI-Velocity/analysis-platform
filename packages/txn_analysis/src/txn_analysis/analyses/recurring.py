"""M15: Recurring payment detection and analysis.

Identifies subscription/recurring merchants by detecting accounts
with consistent monthly transactions to the same merchant.
Shows stickiness and primary FI indicators.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

# Minimum months a merchant must appear for an account to be "recurring"
_MIN_RECURRING_MONTHS = 3


def analyze_recurring_payments(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Detect recurring merchants and summarize subscription stickiness.

    A merchant is "recurring" for an account if that account transacted
    with the merchant in >= _MIN_RECURRING_MONTHS distinct months.
    """
    if "year_month" not in df.columns or "merchant_consolidated" not in df.columns:
        return AnalysisResult.from_df(
            "recurring_payments",
            "Recurring Payment Detection",
            pd.DataFrame(),
            error="Missing year_month or merchant_consolidated column",
        )

    # Build account-merchant-month matrix
    acct_merch = (
        df.groupby(["primary_account_num", "merchant_consolidated"])["year_month"]
        .nunique()
        .reset_index(name="months_active")
    )

    # Filter to recurring relationships
    recurring = acct_merch[acct_merch["months_active"] >= _MIN_RECURRING_MONTHS]

    if recurring.empty:
        return AnalysisResult.from_df(
            "recurring_payments",
            "Recurring Payment Detection",
            pd.DataFrame({"Note": ["No recurring merchants detected"]}),
            metadata={"recurring_count": 0},
        )

    # Summarize by merchant
    merchant_summary = (
        recurring.groupby("merchant_consolidated")
        .agg(
            recurring_accounts=("primary_account_num", "nunique"),
            avg_months=("months_active", "mean"),
            max_months=("months_active", "max"),
        )
        .reset_index()
        .sort_values("recurring_accounts", ascending=False)
        .head(settings.top_n)
    )

    # Add spend data
    spend_by_merchant = (
        df[df["merchant_consolidated"].isin(merchant_summary["merchant_consolidated"])]
        .groupby("merchant_consolidated")["amount"]
        .agg(total_spend="sum", avg_txn="mean")
        .reset_index()
    )

    result = merchant_summary.merge(spend_by_merchant, on="merchant_consolidated", how="left")
    result["avg_months"] = result["avg_months"].round(1)
    result["avg_txn"] = result["avg_txn"].round(2)
    result["total_spend"] = result["total_spend"].round(2)

    result.columns = [
        "Merchant",
        "Recurring Accounts",
        "Avg Months Active",
        "Max Months",
        "Total Spend",
        "Avg Transaction",
    ]

    total_recurring_accts = recurring["primary_account_num"].nunique()
    total_accts = df["primary_account_num"].nunique()
    pct = (total_recurring_accts / total_accts * 100) if total_accts else 0

    meta = {
        "sheet_name": "M15 Recurring",
        "recurring_merchants": len(result),
        "recurring_accounts": total_recurring_accts,
        "recurring_pct": round(pct, 1),
    }
    return AnalysisResult(
        name="recurring_payments",
        title="Recurring Payment Detection",
        data={"main": result},
        metadata=meta,
        summary=(
            f"{total_recurring_accts:,} accounts ({pct:.1f}%) have recurring "
            f"relationships with {len(result)} merchants"
        ),
    )
