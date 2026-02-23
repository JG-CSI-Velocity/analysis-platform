"""Charts for DM/REF source deep-dive analyses.

These chart functions are used for BOTH DM and REF analyses (identical column
structure, different Source filter). The CHART_REGISTRY maps REF names to
these same functions.
"""

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
    LINE_WIDTH,
    MARKER_SIZE,
    NAVY,
    SPEND,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def chart_dm_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar of source count by Branch with debit % as text."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy()
        data = data.sort_values("Count", ascending=True)
        n = len(data)

        base = np.array([0x1B, 0x36, 0x5D]) / 255
        colors = [(*base, 0.4 + 0.6 * i / max(n - 1, 1)) for i in range(n)]

        bars = ax.barh(
            range(n),
            data["Count"],
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Branch"].astype(str))

        for bar, (_, row) in zip(bars, data.iterrows()):
            count = int(row["Count"])
            debit_pct = row.get("Debit %")
            if pd.notna(debit_pct):
                label = f"  {count:,}  ({debit_pct:.0f}% debit)"
            else:
                label = f"  {count:,}"
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                label,
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Account Count")
        ax.set_title("Accounts by Branch")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_dm_by_year(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Vertical bar of source count by Year Opened."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        data = df[df["Year Opened"] != "Total"].copy()

        bars = ax.bar(
            data["Year Opened"].astype(str),
            data["Count"],
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.55,
        )

        for bar, val in zip(bars, data["Count"]):
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

        ax.set_xlabel("Year Opened")
        ax.set_ylabel("Account Count")
        ax.set_title("Accounts by Year Opened")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_dm_activity_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of count + activation rate by Branch."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (fig, ax):
        data = df[df["Branch"] != "Total"].copy()
        data = data.sort_values("Count", ascending=False)

        bars = ax.bar(
            data["Branch"].astype(str),
            data["Count"],
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.55,
            label="Count",
        )

        for bar, val in zip(bars, data["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=DATA_LABEL_SIZE - 3,
                fontweight="bold",
                color=NAVY,
            )

        if "Activation %" in data.columns:
            ax2 = ax.twinx()
            rates = pd.to_numeric(data["Activation %"], errors="coerce")
            ax2.plot(
                data["Branch"].astype(str),
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

        ax.set_xlabel("Branch")
        ax.set_ylabel("Account Count")
        ax.set_title("Activity by Branch")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_dm_monthly_trends(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Dual-axis line of Swipes + Spend over L12M."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (fig, ax):
        x = range(len(df))
        months = list(df["Month"])

        ax.plot(
            x,
            df["Total Swipes"],
            color=NAVY,
            marker="o",
            markersize=MARKER_SIZE,
            linewidth=LINE_WIDTH,
            label="Total Swipes",
        )
        ax.plot(
            x,
            df["Active Accounts"],
            color=TEAL,
            marker="s",
            markersize=MARKER_SIZE,
            linewidth=LINE_WIDTH,
            label="Active Accounts",
        )

        ax2 = ax.twinx()
        ax2.plot(
            x,
            df["Total Spend"],
            color=SPEND,
            marker="^",
            markersize=MARKER_SIZE,
            linewidth=LINE_WIDTH,
            linestyle="--",
            label="Total Spend",
        )
        ax2.set_ylabel("Total Spend ($)")
        ax2.yaxis.set_major_formatter(DOLLAR_FORMATTER)
        ax2.grid(False)

        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_ylabel("Swipes / Active Accounts")
        ax.set_title("Monthly Trends")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    buf.seek(0)
    return buf.read()
