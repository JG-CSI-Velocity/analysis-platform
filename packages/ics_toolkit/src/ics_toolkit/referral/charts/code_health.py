"""Chart for R07: Code Health -- stacked bar by reliability tier."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    PALETTE,
    TICK_SIZE,
)
from ics_toolkit.settings import ChartConfig


def chart_code_health(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked bar chart: code category distribution by Reliability tier."""
    if df.empty:
        return b""

    data = df.copy()
    data["Label"] = data["Channel"] + " / " + data["Type"]
    reliabilities = data["Reliability"].unique()

    buf = BytesIO()

    with chart_figure(figsize=(12, 6), save_path=buf) as (_fig, ax):
        labels_unique = data["Label"].unique()
        x = np.arange(len(labels_unique))
        label_to_idx = {lbl: i for i, lbl in enumerate(labels_unique)}
        bottom = np.zeros(len(labels_unique))

        for i, rel in enumerate(reliabilities):
            subset = data[data["Reliability"] == rel]
            heights = np.zeros(len(labels_unique))
            for _, row in subset.iterrows():
                idx = label_to_idx[row["Label"]]
                heights[idx] = row["Count"]

            color = PALETTE[i % len(PALETTE)]
            ax.bar(
                x,
                heights,
                bottom=bottom,
                color=color,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
                label=rel,
                width=0.6,
            )
            bottom += heights

        ax.set_xticks(x)
        rotation = -45 if len(labels_unique) > 6 else 0
        ax.set_xticklabels(
            labels_unique,
            fontsize=TICK_SIZE,
            rotation=rotation,
            ha="right" if rotation else "center",
        )
        ax.set_ylabel("Count", fontsize=TICK_SIZE)
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=min(len(reliabilities), 4),
            frameon=False,
        )

    buf.seek(0)
    return buf.read()
