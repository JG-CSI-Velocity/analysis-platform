"""M5C: Spending consistency analysis (CV metric)."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings


def analyze_spending_consistency(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Coefficient of variation per merchant; min months + min spend filter."""
    min_months = settings.consistency_min_months
    min_spend = settings.consistency_min_spend

    monthly = (
        df.groupby(["merchant_consolidated", "year_month"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "spend"})
    )

    pivot = monthly.pivot_table(
        index="merchant_consolidated", columns="year_month", values="spend", fill_value=0
    )

    rows: list[dict] = []
    for merchant in pivot.index:
        values = pivot.loc[merchant].values
        non_zero = values[values > 0]
        if len(non_zero) < min_months:
            continue
        total = float(non_zero.sum())
        if total < min_spend:
            continue
        mean_val = float(non_zero.mean())
        std_val = float(non_zero.std(ddof=1)) if len(non_zero) > 1 else 0.0
        cv = (std_val / mean_val * 100) if mean_val else 0.0
        consistency = max(0, 100 - min(cv, 100))
        rows.append(
            {
                "merchant_consolidated": merchant,
                "total_spend": round(total, 2),
                "mean_monthly": round(mean_val, 2),
                "std_dev": round(std_val, 2),
                "coefficient_variation": round(cv, 2),
                "months_active": int(len(non_zero)),
                "consistency_score": round(consistency, 2),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return AnalysisResult.from_df(
            "spending_consistency",
            "Spending Consistency Analysis",
            result,
            sheet_name="M5C Consistency",
        )

    result = result.sort_values("consistency_score", ascending=False).reset_index(drop=True)

    return AnalysisResult.from_df(
        "spending_consistency",
        "Spending Consistency Analysis",
        result,
        sheet_name="M5C Consistency",
    )
