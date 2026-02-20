"""Competitor account segmentation (Heavy/Balanced/CU-Focused)."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult, safe_percentage
from txn_analysis.settings import Settings


def analyze_competitor_segmentation(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Segment accounts by competitor spend percentage."""
    if not context:
        return _empty_result()

    comp_data = context.get("competitor_data", {})
    if not comp_data:
        return _empty_result()

    all_comp = pd.concat(comp_data.values(), ignore_index=True)

    # Total spend per account across all transactions
    account_total = df.groupby("primary_account_num")["amount"].sum().rename("total_spend")

    # Competitor spend per account
    comp_by_acct = (
        all_comp.groupby("primary_account_num")["amount"].sum().rename("competitor_spend")
    )

    merged = pd.DataFrame({"total_spend": account_total}).join(
        pd.DataFrame({"competitor_spend": comp_by_acct}), how="left"
    )
    merged["competitor_spend"] = merged["competitor_spend"].fillna(0)
    merged["competitor_pct"] = merged.apply(
        lambda r: safe_percentage(r["competitor_spend"], r["total_spend"]), axis=1
    )

    # Segment: Heavy >50%, Balanced 25-50%, CU-Focused <25%
    def _segment(pct: float) -> str:
        if pct > 50:
            return "Heavy Competitor (>50%)"
        if pct >= 25:
            return "Balanced (25-50%)"
        return "CU-Focused (<25%)"

    merged["segment"] = merged["competitor_pct"].apply(_segment)

    segment_summary = (
        merged.groupby("segment")
        .agg(
            account_count=("total_spend", "count"),
            total_spend=("total_spend", "sum"),
            competitor_spend=("competitor_spend", "sum"),
        )
        .round(2)
        .reset_index()
    )
    segment_summary["avg_competitor_pct"] = segment_summary.apply(
        lambda r: safe_percentage(r["competitor_spend"], r["total_spend"]), axis=1
    )

    return AnalysisResult.from_df(
        "competitor_segmentation",
        "Competitor Account Segmentation",
        segment_summary,
        sheet_name="M6 Segmentation",
    )


def _empty_result() -> AnalysisResult:
    return AnalysisResult.from_df(
        "competitor_segmentation",
        "Competitor Account Segmentation",
        pd.DataFrame(),
        sheet_name="M6 Segmentation",
    )
