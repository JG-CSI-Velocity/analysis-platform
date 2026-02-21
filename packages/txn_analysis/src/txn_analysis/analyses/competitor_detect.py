"""M6A: Competitor detection -- 3-tier precision matching.

Classifies merchant names via exact > starts_with > contains matching,
with false-positive exclusion. Populates shared context for downstream
M6B analyses.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.competitor_patterns import classify_merchant, is_false_positive
from txn_analysis.settings import Settings


def analyze_competitor_detection(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Detect competitor transactions via 3-tier matching and populate shared context."""
    has_consolidated = "merchant_consolidated" in df.columns
    search_col = "merchant_consolidated" if has_consolidated else "merchant_name"
    upper_col = df[search_col].str.upper()

    # Classify every merchant
    classifications = upper_col.apply(classify_merchant)
    categories = classifications.apply(lambda r: r.category)
    tiers = classifications.apply(lambda r: r.tier)
    patterns = classifications.apply(lambda r: r.pattern)

    # Filter: matched AND not a false positive
    matched_mask = categories.notna()
    fp_mask = upper_col.apply(is_false_positive)
    final_mask = matched_mask & ~fp_mask

    if not final_mask.any():
        empty_summary = pd.DataFrame()
        if context is not None:
            context["competitor_data"] = {}
            context["competitor_summary"] = empty_summary
        return AnalysisResult.from_df(
            "competitor_detection",
            "Competitor Detection",
            empty_summary,
            sheet_name="M6A Detection",
        )

    comp_df = df[final_mask].copy()
    comp_df["competitor_category"] = categories[final_mask].values
    comp_df["competitor_name"] = patterns[final_mask].values
    comp_df["match_tier"] = tiers[final_mask].values

    # Build per-pattern data dict (keyed by pattern for backward compat)
    all_competitor_data: dict[str, pd.DataFrame] = {}
    for pattern_name, group in comp_df.groupby("competitor_name"):
        all_competitor_data[pattern_name] = group

    # Build summary
    summary_rows: list[dict] = []
    for pattern_name, group in comp_df.groupby("competitor_name"):
        summary_rows.append(
            {
                "competitor": pattern_name,
                "category": group["competitor_category"].iloc[0],
                "match_tier": group["match_tier"].iloc[0],
                "total_transactions": len(group),
                "unique_accounts": group["primary_account_num"].nunique(),
                "total_amount": round(group["amount"].sum(), 2),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values("total_amount", ascending=False).reset_index(drop=True)

    if context is not None:
        context["competitor_data"] = all_competitor_data
        context["competitor_summary"] = summary_df

    return AnalysisResult.from_df(
        "competitor_detection",
        "Competitor Detection",
        summary_df,
        sheet_name="M6A Detection",
    )
