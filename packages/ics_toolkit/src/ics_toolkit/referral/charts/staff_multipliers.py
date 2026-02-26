"""Chart for R05: Staff Multipliers -- grouped bar."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    NAVY,
    TEAL,
    TICK_SIZE,
)
from ics_toolkit.settings import ChartConfig


def chart_staff_multipliers(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar: multiplier score (primary) and referrals processed (secondary)."""
    data = df.sort_values("Multiplier Score", ascending=False)
    n = len(data)
    if n == 0:
        return b""

    has_referrals = "Referrals Processed" in data.columns
    buf = BytesIO()

    with chart_figure(figsize=(12, 6), save_path=buf) as (fig, ax):
        x = np.arange(n)
        width = 0.35 if has_referrals else 0.6

        ax.bar(
            x - (width / 2 if has_referrals else 0),
            data["Multiplier Score"].values,
            width=width,
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            label="Multiplier Score",
        )

        if has_referrals:
            ax2 = ax.twinx()
            ax2.bar(
                x + width / 2,
                data["Referrals Processed"].values,
                width=width,
                color=TEAL,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
                label="Referrals Processed",
            )
            ax2.set_ylabel("Referrals Processed", fontsize=TICK_SIZE)

            # Combine legends
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(
                h1 + h2,
                l1 + l2,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.15),
                ncol=2,
                frameon=False,
            )
        else:
            ax.legend(loc="upper right", frameon=False)

        ax.set_xticks(x)
        labels = data["Staff"].tolist()
        rotation = -45 if n > 8 else 0
        ax.set_xticklabels(
            labels,
            fontsize=TICK_SIZE,
            rotation=rotation,
            ha="right" if rotation else "center",
        )
        ax.set_ylabel("Multiplier Score", fontsize=TICK_SIZE)

    buf.seek(0)
    return buf.read()
