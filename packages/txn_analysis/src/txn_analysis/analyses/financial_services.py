"""M7: Financial services detection and summary."""

from __future__ import annotations

import re

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.financial_patterns import FINANCIAL_SERVICES_PATTERNS
from txn_analysis.settings import Settings

# False-positive merchant name fragments to exclude from auto/finance matches.
FALSE_POSITIVES = (
    "TOWING",
    "TOW SERVICE",
    "BODY SHOP",
    "AUTO REPAIR",
    "AUTO PARTS",
    "AUTOZONE",
    "AUTO TRADER",
    "TRADER JOE",
)


def analyze_financial_services_detection(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Detect financial services transactions across 9 categories."""
    search_col = (
        "merchant_consolidated" if "merchant_consolidated" in df.columns else "merchant_name"
    )
    upper_col = df[search_col].str.upper()
    all_rows: list[dict] = []

    for category, patterns in FINANCIAL_SERVICES_PATTERNS.items():
        regex = "|".join(re.escape(p) for p in patterns)
        mask = upper_col.str.contains(regex, case=False, na=False, regex=True)
        matched = df[mask].copy()

        if matched.empty:
            continue

        # Filter out false positives
        fp_mask = (
            matched[search_col].str.upper().apply(lambda x: any(fp in x for fp in FALSE_POSITIVES))
        )
        matched = matched[~fp_mask]

        if matched.empty:
            continue

        matched["financial_category"] = category
        all_rows.append(
            {
                "category": category,
                "unique_accounts": matched["primary_account_num"].nunique(),
                "total_transactions": len(matched),
                "total_spend": round(matched["amount"].sum(), 2),
                "unique_merchants": matched[search_col].nunique(),
            }
        )

    result = pd.DataFrame(all_rows)
    if not result.empty:
        result = result.sort_values("total_spend", ascending=False).reset_index(drop=True)

    return AnalysisResult.from_df(
        "financial_services_detection",
        "Financial Services Detection",
        result,
        sheet_name="M7 Detection",
    )


def analyze_financial_services_summary(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """High-level summary: how many accounts use external financial services.

    Reads detection results from context['completed_results'] to avoid
    running the expensive regex scan a second time.
    """
    # Read from context if available (detection already ran)
    det_df = pd.DataFrame()
    if context:
        prior = context.get("completed_results", {})
        detection_result = prior.get("financial_services_detection")
        if detection_result is not None:
            det_df = detection_result.df

    # Fallback: run detection directly (standalone mode)
    if det_df.empty and (not context or "completed_results" not in context):
        detection = analyze_financial_services_detection(df, business_df, personal_df, settings)
        det_df = detection.df

    if det_df.empty:
        return AnalysisResult.from_df(
            "financial_services_summary",
            "Financial Services Summary",
            pd.DataFrame(),
            sheet_name="M7 Summary",
        )

    total_accounts = df["primary_account_num"].nunique()
    total_spend = df["amount"].sum()

    fs_accounts = det_df["unique_accounts"].sum()
    fs_spend = det_df["total_spend"].sum()
    fs_transactions = det_df["total_transactions"].sum()

    summary = pd.DataFrame(
        [
            {"metric": "Categories Detected", "value": len(det_df)},
            {"metric": "Total Financial Services Spend", "value": round(fs_spend, 2)},
            {
                "metric": "% of Total Spend",
                "value": (round(fs_spend / total_spend * 100, 2) if total_spend else 0),
            },
            {"metric": "Accounts Using Fin Services", "value": int(fs_accounts)},
            {
                "metric": "% of All Accounts",
                "value": (round(fs_accounts / total_accounts * 100, 2) if total_accounts else 0),
            },
            {"metric": "Total Transactions", "value": int(fs_transactions)},
        ]
    )

    return AnalysisResult.from_df(
        "financial_services_summary",
        "Financial Services Summary",
        summary,
        sheet_name="M7 Summary",
    )
