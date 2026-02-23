"""Charts for performance analyses -- days to first use, branch index, product code."""

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    ACQUISITION,
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    DATA_LABEL_SIZE,
    LINE_WIDTH,
    MARKER_SIZE,
    NAVY,
    PALETTE,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def chart_days_to_first_use(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Histogram-style bar of days-to-first-use buckets."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        n = len(df)
        # Gradient: faster activation = greener
        gradient = []
        for i in range(n):
            frac = i / max(n - 1, 1)
            if frac < 0.25:
                gradient.append(ACQUISITION)
            elif frac < 0.5:
                gradient.append(TEAL)
            elif frac < 0.75:
                gradient.append(NAVY)
            else:
                gradient.append("#95A5A6")

        bars = ax.bar(
            df["Days Bucket"],
            df["Count"],
            color=gradient,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.6,
        )

        for bar, val in zip(bars, df["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Days to First Use")
        ax.set_ylabel("Account Count")
        ax.set_title("Days to First Debit Card Use")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_branch_performance_index(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Radar/spider chart of branch performance indices."""
    buf = BytesIO()
    categories = ["Activation Index", "Swipes Index", "Spend Index", "Balance Index"]

    with chart_figure(figsize=(10, 10), save_path=buf) as (fig, ax):
        ax.remove()
        ax = fig.add_subplot(111, polar=True)

        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        for i, (_, row) in enumerate(df.head(8).iterrows()):
            values = [row.get(c, 100) for c in categories]
            values += values[:1]

            color = PALETTE[i % len(PALETTE)]
            ax.plot(angles, values, color=color, linewidth=LINE_WIDTH, label=str(row["Branch"]))
            ax.fill(angles, values, color=color, alpha=0.1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=13)
        ax.set_title("Branch Performance Index", fontsize=22, fontweight="bold", pad=30)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0), fontsize=11)

        max_val = max(200, df[categories].max().max() + 20) if not df.empty else 200
        ax.set_ylim(0, max_val)
        ax.yaxis.set_tick_params(labelsize=11)

    buf.seek(0)
    return buf.read()


def chart_product_code_performance(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of accounts + activation rate by Product Code."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (fig, ax):
        data = df[df["Prod Code"] != "Total"].copy() if "Prod Code" in df.columns else df

        bars = ax.bar(
            data["Prod Code"].astype(str),
            data["Accounts"],
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.55,
            label="Accounts",
        )

        for bar, val in zip(bars, data["Accounts"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
                color=NAVY,
            )

        if "Activation %" in data.columns:
            ax2 = ax.twinx()
            rates = pd.to_numeric(data["Activation %"], errors="coerce")
            ax2.plot(
                data["Prod Code"].astype(str),
                rates,
                color=ACQUISITION,
                marker="D",
                markersize=MARKER_SIZE,
                linewidth=LINE_WIDTH,
                label="Activation %",
                zorder=5,
            )
            ax2.set_ylabel("Activation %")
            ax2.set_ylim(0, 105)
            ax2.grid(False)
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

        ax.set_xlabel("Product Code")
        ax.set_ylabel("Account Count")
        ax.set_title("Product Code Performance")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
