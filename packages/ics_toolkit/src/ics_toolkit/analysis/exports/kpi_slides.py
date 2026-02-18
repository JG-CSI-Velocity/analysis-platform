"""KPI slide builders for PPTX executive summary."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.exports.deck_builder import SlideContent


def _format_kpi_value(key: str, value: object) -> str:
    """Format a KPI value for display based on the metric name."""
    if isinstance(value, float) and ("Rate" in key or "%" in key):
        return f"{value:.1f}%"
    if isinstance(value, (int, float)) and ("Interchange" in key or "Revenue" in key):
        return f"${value:,.0f}"
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return str(value)


def build_executive_kpi_slide(analysis: AnalysisResult) -> SlideContent | None:
    """Build a KPI summary slide from executive summary metadata.

    Returns a SlideContent with formatted KPI bullets in a 2x3 grid,
    or None if no hero_kpis metadata exists.
    """
    hero_kpis = analysis.metadata.get("hero_kpis", {})
    traffic_lights = analysis.metadata.get("traffic_lights", {})

    if not hero_kpis:
        return None

    bullets = []
    for key, value in hero_kpis.items():
        formatted = _format_kpi_value(key, value)
        light = traffic_lights.get(key, "")
        indicator = f" [{light.upper()}]" if light and light != "gray" else ""
        bullets.append(f"{key}\n{formatted}{indicator}")

    # Pad to 6 for a 2x3 grid
    while len(bullets) < 6:
        bullets.append("")

    return SlideContent(
        slide_type="summary",
        title="Executive Summary - Key Performance Indicators",
        bullets=bullets[:9],
        layout_index=5,
    )


def build_narrative_slide(analysis: AnalysisResult) -> SlideContent | None:
    """Build a narrative slide with What / So What / Now What bullets.

    Returns a SlideContent, or None if no narrative metadata exists.
    """
    narrative = analysis.metadata.get("narrative", [])
    if not narrative:
        return None

    labels = {"what": "WHAT", "so_what": "SO WHAT", "now_what": "NOW WHAT"}

    bullets = []
    for item in narrative:
        label = labels.get(item["type"], item["type"].upper())
        bullets.append(f"{label}: {item['text']}")

    return SlideContent(
        slide_type="summary",
        title="Executive Summary - Strategic Narrative",
        bullets=bullets,
        layout_index=5,
    )


def generate_declarative_title(analysis: AnalysisResult) -> str:
    """Generate a data-driven title from analysis results.

    Extracts a key insight and returns a declarative sentence like
    "Branch 12 leads activation at 78%" instead of "Branch Activation".
    Falls back to analysis.title if no insight can be extracted.
    """
    df = analysis.df
    name = analysis.name

    if df.empty:
        return analysis.title

    try:
        return _try_declarative_title(name, df)
    except (KeyError, IndexError, ValueError, TypeError):
        return analysis.title


def _try_declarative_title(name: str, df: pd.DataFrame) -> str:
    """Attempt to generate a declarative title; raises on failure."""
    if name == "Branch Activation" and "Branch" in df.columns:
        rate_col = "Activation Rate" if "Activation Rate" in df.columns else "Activation %"
        if rate_col in df.columns:
            non_total = df[df["Branch"] != "Total"]
            if not non_total.empty:
                rates = pd.to_numeric(non_total[rate_col], errors="coerce")
                best_idx = rates.idxmax()
                branch = non_total.loc[best_idx, "Branch"]
                rate = rates.loc[best_idx]
                return f"Branch {branch} leads activation at {rate:.0f}%"

    if name == "Branch Performance Index" and "Composite Score" in df.columns:
        top = df.iloc[0]
        score = top["Composite Score"]
        return f"Branch {top['Branch']} tops performance (score: {score:.0f})"

    if name == "Activation Funnel" and "Count" in df.columns:
        first_count = df.iloc[0]["Count"]
        last_count = df.iloc[-1]["Count"]
        if first_count > 0:
            pct = (last_count / first_count) * 100
            return f"Activation funnel: {pct:.0f}% reach active status"

    if name == "Days to First Use" and "Count" in df.columns:
        total = df["Count"].sum()
        never = df.loc[df["Days Bucket"] == "Never Used", "Count"].sum()
        if total > 0:
            pct = ((total - never) / total) * 100
            return f"{pct:.0f}% of accounts activate their debit card"

    if name == "Engagement Decay" and "Category" in df.columns:
        decayed = df[df["Category"] == "Decayed"]
        if not decayed.empty and "% of Total" in df.columns:
            pct = decayed["% of Total"].iloc[0]
            return f"{pct:.1f}% of accounts show engagement decay"

    if name == "Spend Concentration" and "Spend Share %" in df.columns:
        top10 = df[df["Percentile"] == "Top 10%"]
        if not top10.empty:
            share = top10["Spend Share %"].iloc[0]
            return f"Top 10% of spenders account for {share:.0f}% of volume"

    raise ValueError("no declarative title available")
