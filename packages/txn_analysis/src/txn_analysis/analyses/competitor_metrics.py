"""M6B-1 thru M6B-5: Competitor metric analyses (read from shared context)."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult, safe_percentage
from txn_analysis.settings import Settings


def _get_context_data(context: dict | None) -> tuple[dict, pd.DataFrame]:
    """Extract competitor data from shared context; return empty defaults if missing."""
    if not context:
        return {}, pd.DataFrame()
    return context.get("competitor_data", {}), context.get("competitor_summary", pd.DataFrame())


def analyze_competitor_high_level(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """M6B-1: High-level competitor metrics summary."""
    _, summary = _get_context_data(context)
    if summary.empty:
        return AnalysisResult(
            name="competitor_high_level",
            title="Competitor High Level Metrics",
            df=pd.DataFrame(),
            sheet_name="M6B-1 Metrics",
        )

    total_trans = len(df)
    total_spend = df["amount"].sum()
    total_accts = df["primary_account_num"].nunique()

    comp_trans = summary["total_transactions"].sum()
    comp_spend = summary["total_amount"].sum()
    comp_accts = summary["unique_accounts"].sum()

    metrics = pd.DataFrame(
        [
            {"metric": "Competitors Found", "value": len(summary)},
            {"metric": "Competitor Transactions", "value": int(comp_trans)},
            {"metric": "% of All Transactions", "value": safe_percentage(comp_trans, total_trans)},
            {"metric": "Competitor Spend", "value": round(comp_spend, 2)},
            {"metric": "% of All Spend", "value": safe_percentage(comp_spend, total_spend)},
            {"metric": "Unique Accounts w/ Competitors", "value": int(comp_accts)},
            {"metric": "% of All Accounts", "value": safe_percentage(comp_accts, total_accts)},
        ]
    )

    return AnalysisResult(
        name="competitor_high_level",
        title="Competitor High Level Metrics",
        df=metrics,
        sheet_name="M6B-1 Metrics",
    )


def analyze_top_20_competitors(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """M6B-2: Top 20 competitors by spend."""
    _, summary = _get_context_data(context)
    result = summary.head(20).copy() if not summary.empty else pd.DataFrame()
    return AnalysisResult(
        name="top_20_competitors",
        title="Top 20 Competitors by Spend",
        df=result,
        sheet_name="M6B-2 Top 20",
    )


def analyze_competitor_categories(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """M6B-3: Competitor category breakdown."""
    _, summary = _get_context_data(context)
    if summary.empty:
        return AnalysisResult(
            name="competitor_categories",
            title="Competitor Category Breakdown",
            df=pd.DataFrame(),
            sheet_name="M6B-3 Categories",
        )

    cat = (
        summary.groupby("category")
        .agg(
            total_transactions=("total_transactions", "sum"),
            unique_accounts=("unique_accounts", "sum"),
            total_amount=("total_amount", "sum"),
            competitor_count=("competitor", "count"),
        )
        .reset_index()
    )

    grand_total = cat["total_amount"].sum()
    cat["pct_of_competitor_spend"] = cat["total_amount"].apply(
        lambda x: safe_percentage(x, grand_total)
    )
    cat = cat.sort_values("total_amount", ascending=False).reset_index(drop=True)

    return AnalysisResult(
        name="competitor_categories",
        title="Competitor Category Breakdown",
        df=cat,
        sheet_name="M6B-3 Categories",
    )


def analyze_competitor_biz_personal(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """M6B-4: Business vs personal split for competitor transactions."""
    comp_data, _ = _get_context_data(context)
    if not comp_data:
        return AnalysisResult(
            name="competitor_biz_personal",
            title="Competitor Biz/Personal Split",
            df=pd.DataFrame(),
            sheet_name="M6B-4 Biz Personal",
        )

    all_comp = pd.concat(comp_data.values(), ignore_index=True)
    if "business_flag" not in all_comp.columns:
        return AnalysisResult(
            name="competitor_biz_personal",
            title="Competitor Biz/Personal Split",
            df=pd.DataFrame(),
            sheet_name="M6B-4 Biz Personal",
        )

    split = (
        all_comp.groupby("business_flag")
        .agg(
            total_spend=("amount", "sum"),
            transaction_count=("amount", "count"),
            avg_transaction=("amount", "mean"),
            unique_accounts=("primary_account_num", "nunique"),
        )
        .round(2)
        .reset_index()
    )

    return AnalysisResult(
        name="competitor_biz_personal",
        title="Competitor Biz/Personal Split",
        df=split,
        sheet_name="M6B-4 Biz Personal",
    )


def analyze_competitor_monthly_trends(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """M6B-5: Monthly competitor spend/transaction trends."""
    comp_data, _ = _get_context_data(context)
    if not comp_data:
        return AnalysisResult(
            name="competitor_monthly_trends",
            title="Competitor Monthly Trends",
            df=pd.DataFrame(),
            sheet_name="M6B-5 Monthly",
        )

    all_comp = pd.concat(comp_data.values(), ignore_index=True)
    if "year_month" not in all_comp.columns:
        return AnalysisResult(
            name="competitor_monthly_trends",
            title="Competitor Monthly Trends",
            df=pd.DataFrame(),
            sheet_name="M6B-5 Monthly",
        )

    monthly = (
        all_comp.groupby("year_month")
        .agg(
            total_spend=("amount", "sum"),
            transaction_count=("amount", "count"),
            unique_accounts=("primary_account_num", "nunique"),
        )
        .round(2)
        .reset_index()
        .sort_values("year_month")
    )

    monthly["spend_growth_pct"] = monthly["total_spend"].pct_change() * 100
    monthly["spend_growth_pct"] = monthly["spend_growth_pct"].round(2)

    return AnalysisResult(
        name="competitor_monthly_trends",
        title="Competitor Monthly Trends",
        df=monthly,
        sheet_name="M6B-5 Monthly",
    )
