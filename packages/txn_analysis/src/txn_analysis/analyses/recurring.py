"""M15: Recurring payment detection and new-onset tracking.

Identifies subscription/recurring merchants by detecting accounts
with consistent monthly transactions to the same merchant.
Tracks when each recurring relationship first crosses the threshold
("new onset") so CSMs can see when new subscriptions appear.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

# Minimum months a merchant must appear for an account to be "recurring"
_MIN_RECURRING_MONTHS = 3


def _build_onset_timeline(
    df: pd.DataFrame,
    min_months: int,
) -> pd.DataFrame:
    """Track when each account-merchant pair first becomes recurring.

    For each account-merchant pair, finds the N-th distinct month (sorted
    chronologically) where N = *min_months*. That month is the "onset" --
    when the relationship first qualifies as recurring.

    Returns a DataFrame with columns:
      primary_account_num, merchant_consolidated, onset_month, cumulative_months
    """
    _cols = ["primary_account_num", "merchant_consolidated", "onset_month", "cumulative_months"]

    # Deduplicate to one row per account-merchant-month, then sort
    unique_months = (
        df[["primary_account_num", "merchant_consolidated", "year_month"]]
        .drop_duplicates()
        .sort_values("year_month")
    )

    # Assign cumulative month count within each pair (0-indexed)
    unique_months["month_rank"] = unique_months.groupby(
        ["primary_account_num", "merchant_consolidated"]
    ).cumcount()

    # Total months per pair
    pair_counts = (
        unique_months.groupby(["primary_account_num", "merchant_consolidated"])
        .size()
        .reset_index(name="cumulative_months")
    )
    qualifying = pair_counts[pair_counts["cumulative_months"] >= min_months]

    if qualifying.empty:
        return pd.DataFrame(columns=_cols)

    # The onset month is the row where month_rank == min_months - 1
    onset_rows = unique_months[unique_months["month_rank"] == min_months - 1][
        ["primary_account_num", "merchant_consolidated", "year_month"]
    ].rename(columns={"year_month": "onset_month"})

    result = qualifying.merge(
        onset_rows, on=["primary_account_num", "merchant_consolidated"], how="inner"
    )
    return result[_cols]


def _summarize_onsets_by_month(
    onsets: pd.DataFrame,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate onset data by month: how many new recurring relationships started."""
    if onsets.empty:
        return pd.DataFrame(
            columns=[
                "Month",
                "New Recurring Relationships",
                "New Recurring Accounts",
                "Top New Merchant",
                "Spend at Onset",
            ]
        )

    # Count new recurring relationships per onset month
    by_month = (
        onsets.groupby("onset_month")
        .agg(
            new_relationships=("merchant_consolidated", "count"),
            new_accounts=("primary_account_num", "nunique"),
            top_merchant=("merchant_consolidated", lambda s: s.value_counts().index[0]),
        )
        .reset_index()
        .sort_values("onset_month")
    )

    # Add spend in the onset month for those account-merchant pairs
    # Merge onsets with transactions on (account, merchant, month) for efficiency
    onset_txns = onsets.rename(columns={"onset_month": "year_month"}).merge(
        df[["primary_account_num", "merchant_consolidated", "year_month", "amount"]],
        on=["primary_account_num", "merchant_consolidated", "year_month"],
        how="inner",
    )
    onset_spend = (
        onset_txns.groupby("year_month")["amount"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"year_month": "onset_month", "amount": "onset_spend"})
    )
    by_month = by_month.merge(onset_spend, on="onset_month", how="left")
    by_month["onset_spend"] = by_month["onset_spend"].fillna(0)

    by_month.columns = [
        "Month",
        "New Recurring Relationships",
        "New Recurring Accounts",
        "Top New Merchant",
        "Spend at Onset",
    ]
    return by_month


def analyze_recurring_payments(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Detect recurring merchants and track when new recurring relationships start.

    A merchant is "recurring" for an account if that account transacted
    with the merchant in >= _MIN_RECURRING_MONTHS distinct months.

    Returns two data sheets:
      - main: Top recurring merchants by account count + spend
      - onsets: New recurring relationships by month (when they first appear)
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

    # --- Sheet 1: Top recurring merchants ---
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

    spend_by_merchant = (
        df[df["merchant_consolidated"].isin(merchant_summary["merchant_consolidated"])]
        .groupby("merchant_consolidated")["amount"]
        .agg(total_spend="sum", avg_txn="mean")
        .reset_index()
    )

    main_result = merchant_summary.merge(spend_by_merchant, on="merchant_consolidated", how="left")
    main_result["avg_months"] = main_result["avg_months"].round(1)
    main_result["avg_txn"] = main_result["avg_txn"].round(2)
    main_result["total_spend"] = main_result["total_spend"].round(2)
    main_result.columns = [
        "Merchant",
        "Recurring Accounts",
        "Avg Months Active",
        "Max Months",
        "Total Spend",
        "Avg Transaction",
    ]

    # --- Sheet 2: New recurring onsets by month ---
    onsets = _build_onset_timeline(df, _MIN_RECURRING_MONTHS)
    onset_summary = _summarize_onsets_by_month(onsets, df)

    total_recurring_accts = recurring["primary_account_num"].nunique()
    total_accts = df["primary_account_num"].nunique()
    pct = (total_recurring_accts / total_accts * 100) if total_accts else 0

    # Build summary text
    summary_parts = [
        f"{total_recurring_accts:,} accounts ({pct:.1f}%) have recurring "
        f"relationships with {len(main_result)} merchants"
    ]
    if not onset_summary.empty:
        latest = onset_summary.iloc[-1]
        summary_parts.append(
            f"Most recent month: {latest['New Recurring Relationships']} "
            f"new recurring relationships started in {latest['Month']}"
        )

    # Store onset data in context for downstream analyses (scorecard)
    if context is not None:
        context["recurring_onsets"] = {
            "total_recurring_accounts": total_recurring_accts,
            "total_recurring_pct": round(pct, 1),
            "onset_months": len(onset_summary),
        }

    meta = {
        "sheet_name": "M15 Recurring",
        "recurring_merchants": len(main_result),
        "recurring_accounts": total_recurring_accts,
        "recurring_pct": round(pct, 1),
        "onset_count": len(onsets),
    }

    data: dict[str, pd.DataFrame] = {"main": main_result}
    if not onset_summary.empty:
        data["onsets"] = onset_summary

    return AnalysisResult(
        name="recurring_payments",
        title="Recurring Payment Detection",
        data=data,
        metadata=meta,
        summary=". ".join(summary_parts),
    )
