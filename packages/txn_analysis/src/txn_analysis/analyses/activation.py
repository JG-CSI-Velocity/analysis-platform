"""M24: Activation curve, dormancy detection, and reactivation tracking.

Measures how quickly accounts start transacting after opening (or after mailer),
identifies dormant accounts (no transactions in 30/60/90 day windows),
and tracks reactivation of previously dormant accounts.

Requires ODD data in context["odd_df"] for account open dates and mailer dates.

Executive presentation: Headlines are conclusions, not labels.
"""

from __future__ import annotations

import logging

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)

# Dormancy windows in days
_DORMANCY_WINDOWS = [30, 60, 90]

# Activation time buckets (days)
_ACTIVATION_BUCKETS = [
    (0, 7, "0-7 days"),
    (8, 14, "8-14 days"),
    (15, 30, "15-30 days"),
    (31, 60, "31-60 days"),
    (61, 90, "61-90 days"),
    (91, 180, "91-180 days"),
    (181, 365, "181-365 days"),
    (366, 99999, "365+ days"),
]


def _detect_acct_col(odd_df: pd.DataFrame) -> str | None:
    for col in ("Acct Number", "Account Number", "Account_Number"):
        if col in odd_df.columns:
            return col
    return None


# ---------------------------------------------------------------------------
# M24.1 -- Activation Curve
# ---------------------------------------------------------------------------


def _compute_activation(
    txn_df: pd.DataFrame, odd_df: pd.DataFrame, acct_col: str
) -> pd.DataFrame:
    """Compute days from account open to first transaction per account.

    Returns DataFrame with columns: account, date_opened, first_txn_date, days_to_activation, bucket.
    """
    if "Date Opened" not in odd_df.columns:
        return pd.DataFrame()

    # Get Date Opened per account
    acct_opened = odd_df[[acct_col, "Date Opened"]].dropna(subset=["Date Opened"]).copy()
    acct_opened[acct_col] = acct_opened[acct_col].astype(str).str.strip()
    acct_opened["Date Opened"] = pd.to_datetime(
        acct_opened["Date Opened"], errors="coerce", format="mixed"
    )
    acct_opened = acct_opened.dropna(subset=["Date Opened"])

    # Get first transaction date per account
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce", format="mixed")
    work = txn_df[dt.notna()].copy()
    work["txn_date"] = dt[dt.notna()]
    work["acct_str"] = work["primary_account_num"].astype(str).str.strip()

    first_txn = work.groupby("acct_str")["txn_date"].min().reset_index()
    first_txn.rename(columns={"acct_str": "account", "txn_date": "first_txn_date"}, inplace=True)

    # Merge
    merged = acct_opened.merge(
        first_txn, left_on=acct_col, right_on="account", how="inner"
    )
    if merged.empty:
        return pd.DataFrame()

    merged["days_to_activation"] = (merged["first_txn_date"] - merged["Date Opened"]).dt.days
    # Only include positive activation times (first txn after account open)
    merged = merged[merged["days_to_activation"] >= 0]

    def _bucket(days: int) -> str:
        for lo, hi, label in _ACTIVATION_BUCKETS:
            if lo <= days <= hi:
                return label
        return "365+ days"

    merged["bucket"] = merged["days_to_activation"].apply(_bucket)
    return merged[["account", "Date Opened", "first_txn_date", "days_to_activation", "bucket"]]


def _build_activation_summary(activation: pd.DataFrame) -> pd.DataFrame:
    """Summarize activation by time bucket."""
    if activation.empty:
        return pd.DataFrame()

    bucket_order = [b[2] for b in _ACTIVATION_BUCKETS]
    summary = (
        activation.groupby("bucket")
        .agg(accounts=("account", "count"))
        .reindex(bucket_order)
        .fillna(0)
        .reset_index()
    )
    summary["accounts"] = summary["accounts"].astype(int)
    total = summary["accounts"].sum()
    summary["pct"] = (summary["accounts"] / total * 100).round(1) if total else 0
    summary["cumulative_pct"] = summary["pct"].cumsum().round(1)

    summary.columns = ["Activation Window", "Accounts", "% of Total", "Cumulative %"]
    return summary


# ---------------------------------------------------------------------------
# M24.2 -- Dormancy Detection
# ---------------------------------------------------------------------------


def _compute_dormancy(txn_df: pd.DataFrame) -> pd.DataFrame:
    """Classify accounts by dormancy status based on days since last transaction.

    Returns DataFrame with columns: account, last_txn_date, days_since, status.
    """
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce", format="mixed")
    work = txn_df[dt.notna()].copy()
    work["txn_date"] = dt[dt.notna()]
    work["acct_str"] = work["primary_account_num"].astype(str).str.strip()

    if work.empty:
        return pd.DataFrame()

    anchor = work["txn_date"].max()

    last_txn = work.groupby("acct_str")["txn_date"].max().reset_index()
    last_txn.rename(columns={"acct_str": "account", "txn_date": "last_txn_date"}, inplace=True)
    last_txn["days_since"] = (anchor - last_txn["last_txn_date"]).dt.days

    def _status(days: int) -> str:
        if days <= _DORMANCY_WINDOWS[0]:
            return "Active"
        if days <= _DORMANCY_WINDOWS[1]:
            return "At-Risk"
        if days <= _DORMANCY_WINDOWS[2]:
            return "Dormant"
        return "Lost"

    last_txn["status"] = last_txn["days_since"].apply(_status)
    return last_txn


def _build_dormancy_summary(dormancy: pd.DataFrame) -> pd.DataFrame:
    """Summarize dormancy status distribution."""
    if dormancy.empty:
        return pd.DataFrame()

    status_order = ["Active", "At-Risk", "Dormant", "Lost"]
    summary = (
        dormancy.groupby("status")
        .agg(
            accounts=("account", "count"),
            avg_days_since=("days_since", "mean"),
        )
        .reindex(status_order)
        .fillna(0)
        .reset_index()
    )
    summary["accounts"] = summary["accounts"].astype(int)
    total = summary["accounts"].sum()
    summary["pct"] = (summary["accounts"] / total * 100).round(1) if total else 0
    summary["avg_days_since"] = summary["avg_days_since"].round(0)

    summary.columns = ["Status", "Accounts", "Avg Days Since Last Txn", "% of Total"]
    return summary


# ---------------------------------------------------------------------------
# M24.3 -- Reactivation Tracking
# ---------------------------------------------------------------------------


def _compute_reactivation(txn_df: pd.DataFrame) -> pd.DataFrame:
    """Track monthly flow between active/dormant states.

    For each month, count accounts that were dormant in the prior month
    but transacted in the current month (reactivated).
    """
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce", format="mixed")
    work = txn_df[dt.notna()].copy()
    work["txn_date"] = dt[dt.notna()]
    work["year_month"] = work["txn_date"].dt.to_period("M")
    work["acct_str"] = work["primary_account_num"].astype(str).str.strip()

    if work.empty:
        return pd.DataFrame()

    # Get unique accounts per month
    monthly_accts = work.groupby("year_month")["acct_str"].apply(set).sort_index()
    if len(monthly_accts) < 2:
        return pd.DataFrame()

    months = sorted(monthly_accts.index)
    all_seen: set[str] = set()
    rows: list[dict] = []

    for i, m in enumerate(months):
        current = monthly_accts[m]
        if i == 0:
            all_seen = current.copy()
            rows.append(
                {
                    "Month": str(m),
                    "Active": len(current),
                    "New": len(current),
                    "Reactivated": 0,
                    "Went Dormant": 0,
                }
            )
            continue

        prev = monthly_accts[months[i - 1]]
        reactivated = current & (all_seen - prev)
        new = current - all_seen
        went_dormant = prev - current

        all_seen |= current

        rows.append(
            {
                "Month": str(m),
                "Active": len(current),
                "New": len(new),
                "Reactivated": len(reactivated),
                "Went Dormant": len(went_dormant),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_activation(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Analyze activation speed, dormancy, and reactivation patterns.

    Uses ODD for account open dates; TXN for transaction timing.
    """
    ctx = context or {}
    odd_df = ctx.get("odd_df")
    data: dict[str, pd.DataFrame] = {}
    summary_parts: list[str] = []

    # M24.2 -- Dormancy (always available, pure TXN)
    dormancy = _compute_dormancy(df)
    if not dormancy.empty:
        dormancy_summary = _build_dormancy_summary(dormancy)
        if not dormancy_summary.empty:
            data["dormancy"] = dormancy_summary
            active_row = dormancy_summary[dormancy_summary["Status"] == "Active"]
            if not active_row.empty:
                active_pct = active_row.iloc[0]["% of Total"]
                summary_parts.append(f"{active_pct:.0f}% of accounts active (txn in last 30 days)")
            at_risk_row = dormancy_summary[dormancy_summary["Status"] == "At-Risk"]
            dormant_row = dormancy_summary[dormancy_summary["Status"] == "Dormant"]
            at_risk_n = int(at_risk_row.iloc[0]["Accounts"]) if not at_risk_row.empty else 0
            dormant_n = int(dormant_row.iloc[0]["Accounts"]) if not dormant_row.empty else 0
            if at_risk_n + dormant_n > 0:
                summary_parts.append(
                    f"{at_risk_n + dormant_n:,} accounts at-risk or dormant -- reactivation opportunity"
                )

    # M24.3 -- Reactivation
    reactivation = _compute_reactivation(df)
    if not reactivation.empty:
        data["reactivation"] = reactivation
        total_reactivated = reactivation["Reactivated"].sum()
        if total_reactivated > 0:
            summary_parts.append(f"{total_reactivated:,} accounts reactivated across all months")

    # M24.1 -- Activation (requires ODD)
    if odd_df is not None and not odd_df.empty:
        acct_col = _detect_acct_col(odd_df)
        if acct_col:
            activation = _compute_activation(df, odd_df, acct_col)
            if not activation.empty:
                activation_summary = _build_activation_summary(activation)
                if not activation_summary.empty:
                    data["activation"] = activation_summary

                    median_days = activation["days_to_activation"].median()
                    pct_7d = len(activation[activation["days_to_activation"] <= 7]) / len(
                        activation
                    ) * 100
                    summary_parts.insert(
                        0,
                        f"Median activation: {median_days:.0f} days -- "
                        f"{pct_7d:.0f}% activated within first week",
                    )

    if not data:
        return AnalysisResult.from_df(
            "activation",
            "Activation & Dormancy Analysis",
            pd.DataFrame({"Note": ["Insufficient data for activation analysis"]}),
            metadata={"sheet_name": "M24 Activation", "chart_id": "M24"},
        )

    # Use dormancy as main (always available) or activation if present
    main_key = "activation" if "activation" in data else "dormancy"

    # Executive headline
    headline = "Activation & Dormancy Analysis"
    if "activation" in data:
        median_days = (
            data["activation"]["Cumulative %"]
            .loc[data["activation"]["Cumulative %"] >= 50]
            .index[0]
            if not data["activation"].empty
            else None
        )
        if dormancy is not None and not dormancy.empty:
            active_count = len(dormancy[dormancy["status"] == "Active"])
            total = len(dormancy)
            headline = (
                f"{active_count:,} of {total:,} accounts active -- "
                f"{len(dormancy[dormancy['status'].isin(['At-Risk', 'Dormant'])])}"
                f" need reactivation"
            )

    meta = {
        "sheet_name": "M24 Activation",
        "chart_id": "M24",
        "category": "Engagement Intelligence",
    }

    return AnalysisResult(
        name="activation",
        title=headline,
        data={"main": data[main_key], **{k: v for k, v in data.items() if k != main_key}},
        metadata=meta,
        summary=". ".join(summary_parts),
    )
