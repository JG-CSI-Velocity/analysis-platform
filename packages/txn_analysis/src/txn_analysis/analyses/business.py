"""M3: Business account top merchant analyses."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.templates import top_merchants_summary
from txn_analysis.settings import Settings


def analyze_business_top_by_spend(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_merchants_summary(
        business_df,
        sort_col="total_amount",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="business_top_by_spend",
        title="Business - Top Merchants by Spend",
        df=result,
        sheet_name="M3 Biz Spend",
    )


def analyze_business_top_by_transactions(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_merchants_summary(
        business_df,
        sort_col="transaction_count",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="business_top_by_transactions",
        title="Business - Top Merchants by Transactions",
        df=result,
        sheet_name="M3 Biz Transactions",
    )


def analyze_business_top_by_accounts(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_merchants_summary(
        business_df,
        sort_col="unique_accounts",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="business_top_by_accounts",
        title="Business - Top Merchants by Accounts",
        df=result,
        sheet_name="M3 Biz Accounts",
    )
