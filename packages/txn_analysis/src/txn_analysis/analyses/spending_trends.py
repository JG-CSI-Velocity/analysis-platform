"""M19: Spending trends by ARS segment with auto-generated insights.

Computes weekly spend time series for each ARS segment and detects
notable patterns (peaks, trends, cross-segment differences) to
generate bullet-point insights for the chart annotation box.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import SEGMENT_ORDER, merge_segments_to_txn
from txn_analysis.settings import Settings


def _generate_insights(weekly: pd.DataFrame) -> list[str]:
    """Auto-generate up to 3 text insights from weekly segment spend."""
    insights: list[str] = []

    if weekly.empty:
        return insights

    segments = [c for c in weekly.columns if c in SEGMENT_ORDER]
    if not segments:
        return insights

    # Insight 1: overall trend direction per segment
    for seg in segments:
        series = weekly[seg].dropna()
        if len(series) < 4:
            continue
        first_half = series.iloc[: len(series) // 2].mean()
        second_half = series.iloc[len(series) // 2 :].mean()
        if first_half > 0:
            pct_change = (second_half - first_half) / first_half * 100
            direction = (
                "increasing" if pct_change > 5 else "declining" if pct_change < -5 else "stable"
            )
            insights.append(f"{seg} spend is {direction} ({pct_change:+.0f}% half-over-half)")
            break  # One trend insight is enough

    # Insight 2: cross-segment comparison
    if "Responder" in segments and "Non-Responder" in segments:
        resp_avg = weekly["Responder"].mean()
        non_resp_avg = weekly["Non-Responder"].mean()
        if non_resp_avg > 0:
            lift = (resp_avg - non_resp_avg) / non_resp_avg * 100
            insights.append(f"Responders average {lift:+.0f}% weekly spend vs Non-Responders")

    # Insight 3: peak week identification
    total_weekly = weekly[segments].sum(axis=1)
    if not total_weekly.empty:
        peak_idx = total_weekly.idxmax()
        peak_val = total_weekly.max()
        avg_val = total_weekly.mean()
        if avg_val > 0 and peak_val > avg_val * 1.3:
            peak_label = str(peak_idx)
            if hasattr(peak_idx, "strftime"):
                peak_label = peak_idx.strftime("%b %d")
            insights.append(f"Peak spending week: {peak_label} ({peak_val / avg_val:.1f}x average)")

    return insights[:3]


def analyze_spending_trends(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Compute weekly spending trends per ARS segment."""
    ctx = context or {}
    odd_df = ctx.get("odd_df")

    if odd_df is None or (isinstance(odd_df, pd.DataFrame) and odd_df.empty):
        return AnalysisResult.from_df(
            "spending_trends",
            "Spending Trends by Segment",
            pd.DataFrame({"Note": ["ODD data required for segment trends"]}),
            metadata={"sheet_name": "M19 Trends"},
        )

    if df.empty or "amount" not in df.columns:
        return AnalysisResult.from_df(
            "spending_trends",
            "Spending Trends by Segment",
            pd.DataFrame(),
            error="No transaction data available",
        )

    merged = merge_segments_to_txn(df, odd_df)
    known = merged[merged["ars_segment"] != "Unknown"]

    if known.empty:
        return AnalysisResult.from_df(
            "spending_trends",
            "Spending Trends by Segment",
            pd.DataFrame({"Note": ["No accounts matched between ODD and transactions"]}),
            metadata={"sheet_name": "M19 Trends"},
        )

    # Parse dates
    dates = pd.to_datetime(known["transaction_date"], errors="coerce", format="mixed")
    known = known[dates.notna()].copy()
    known["txn_date"] = dates[dates.notna()]

    if known.empty:
        return AnalysisResult.from_df(
            "spending_trends",
            "Spending Trends by Segment",
            pd.DataFrame({"Note": ["No valid transaction dates found"]}),
            metadata={"sheet_name": "M19 Trends"},
        )

    # Weekly aggregation per segment
    known["week"] = known["txn_date"].dt.to_period("W").apply(lambda p: p.start_time)

    weekly = known.groupby(["week", "ars_segment"])["amount"].sum().unstack(fill_value=0)

    # Reorder columns
    ordered = [s for s in SEGMENT_ORDER if s in weekly.columns]
    weekly = weekly[ordered]

    insights = _generate_insights(weekly)

    # Flatten for export
    export_df = weekly.reset_index()
    export_df.columns = ["Week"] + list(weekly.columns)

    insights_df = pd.DataFrame({"Insight": insights}) if insights else pd.DataFrame()

    data: dict[str, pd.DataFrame] = {"main": export_df}
    if not insights_df.empty:
        data["insights"] = insights_df

    return AnalysisResult(
        name="spending_trends",
        title="Spending Trends by Segment",
        data=data,
        metadata={
            "sheet_name": "M19 Trends",
            "category": "Spending Intelligence",
            "chart_id": "M19",
            "insights": insights,
        },
        summary=insights[0] if insights else "Weekly spending trends by ARS segment",
    )
