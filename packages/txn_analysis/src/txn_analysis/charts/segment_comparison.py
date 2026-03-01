"""M22 chart: grouped horizontal bar comparing ARS segments."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import ACCENT, CORAL, TEAL
from txn_analysis.settings import ChartConfig

_SEG_COLORS = {"Responder": ACCENT, "Non-Responder": CORAL, "Control": TEAL}


def chart_segment_comparison_bars(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Grouped horizontal bar: key metrics per ARS segment."""
    df = result.df
    if df.empty or "Segment" not in df.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No segment data", ha="center", va="center")
        ax.axis("off")
        return fig

    numeric_cols = ["Avg Txns/Account", "Avg Monthly Spend", "Avg Ticket"]
    available = [c for c in numeric_cols if c in df.columns]

    if not available:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No numeric metrics found", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, axes = plt.subplots(1, len(available), figsize=(5 * len(available), 6))
    if len(available) == 1:
        axes = [axes]

    for ax, col in zip(axes, available):
        segments = df["Segment"].tolist()
        values = df[col].tolist()
        colors = [_SEG_COLORS.get(s, "#999") for s in segments]

        y_pos = np.arange(len(segments))
        ax.barh(y_pos, values, color=colors, height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(segments, fontsize=10)
        ax.set_xlabel(col)

        # Value labels
        for i, v in enumerate(values):
            label = f"${v:,.0f}" if "Spend" in col or "Ticket" in col else f"{v:.1f}"
            ax.text(v + max(values) * 0.02, i, label, va="center", fontsize=9)

        ax.set_title(col, fontsize=11, fontweight="bold")

    fig.suptitle("Segment Behavioral Comparison", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig
