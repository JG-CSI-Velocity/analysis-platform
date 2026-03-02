"""M26: Merchant loyalty metrics -- repeat rate, HHI diversity, new merchant exploration.

Computes per-account merchant loyalty indicators:
  - Repeat merchant rate: % of unique merchants visited 3+ times
  - HHI (Herfindahl-Hirschman Index): merchant spend concentration (0=diverse, 1=single merchant)
  - New merchant exploration: monthly count of first-time merchants
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import SEGMENT_ORDER, merge_segments_to_txn
from txn_analysis.settings import Settings

_REPEAT_THRESHOLD = 3  # visits to count as "repeat merchant"


def _compute_repeat_rate(acct_df: pd.DataFrame) -> float:
    """% of unique merchants visited >= _REPEAT_THRESHOLD times."""
    merch_counts = acct_df["merchant_consolidated"].value_counts()
    if merch_counts.empty:
        return 0.0
    repeat = (merch_counts >= _REPEAT_THRESHOLD).sum()
    return round(repeat / len(merch_counts) * 100, 1)


def _compute_hhi(acct_df: pd.DataFrame) -> float:
    """Herfindahl-Hirschman Index of merchant spend concentration.

    0 = perfectly diverse, 1 = all spend at one merchant.
    """
    if acct_df.empty or "amount" not in acct_df.columns:
        return 0.0
    merch_spend = acct_df.groupby("merchant_consolidated")["amount"].sum()
    total = merch_spend.sum()
    if total == 0:
        return 0.0
    shares = merch_spend / total
    return round(float((shares**2).sum()), 4)


def analyze_merchant_loyalty(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Compute merchant loyalty metrics across all accounts."""
    merch_col = "merchant_consolidated" if "merchant_consolidated" in df.columns else None
    if merch_col is None:
        merch_col = "merchant_name" if "merchant_name" in df.columns else None

    if merch_col is None or df.empty:
        return AnalysisResult.from_df(
            "merchant_loyalty",
            "Merchant Loyalty Analysis",
            pd.DataFrame(),
            error="No merchant or transaction data available",
        )

    # Normalise to merchant_consolidated for internal use
    work = df.copy()
    if "merchant_consolidated" not in work.columns:
        work["merchant_consolidated"] = work[merch_col]

    # --- Sheet 1: Per-account repeat rate and HHI ---
    acct_rows: list[dict] = []
    for acct, grp in work.groupby("primary_account_num"):
        acct_rows.append(
            {
                "Account": acct,
                "Total Txns": len(grp),
                "Unique Merchants": grp["merchant_consolidated"].nunique(),
                "Repeat Rate %": _compute_repeat_rate(grp),
                "HHI": _compute_hhi(grp),
            }
        )
    acct_df = pd.DataFrame(acct_rows)

    # Summary stats
    summary_df = pd.DataFrame(
        [
            {
                "Metric": "Accounts Analyzed",
                "Value": len(acct_df),
            },
            {
                "Metric": "Avg Repeat Rate %",
                "Value": round(acct_df["Repeat Rate %"].mean(), 1) if not acct_df.empty else 0,
            },
            {
                "Metric": "Median Repeat Rate %",
                "Value": round(acct_df["Repeat Rate %"].median(), 1) if not acct_df.empty else 0,
            },
            {
                "Metric": "Avg HHI",
                "Value": round(acct_df["HHI"].mean(), 4) if not acct_df.empty else 0,
            },
            {
                "Metric": "Median HHI",
                "Value": round(acct_df["HHI"].median(), 4) if not acct_df.empty else 0,
            },
            {
                "Metric": "Avg Unique Merchants",
                "Value": round(acct_df["Unique Merchants"].mean(), 1) if not acct_df.empty else 0,
            },
        ]
    )

    # --- Sheet 2: New merchant exploration (monthly first-time merchants) ---
    new_merch_df = pd.DataFrame()
    if "transaction_date" in work.columns:
        dt = pd.to_datetime(work["transaction_date"], errors="coerce", format="mixed")
        valid = dt.notna()
        if valid.sum() > 0:
            explore = work[valid].copy()
            explore["txn_month"] = dt[valid].dt.to_period("M").astype(str)
            # For each account, track first occurrence of each merchant
            explore = explore.sort_values("transaction_date")
            explore["first_visit"] = ~explore.duplicated(
                subset=["primary_account_num", "merchant_consolidated"], keep="first"
            )
            new_by_month = (
                explore[explore["first_visit"]]
                .groupby("txn_month")
                .agg(
                    new_merchants=("merchant_consolidated", "nunique"),
                    new_visits=("first_visit", "sum"),
                    unique_accounts=("primary_account_num", "nunique"),
                )
                .reset_index()
            )
            new_by_month.columns = [
                "Month",
                "New Merchants",
                "First Visits",
                "Active Accounts",
            ]
            new_merch_df = new_by_month

    # --- Sheet 3: By-segment breakdown (if ODD available) ---
    segment_df = pd.DataFrame()
    ctx = context or {}
    odd_df = ctx.get("odd_df")
    if odd_df is not None and isinstance(odd_df, pd.DataFrame) and not odd_df.empty:
        merged = merge_segments_to_txn(work, odd_df)
        known = merged[merged["ars_segment"] != "Unknown"]
        if not known.empty:
            seg_rows: list[dict] = []
            for seg in SEGMENT_ORDER:
                seg_data = known[known["ars_segment"] == seg]
                if seg_data.empty:
                    continue
                seg_acct_stats: list[float] = []
                seg_hhi_stats: list[float] = []
                for _acct, grp in seg_data.groupby("primary_account_num"):
                    seg_acct_stats.append(_compute_repeat_rate(grp))
                    seg_hhi_stats.append(_compute_hhi(grp))
                seg_rows.append(
                    {
                        "Segment": seg,
                        "Accounts": seg_data["primary_account_num"].nunique(),
                        "Avg Repeat Rate %": round(sum(seg_acct_stats) / len(seg_acct_stats), 1)
                        if seg_acct_stats
                        else 0,
                        "Avg HHI": round(sum(seg_hhi_stats) / len(seg_hhi_stats), 4)
                        if seg_hhi_stats
                        else 0,
                    }
                )
            segment_df = pd.DataFrame(seg_rows)

    # Build result
    data: dict[str, pd.DataFrame] = {"main": summary_df}
    if not acct_df.empty:
        data["account_detail"] = acct_df
    if not new_merch_df.empty:
        data["new_merchants"] = new_merch_df
    if not segment_df.empty:
        data["by_segment"] = segment_df

    meta: dict = {
        "sheet_name": "M26 Merchant Loyalty",
        "category": "Merchant Intelligence",
        "chart_id": "M26",
    }
    if not acct_df.empty:
        meta["avg_repeat_rate"] = round(acct_df["Repeat Rate %"].mean(), 1)
        meta["avg_hhi"] = round(acct_df["HHI"].mean(), 4)
        meta["avg_unique_merchants"] = round(acct_df["Unique Merchants"].mean(), 1)

    summary_parts: list[str] = []
    if not acct_df.empty:
        avg_rr = acct_df["Repeat Rate %"].mean()
        avg_hhi = acct_df["HHI"].mean()
        summary_parts.append(f"Avg repeat rate: {avg_rr:.1f}%")
        hhi_label = "concentrated" if avg_hhi > 0.25 else "moderately diverse" if avg_hhi > 0.1 else "diverse"
        summary_parts.append(f"Avg HHI: {avg_hhi:.3f} ({hhi_label})")
        summary_parts.append(f"Avg unique merchants: {acct_df['Unique Merchants'].mean():.0f}")
    if not new_merch_df.empty:
        total_new = new_merch_df["New Merchants"].sum()
        summary_parts.append(f"{total_new:,} new merchant relationships formed")

    return AnalysisResult(
        name="merchant_loyalty",
        title="Merchant Loyalty Analysis",
        data=data,
        metadata=meta,
        summary=". ".join(summary_parts) if summary_parts else "Merchant loyalty metrics",
    )
