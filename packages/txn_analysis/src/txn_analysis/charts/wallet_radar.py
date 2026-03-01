"""M18 chart: radar / spider chart for share-of-wallet by MCC category."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import ACCENT, CORAL, TEAL
from txn_analysis.settings import ChartConfig

_SEG_COLORS = {"Responder": ACCENT, "Non-Responder": CORAL, "Control": TEAL}
_SEG_ALPHA = {"Responder": 0.25, "Non-Responder": 0.20, "Control": 0.15}


def chart_wallet_radar(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Radar chart: MCC category spend % per ARS segment."""
    df = result.df
    if df.empty or "Segment" not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "No wallet data", ha="center", va="center")
        ax.axis("off")
        return fig

    categories = [c for c in df.columns if c != "Segment"]
    if len(categories) < 3:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "Need at least 3 MCC categories", ha="center", va="center")
        ax.axis("off")
        return fig

    n = len(categories)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={"projection": "polar"})

    for _, row in df.iterrows():
        seg = row["Segment"]
        values = [row.get(c, 0) for c in categories]
        values += values[:1]  # close

        color = _SEG_COLORS.get(seg, "#999")
        alpha = _SEG_ALPHA.get(seg, 0.2)

        ax.plot(angles, values, "o-", linewidth=2, label=seg, color=color)
        ax.fill(angles, values, alpha=alpha, color=color)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Wrap long labels
    wrapped = [c[:20] + "..." if len(c) > 20 else c for c in categories]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(wrapped, fontsize=8)

    ax.set_title("Share of Wallet by Category", fontsize=14, fontweight="bold", pad=30)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), frameon=False, fontsize=10)

    fig.tight_layout()
    return fig
