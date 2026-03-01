"""M21 chart: violin plot of transaction amount distribution by spending tier."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import TIER_ORDER
from txn_analysis.charts.theme import ACCENT, CORAL, TEAL, set_insight_title
from txn_analysis.settings import ChartConfig

_TIER_COLORS = [TEAL, ACCENT, CORAL]


def chart_txn_violin(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Violin plot: transaction amount distribution per spending tier."""
    raw = result.data.get("raw_amounts")
    if raw is None or raw.empty:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No distribution data", ha="center", va="center")
        ax.axis("off")
        return fig

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 7))

    datasets = []
    labels = []
    colors = []
    for i, tier in enumerate(TIER_ORDER):
        subset = raw[raw["spending_tier"] == tier]["amount"]
        if subset.empty:
            continue
        datasets.append(subset.values)
        labels.append(tier)
        colors.append(_TIER_COLORS[i % len(_TIER_COLORS)])

    if not datasets:
        ax.text(0.5, 0.5, "Insufficient data for distribution plot", ha="center", va="center")
        ax.axis("off")
        return fig

    parts = ax.violinplot(datasets, showmeans=True, showmedians=True, showextrema=False)

    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.7)
        pc.set_edgecolor("none")

    parts["cmeans"].set_color("#333")
    parts["cmeans"].set_linewidth(1.5)
    parts["cmedians"].set_color("#E4573D")
    parts["cmedians"].set_linewidth(2)

    # Add jittered strip points (sampled for performance)
    rng = np.random.default_rng(42)
    for i, data in enumerate(datasets):
        sample = data if len(data) <= 200 else rng.choice(data, 200, replace=False)
        jitter = rng.normal(0, 0.04, size=len(sample))
        ax.scatter(
            np.full_like(sample, i + 1) + jitter,
            sample,
            alpha=0.15,
            s=6,
            color=colors[i],
            zorder=2,
        )

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Transaction Amount ($)")

    # Quartile annotations
    for i, data in enumerate(datasets):
        q1, med, q3 = np.percentile(data, [25, 50, 75])
        ax.hlines([q1, q3], i + 0.7, i + 1.3, colors="#999", linewidths=0.8, linestyles="--")

    set_insight_title(ax, "Transaction Amount Distribution", "by Spending Tier")
    fig.tight_layout()
    return fig
