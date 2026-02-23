"""Charts for strategic analyses: Activation Funnel and Revenue Impact."""

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
    DOLLAR_FORMATTER,
    INTERCHANGE,
    NAVY,
    SPEND,
    TEAL,
    VALUE,
)
from ics_toolkit.settings import ChartConfig


def chart_activation_funnel(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal funnel showing account activation pipeline."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        stages = list(df["Stage"])
        counts = list(df["Count"])
        total = counts[0] if counts else 1

        # Gradient from strong to muted as funnel narrows
        n = len(stages)
        colors = []
        for i in range(n):
            frac = 1.0 - (i / max(n - 1, 1)) * 0.6
            r, g, b = (
                int(0x1B * frac + 0xFF * (1 - frac)),
                int(0x36 * frac + 0xFF * (1 - frac)),
                int(0x5D * frac + 0xFF * (1 - frac)),
            )
            colors.append(f"#{r:02X}{g:02X}{b:02X}")

        bars = ax.barh(
            range(n),
            counts,
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            height=0.65,
        )

        ax.set_yticks(range(n))
        ax.set_yticklabels(stages)
        ax.invert_yaxis()

        for i, (bar, val) in enumerate(zip(bars, counts)):
            pct = val / total * 100 if total > 0 else 0
            label = f"{val:,}  ({pct:.0f}%)" if i > 0 else f"{val:,}"
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                f"  {label}",
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Accounts")
        ax.set_title("Activation Funnel")
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)

    buf.seek(0)
    return buf.read()


def chart_revenue_impact(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of key revenue KPIs."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        revenue_metrics = []
        for _, row in df.iterrows():
            metric = str(row["Metric"])
            value = row["Value"]
            if "Count" not in metric and isinstance(value, (int, float)):
                revenue_metrics.append((metric, float(value)))

        if not revenue_metrics:
            ax.text(
                0.5,
                0.5,
                "No revenue data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=18,
            )
        else:
            labels = [m[0] for m in revenue_metrics]
            values = [m[1] for m in revenue_metrics]

            colors = [INTERCHANGE, VALUE, SPEND, TEAL, ACQUISITION][: len(values)]
            bars = ax.bar(
                labels,
                values,
                color=colors,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
                width=0.55,
            )

            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"${val:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=DATA_LABEL_SIZE,
                    fontweight="bold",
                    color=NAVY,
                )

            ax.set_ylabel("USD ($)")
            ax.set_title("Revenue Impact")
            ax.yaxis.set_major_formatter(DOLLAR_FORMATTER)
            ax.grid(axis="y", alpha=0.15, linestyle="--")
            ax.set_axisbelow(True)
            ax.tick_params(axis="x", rotation=-15)

    buf.seek(0)
    return buf.read()


def chart_revenue_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar chart of interchange by branch."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df
        data = data.sort_values("Est. Interchange", ascending=True)

        n = len(data)
        # Color gradient: lighter for low, darker for high
        base = np.array([0x1B, 0x36, 0x5D]) / 255
        colors = [(*base, 0.4 + 0.6 * i / max(n - 1, 1)) for i in range(n)]

        bars = ax.barh(
            range(n),
            data["Est. Interchange"],
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Branch"].astype(str))

        for bar, val in zip(bars, data["Est. Interchange"]):
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                f"  ${val:,.0f}",
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Estimated Interchange ($)")
        ax.set_title("Revenue by Branch")
        ax.xaxis.set_major_formatter(DOLLAR_FORMATTER)
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_revenue_by_source(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of interchange by source channel."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 8), save_path=buf) as (_fig, ax):
        data = df[df["Source"] != "Total"].copy() if "Source" in df.columns else df
        colors = [NAVY, TEAL, ACQUISITION, SPEND][: len(data)]

        bars = ax.bar(
            data["Source"],
            data["Est. Interchange"],
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.5,
        )

        for bar, val in zip(bars, data["Est. Interchange"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"${val:,.0f}",
                ha="center",
                va="bottom",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Source")
        ax.set_ylabel("Estimated Interchange ($)")
        ax.set_title("Revenue by Source Channel")
        ax.yaxis.set_major_formatter(DOLLAR_FORMATTER)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
