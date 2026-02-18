"""M2: MCC (Merchant Category Code) analyses."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.templates import top_mcc_summary
from txn_analysis.settings import Settings


def analyze_mcc_by_accounts(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_mcc_summary(
        df,
        sort_col="unique_accounts",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="mcc_by_accounts",
        title="Top MCC Codes by Unique Accounts",
        df=result,
        sheet_name="M2 MCC Accounts",
    )


def analyze_mcc_by_transactions(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_mcc_summary(
        df,
        sort_col="transaction_count",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="mcc_by_transactions",
        title="Top MCC Codes by Transaction Count",
        df=result,
        sheet_name="M2 MCC Transactions",
    )


def analyze_mcc_by_spend(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    result = top_mcc_summary(
        df,
        sort_col="total_amount",
        top_n=settings.top_n,
        ic_rate=settings.ic_rate,
    )
    return AnalysisResult(
        name="mcc_by_spend",
        title="Top MCC Codes by Total Spend",
        df=result,
        sheet_name="M2 MCC Spend",
    )
