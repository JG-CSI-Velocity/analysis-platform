"""M15: Recurring payment charts (matplotlib)."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import ACCENT, ACCENT_SECONDARY, set_insight_title
from txn_analysis.settings import ChartConfig


def chart_recurring_merchants(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Top recurring merchants by account count."""
    df = result.df
    if df.empty or "Merchant" not in df.columns:
        return Figure()

    data = df.head(20).sort_values("Recurring Accounts", ascending=True)
    n = len(data)

    row_height = 0.35
    fig_height = max(4, n * row_height + 1.5)

    with chart_figure(figsize=(10, fig_height)) as (fig, ax):
        y_pos = list(range(n))
        values = data["Recurring Accounts"].tolist()
        labels = data["Merchant"].tolist()

        ax.barh(y_pos, values, color=ACCENT, height=0.6)

        for i, val in enumerate(values):
            ax.annotate(
                f"{val:,.0f}",
                xy=(val, i),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=8,
                va="center",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.xaxis.set_visible(False)

        set_insight_title(
            ax,
            "Top Recurring Merchants",
            f"{len(result.df)} merchants with 3+ month relationships",
        )
        fig.tight_layout()

    return fig


def chart_recurring_onsets(result: AnalysisResult, config: ChartConfig) -> Figure:
    """New recurring relationships by month -- when subscriptions start."""
    onsets = result.data.get("onsets")
    if onsets is None or onsets.empty:
        return Figure()

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        months = onsets["Month"].tolist()
        new_recurring = onsets["New Recurring Relationships"].tolist()
        x = np.arange(len(months))

        # Bar: new recurring relationships count
        ax.bar(x, new_recurring, color=ACCENT, width=0.6, label="New Recurring")

        # Value labels on bars
        for i, val in enumerate(new_recurring):
            ax.annotate(
                str(val),
                xy=(i, val),
                xytext=(0, 4),
                textcoords="offset points",
                fontsize=9,
                ha="center",
                va="bottom",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=-45, ha="right", fontsize=9)
        ax.set_ylabel("New Relationships", fontsize=10)

        # Line: spend at onset on secondary y-axis
        if onsets["Spend at Onset"].sum() > 0:
            ax2 = ax.twinx()
            ax2.plot(
                x,
                onsets["Spend at Onset"].tolist(),
                color=ACCENT_SECONDARY,
                linewidth=2,
                marker="o",
                markersize=5,
                label="Spend at Onset",
            )
            ax2.set_ylabel("Spend ($)", fontsize=10)
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_visible(False)
            ax2.spines["left"].set_visible(False)
            ax2.spines["bottom"].set_visible(False)

            # Combined legend
            lines_1, labels_1 = ax.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax.legend(
                lines_1 + lines_2,
                labels_1 + labels_2,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.18),
                ncol=2,
                frameon=False,
            )
        else:
            ax.legend(
                loc="upper center",
                bbox_to_anchor=(0.5, -0.18),
                ncol=1,
                frameon=False,
            )

        total = int(onsets["New Recurring Relationships"].sum())
        set_insight_title(
            ax,
            "New Recurring Relationships by Month",
            f"{total} total new subscriptions detected across {len(onsets)} months",
        )
        fig.tight_layout()

    return fig
