"""M6A: Competitor detection -- scans merchant names for competitor patterns."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.competitor_patterns import COMPETITOR_MERCHANTS
from txn_analysis.settings import Settings


def analyze_competitor_detection(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Detect competitor transactions and populate shared context."""
    has_consolidated = "merchant_consolidated" in df.columns
    search_col = "merchant_consolidated" if has_consolidated else "merchant_name"
    upper_col = df[search_col].str.upper()

    all_competitor_data: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict] = []

    for category, patterns in COMPETITOR_MERCHANTS.items():
        for pattern in patterns:
            mask = upper_col.str.contains(pattern, case=False, na=False, regex=False)
            matched = df[mask]
            if matched.empty:
                continue
            comp_df = matched.copy()
            comp_df["competitor_category"] = category
            comp_df["competitor_name"] = pattern
            all_competitor_data[pattern] = comp_df
            summary_rows.append(
                {
                    "competitor": pattern,
                    "category": category,
                    "total_transactions": len(comp_df),
                    "unique_accounts": comp_df["primary_account_num"].nunique(),
                    "total_amount": round(comp_df["amount"].sum(), 2),
                }
            )

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values("total_amount", ascending=False).reset_index(drop=True)

    # Populate shared context for downstream M6B analyses
    if context is not None:
        context["competitor_data"] = all_competitor_data
        context["competitor_summary"] = summary_df

    return AnalysisResult.from_df(
        "competitor_detection",
        "Competitor Detection",
        summary_df,
        sheet_name="M6A Detection",
    )
