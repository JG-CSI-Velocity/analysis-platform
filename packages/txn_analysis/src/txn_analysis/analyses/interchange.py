"""M8: Interchange revenue estimation."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult, safe_percentage
from txn_analysis.settings import Settings


def analyze_interchange_summary(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Portfolio-level interchange revenue summary.

    Produces a single DataFrame with:
      - Total estimated interchange revenue
      - Revenue by segment (business/personal)
      - Top 10 merchants by estimated IC revenue
      - Top 10 MCC categories by estimated IC revenue
      - Monthly revenue trend

    Stores key metrics in context for downstream use by M9 scorecard.
    """
    ic_rate = settings.ic_rate
    if ic_rate <= 0 or df.empty:
        if context is not None:
            context["interchange_summary"] = {
                "total_ic_revenue": 0.0,
                "ic_rate": ic_rate,
            }
        return AnalysisResult.from_df(
            "interchange_summary",
            "Interchange Revenue Summary",
            pd.DataFrame(),
            sheet_name="M8 IC Summary",
            metadata={"ic_rate": ic_rate, "note": "IC rate not configured"},
        )

    total_spend = df["amount"].sum()
    total_ic = total_spend * ic_rate
    total_accounts = df["primary_account_num"].nunique()

    rows: list[dict] = []

    # --- Portfolio totals ---
    rows.append(
        {
            "section": "Portfolio",
            "item": "Total Estimated Interchange Revenue",
            "spend": round(total_spend, 2),
            "estimated_ic_revenue": round(total_ic, 2),
            "accounts": total_accounts,
            "pct_of_total": 100.0,
        }
    )

    # --- Segment split ---
    for label, seg_df in [("Business", business_df), ("Personal", personal_df)]:
        seg_spend = seg_df["amount"].sum()
        seg_ic = seg_spend * ic_rate
        rows.append(
            {
                "section": "Segment",
                "item": label,
                "spend": round(seg_spend, 2),
                "estimated_ic_revenue": round(seg_ic, 2),
                "accounts": seg_df["primary_account_num"].nunique(),
                "pct_of_total": safe_percentage(seg_ic, total_ic),
            }
        )

    # --- Top 10 merchants by IC revenue ---
    merchant_agg = (
        df.groupby("merchant_consolidated")
        .agg(spend=("amount", "sum"), accounts=("primary_account_num", "nunique"))
        .sort_values("spend", ascending=False)
        .head(10)
    )
    for merchant, row in merchant_agg.iterrows():
        merchant_ic = row["spend"] * ic_rate
        rows.append(
            {
                "section": "Top Merchants",
                "item": merchant,
                "spend": round(row["spend"], 2),
                "estimated_ic_revenue": round(merchant_ic, 2),
                "accounts": int(row["accounts"]),
                "pct_of_total": safe_percentage(merchant_ic, total_ic),
            }
        )

    # --- Top 10 MCC categories by IC revenue ---
    if "mcc_code" in df.columns:
        mcc_agg = (
            df.groupby("mcc_code")
            .agg(spend=("amount", "sum"), accounts=("primary_account_num", "nunique"))
            .sort_values("spend", ascending=False)
            .head(10)
        )
        for mcc, row in mcc_agg.iterrows():
            mcc_ic = row["spend"] * ic_rate
            rows.append(
                {
                    "section": "Top MCC",
                    "item": str(mcc),
                    "spend": round(row["spend"], 2),
                    "estimated_ic_revenue": round(mcc_ic, 2),
                    "accounts": int(row["accounts"]),
                    "pct_of_total": safe_percentage(mcc_ic, total_ic),
                }
            )

    # --- Monthly trend ---
    if "year_month" in df.columns:
        monthly = (
            df.groupby("year_month")
            .agg(spend=("amount", "sum"), accounts=("primary_account_num", "nunique"))
            .sort_index()
        )
        for ym, row in monthly.iterrows():
            monthly_ic = row["spend"] * ic_rate
            rows.append(
                {
                    "section": "Monthly",
                    "item": str(ym),
                    "spend": round(row["spend"], 2),
                    "estimated_ic_revenue": round(monthly_ic, 2),
                    "accounts": int(row["accounts"]),
                    "pct_of_total": safe_percentage(monthly_ic, total_ic),
                }
            )

    result = pd.DataFrame(rows)

    # Store summary in context for M9 scorecard
    if context is not None:
        monthly_spend = (
            df.groupby("year_month")["amount"].sum()
            if "year_month" in df.columns
            else pd.Series(dtype=float)
        )
        context["interchange_summary"] = {
            "total_ic_revenue": round(total_ic, 2),
            "total_spend": round(total_spend, 2),
            "ic_rate": ic_rate,
            "total_accounts": total_accounts,
            "monthly_spend": monthly_spend,
            "business_spend": round(business_df["amount"].sum(), 2),
            "personal_spend": round(personal_df["amount"].sum(), 2),
        }

    return AnalysisResult.from_df(
        "interchange_summary",
        "Interchange Revenue Summary (Estimated)",
        result,
        sheet_name="M8 IC Summary",
        metadata={
            "ic_rate": ic_rate,
            "total_ic_revenue": round(total_ic, 2),
            "note": f"Estimated using blended rate of {ic_rate:.4%}",
        },
    )
