"""M1: Overall top merchant analyses (all accounts)."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.templates import top_merchants_summary
from txn_analysis.settings import Settings


def analyze_top_by_spend(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_merchants_summary(
        df,
        sort_col="total_amount",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="top_merchants_by_spend",
        title="Top Merchants by Total Spend",
        df=result,
        sheet_name="M1 Top Spend",
    )


def analyze_top_by_transactions(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_merchants_summary(
        df,
        sort_col="transaction_count",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="top_merchants_by_transactions",
        title="Top Merchants by Transaction Count",
        df=result,
        sheet_name="M1 Top Transactions",
    )


def analyze_top_by_accounts(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_merchants_summary(
        df,
        sort_col="unique_accounts",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="top_merchants_by_accounts",
        title="Top Merchants by Unique Accounts",
        df=result,
        sheet_name="M1 Top Accounts",
    )
