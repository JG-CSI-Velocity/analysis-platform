"""Chart for R02: Emerging Referrers -- scatter timeline."""

from __future__ import annotations

from io import BytesIO

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import TICK_SIZE
from ics_toolkit.settings import ChartConfig


def chart_emerging_referrers(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Scatter plot: Referrer (y) x First Referral date (x), size = Burst Count."""
    if df.empty:
        return b""

    data = df.copy()
    data["First Referral"] = pd.to_datetime(data["First Referral"], errors="coerce")
    data = data.dropna(subset=["First Referral"])
    if data.empty:
        return b""

    n = len(data)
    row_height = 0.5
    fig_height = max(4, n * row_height + 1.5)
    buf = BytesIO()

    with chart_figure(figsize=(12, fig_height), save_path=buf) as (_fig, ax):
        burst = data["Burst Count"].clip(lower=1).values
        marker_sizes = burst * 60

        scores = data["Influence Score"].values
        score_min = scores.min() if len(scores) > 0 else 0
        score_max = scores.max() if len(scores) > 0 else 1
        score_range = score_max - score_min if score_max > score_min else 1
        norm_scores = (scores - score_min) / score_range

        dates = mdates.date2num(data["First Referral"])
        y_pos = np.arange(n)

        sc = ax.scatter(
            dates,
            y_pos,
            s=marker_sizes,
            c=norm_scores,
            cmap="Blues",
            alpha=0.8,
            edgecolors="white",
            linewidth=0.5,
        )
        _fig.colorbar(sc, ax=ax, label="Influence Score", shrink=0.8)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(data["Referrer"].tolist(), fontsize=TICK_SIZE)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        _fig.autofmt_xdate(rotation=45)
        ax.set_xlabel("First Referral Date", fontsize=TICK_SIZE)

    buf.seek(0)
    return buf.read()
