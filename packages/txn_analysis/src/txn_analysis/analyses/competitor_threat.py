"""M6B-6: Competitor threat scoring."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings


def analyze_threat_assessment(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Threat score = 40% penetration + 30% spend + 30% growth."""
    if not context:
        return _empty_result()

    comp_data = context.get("competitor_data", {})
    if not comp_data:
        return _empty_result()

    total_accounts = df["primary_account_num"].nunique()
    months = sorted(df["year_month"].unique()) if "year_month" in df.columns else []

    rows: list[dict] = []
    for competitor, comp_df in comp_data.items():
        total_spend = comp_df["amount"].sum()
        unique_accts = comp_df["primary_account_num"].nunique()
        penetration = (unique_accts / total_accounts * 100) if total_accounts else 0
        growth_rate = _calc_growth_rate(comp_df, months)

        rows.append(
            {
                "competitor": competitor,
                "category": (
                    comp_df["competitor_category"].iloc[0]
                    if "competitor_category" in comp_df.columns
                    else ""
                ),
                "total_spend": round(total_spend, 2),
                "unique_accounts": unique_accts,
                "penetration_pct": round(penetration, 2),
                "growth_rate": round(growth_rate, 2),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return _empty_result()

    # Normalize each component to 0-100 via percentile rank, then weight
    result["_pen_rank"] = result["penetration_pct"].rank(pct=True) * 100
    result["_spend_rank"] = result["total_spend"].rank(pct=True) * 100
    result["_growth_rank"] = result["growth_rate"].clip(lower=0).rank(pct=True) * 100
    result["threat_score"] = (
        result["_pen_rank"] * 0.4 + result["_spend_rank"] * 0.3 + result["_growth_rank"] * 0.3
    ).round(2)
    result = result.drop(columns=["_pen_rank", "_spend_rank", "_growth_rank"])
    result = result.sort_values("threat_score", ascending=False).head(10).reset_index(drop=True)

    return AnalysisResult.from_df(
        "competitor_threat_assessment",
        "Competitor Threat Assessment",
        result,
        sheet_name="M6B-6 Threat",
    )


def _calc_growth_rate(comp_df: pd.DataFrame, months: list[str]) -> float:
    """6-month growth: compare recent 3 months vs prior 3 months."""
    if "year_month" not in comp_df.columns or len(months) < 4:
        return 0.0

    recent_6 = months[-6:] if len(months) >= 6 else months
    mid = len(recent_6) // 2
    prior = recent_6[:mid]
    recent = recent_6[mid:]

    prior_spend = comp_df[comp_df["year_month"].isin(prior)]["amount"].sum()
    recent_spend = comp_df[comp_df["year_month"].isin(recent)]["amount"].sum()

    if prior_spend == 0:
        return 0.0
    return (recent_spend - prior_spend) / prior_spend * 100


def _empty_result() -> AnalysisResult:
    return AnalysisResult.from_df(
        "competitor_threat_assessment",
        "Competitor Threat Assessment",
        pd.DataFrame(),
        sheet_name="M6B-6 Threat",
    )
