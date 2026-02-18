"""Reusable aggregation templates shared by M1, M3, M4."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import add_grand_total, safe_percentage


def top_merchants_summary(
    df: pd.DataFrame,
    sort_col: str,
    top_n: int = 50,
    group_col: str = "merchant_consolidated",
    ic_rate: float = 0.0,
) -> pd.DataFrame:
    """Group by merchant, aggregate, sort, top-N, add percentages + Grand Total.

    Returns a reset-index DataFrame with columns:
      merchant_consolidated, total_amount, transaction_count, avg_transaction,
      unique_accounts, pct_of_total_amount, pct_of_total_transactions
      [+ estimated_ic_revenue if ic_rate > 0]
    """
    if df.empty:
        cols = [
            group_col,
            "total_amount",
            "transaction_count",
            "avg_transaction",
            "unique_accounts",
            "pct_of_total_amount",
            "pct_of_total_transactions",
        ]
        if ic_rate > 0:
            cols.append("estimated_ic_revenue")
        return pd.DataFrame(columns=cols)

    agg = df.groupby(group_col).agg(
        total_amount=("amount", "sum"),
        transaction_count=("amount", "count"),
        avg_transaction=("amount", "mean"),
        unique_accounts=("primary_account_num", "nunique"),
    )

    result = agg.sort_values(sort_col, ascending=False).head(top_n).reset_index()
    result = result.round(2)

    total_amount = df["amount"].sum()
    total_transactions = len(df)
    result["pct_of_total_amount"] = result["total_amount"].apply(
        lambda x: safe_percentage(x, total_amount)
    )
    result["pct_of_total_transactions"] = result["transaction_count"].apply(
        lambda x: safe_percentage(x, total_transactions)
    )

    if ic_rate > 0:
        result["estimated_ic_revenue"] = (result["total_amount"] * ic_rate).round(2)

    return add_grand_total(result, group_col)


def top_mcc_summary(
    df: pd.DataFrame,
    sort_col: str,
    top_n: int = 50,
    group_col: str = "mcc_code",
    ic_rate: float = 0.0,
) -> pd.DataFrame:
    """Group by MCC code, aggregate, sort, top-N, add Grand Total.

    Returns a reset-index DataFrame with columns:
      mcc_code, total_amount, transaction_count, avg_transaction,
      unique_accounts, num_merchants [+ estimated_ic_revenue if ic_rate > 0]
    """
    if df.empty or group_col not in df.columns:
        cols = [
            group_col,
            "total_amount",
            "transaction_count",
            "avg_transaction",
            "unique_accounts",
            "num_merchants",
        ]
        if ic_rate > 0:
            cols.append("estimated_ic_revenue")
        return pd.DataFrame(columns=cols)

    agg = df.groupby(group_col).agg(
        total_amount=("amount", "sum"),
        transaction_count=("amount", "count"),
        avg_transaction=("amount", "mean"),
        unique_accounts=("primary_account_num", "nunique"),
        num_merchants=("merchant_name", "nunique"),
    )

    result = agg.sort_values(sort_col, ascending=False).head(top_n).reset_index()
    result = result.round(2)

    if ic_rate > 0:
        result["estimated_ic_revenue"] = (result["total_amount"] * ic_rate).round(2)

    return add_grand_total(result, group_col)
