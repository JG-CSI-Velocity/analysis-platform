"""Chart for R01: Top Referrers -- horizontal bar by influence score."""

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


def chart_top_referrers(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar chart of top referrers ranked by influence score."""
    data = df.sort_values("Influence Score", ascending=True)
    n = len(data)
    if n == 0:
        return b""

    row_height = 0.4
    fig_height = max(4, n * row_height + 1.5)
    buf = BytesIO()

    with chart_figure(figsize=(12, fig_height), save_path=buf) as (_fig, ax):
        y_pos = np.arange(n)
        scores = data["Influence Score"].values
        labels = data["Referrer"].tolist()

        ax.barh(
            y_pos,
            scores,
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            height=0.6,
        )

        for i, val in enumerate(scores):
            ax.annotate(
                f"{val:.1f}",
                xy=(val, i),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=DATA_LABEL_SIZE,
                va="center",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=TICK_SIZE)
        ax.set_xlabel("Influence Score", fontsize=TICK_SIZE)
        ax.xaxis.set_visible(False)

    buf.seek(0)
    return buf.read()
