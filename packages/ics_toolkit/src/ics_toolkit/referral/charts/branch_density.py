"""Chart for R06: Branch Influence Density -- vertical bar."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    DATA_LABEL_SIZE,
    NAVY,
    TICK_SIZE,
)
from ics_toolkit.settings import ChartConfig


def chart_branch_density(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Vertical bar of avg influence score per branch, sorted descending."""
    data = df.sort_values("Avg Influence Score", ascending=False)
    n = len(data)
    if n == 0:
        return b""

    buf = BytesIO()

    with chart_figure(figsize=(12, 6), save_path=buf) as (_fig, ax):
        x = np.arange(n)
        scores = data["Avg Influence Score"].values

        ax.bar(
            x,
            scores,
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.6,
        )

        for i, val in enumerate(scores):
            ax.annotate(
                f"{val:.1f}",
                xy=(i, val),
                xytext=(0, 4),
                textcoords="offset points",
                fontsize=DATA_LABEL_SIZE,
                ha="center",
                va="bottom",
            )

        labels = data["Branch"].tolist()
        ax.set_xticks(x)
        rotation = -45 if n > 8 else 0
        ax.set_xticklabels(
            labels,
            fontsize=TICK_SIZE,
            rotation=rotation,
            ha="right" if rotation else "center",
        )
        ax.set_ylabel("Avg Influence Score", fontsize=TICK_SIZE)

    buf.seek(0)
    return buf.read()
