"""M19 chart: multi-line time series with insight annotation box."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import SEGMENT_ORDER
from txn_analysis.charts.theme import ACCENT, CORAL, TEAL, set_insight_title
from txn_analysis.settings import ChartConfig

_SEG_COLORS = {"Responder": ACCENT, "Non-Responder": CORAL, "Control": TEAL}
_SEG_STYLES = {"Responder": "-", "Non-Responder": "--", "Control": ":"}


def chart_spending_trends(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Multi-line weekly spend trend with segment overlay + insights panel."""
    df = result.df
    if df.empty or "Week" not in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No trend data", ha="center", va="center")
        ax.axis("off")
        return fig

    segments = [c for c in SEGMENT_ORDER if c in df.columns]
    if not segments:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No segment columns found", ha="center", va="center")
        ax.axis("off")
        return fig

    insights = result.metadata.get("insights", [])

    # Use wider figure if insights present, to accommodate annotation box
    width = 14 if insights else 12
    fig, ax = plt.subplots(figsize=(width, 6))

    weeks = df["Week"]
    for seg in segments:
        ax.plot(
            weeks,
            df[seg],
            label=seg,
            color=_SEG_COLORS.get(seg, "#999"),
            linestyle=_SEG_STYLES.get(seg, "-"),
            linewidth=2,
            marker="o",
            markersize=3,
        )

    ax.set_ylabel("Weekly Spend ($)")
    ax.legend(frameon=False, fontsize=10)

    # Format x-axis dates
    fig.autofmt_xdate(rotation=30)

    set_insight_title(ax, "Weekly Spending Trends", "by ARS Segment")

    # Insight annotation box (right side)
    if insights:
        text = "\n".join(f"  {i + 1}. {ins}" for i, ins in enumerate(insights))
        props = dict(boxstyle="round,pad=0.6", facecolor="#F5F7FA", edgecolor="#C4C4C4", alpha=0.9)
        ax.annotate(
            f"Key Insights:\n{text}",
            xy=(1.02, 0.95),
            xycoords="axes fraction",
            fontsize=8,
            verticalalignment="top",
            bbox=props,
        )

    fig.tight_layout()
    return fig
