"""M6B-7: Discover unmatched financial-institution merchants.

Finds merchants with financial MCC codes that are NOT already classified
as competitors. Surfaces potential gaps in competitor pattern coverage.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.competitor_patterns import FINANCIAL_MCC_CODES
from txn_analysis.settings import Settings


def analyze_unmatched_financial(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Find financial-MCC merchants not already classified as competitors."""
    if "mcc_code" not in df.columns:
        return _empty_result()

    mcc_str = df["mcc_code"].astype(str).str.strip()
    financial_mask = mcc_str.isin(FINANCIAL_MCC_CODES)
    financial_df = df[financial_mask]

    if financial_df.empty:
        return _empty_result()

    # Already-classified merchant names from M6A context
    already_classified: set[str] = set()
    if context:
        comp_data = context.get("competitor_data", {})
        for comp_df in comp_data.values():
            search_col = (
                "merchant_consolidated"
                if "merchant_consolidated" in comp_df.columns
                else "merchant_name"
            )
            already_classified.update(comp_df[search_col].str.upper().unique())

    search_col = (
        "merchant_consolidated" if "merchant_consolidated" in df.columns else "merchant_name"
    )
    upper_merchants = financial_df[search_col].str.upper()
    unmatched_mask = ~upper_merchants.isin(already_classified)
    unmatched = financial_df[unmatched_mask]

    if unmatched.empty:
        return _empty_result()

    unmatched = unmatched.copy()
    unmatched["_upper"] = unmatched[search_col].str.upper()

    summary = (
        unmatched.groupby("_upper")
        .agg(
            mcc_code=("mcc_code", "first"),
            total_transactions=(search_col, "count"),
            unique_accounts=("primary_account_num", "nunique"),
            total_amount=("amount", "sum"),
        )
        .round(2)
        .reset_index()
        .rename(columns={"_upper": "merchant_name"})
        .sort_values("total_amount", ascending=False)
        .reset_index(drop=True)
    )

    return AnalysisResult.from_df(
        "unmatched_financial",
        "Unmatched Financial Merchants",
        summary,
        sheet_name="M6B-7 Unmatched",
    )


def _empty_result() -> AnalysisResult:
    return AnalysisResult.from_df(
        "unmatched_financial",
        "Unmatched Financial Merchants",
        pd.DataFrame(),
        sheet_name="M6B-7 Unmatched",
    )
