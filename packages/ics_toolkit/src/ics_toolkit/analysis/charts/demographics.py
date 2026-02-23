"""Charts for demographics analyses -- age, balance, closures, trajectories."""

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    CLOSURE,
    DATA_LABEL_SIZE,
    DOLLAR_FORMATTER,
    LINE_WIDTH,
    MARKER_SIZE,
    NAVY,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def chart_age_comparison(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of ICS account age distribution."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        bars = ax.bar(
            df["Age Range"], df["Count"], color=NAVY,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.55,
        )

        for bar, val in zip(bars, df["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold", color=NAVY,
            )

        ax.set_xlabel("Age Range")
        ax.set_ylabel("Count")
        ax.set_title("Account Age Distribution")
        ax.tick_params(axis="x", rotation=-30)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_closures(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of closures by month."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        data = df[df["Month Closed"] != "Total"].copy()

        bars = ax.bar(
            data["Month Closed"], data["Count"], color=CLOSURE,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.6,
        )

        for bar, val in zip(bars, data["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold", color=CLOSURE,
            )

        ax.set_xlabel("Month Closed")
        ax.set_ylabel("Count")
        ax.set_title("Monthly Closures")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_open_vs_close(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of Open vs Closed counts."""
    buf = BytesIO()
    with chart_figure(figsize=(10, 8), save_path=buf) as (_fig, ax):
        open_row = df[df["Metric"] == "Open (Stat Code O)"]
        closed_row = df[df["Metric"] == "Closed (Stat Code C)"]

        labels = []
        values = []
        colors = []
        if not open_row.empty:
            labels.append("Open")
            values.append(open_row["Value"].iloc[0])
            colors.append(NAVY)
        if not closed_row.empty:
            labels.append("Closed")
            values.append(closed_row["Value"].iloc[0])
            colors.append(CLOSURE)

        bars = ax.bar(
            labels, values, color=colors,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.45,
        )

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE + 4, fontweight="bold", color=NAVY,
            )

        ax.set_ylabel("Count")
        ax.set_title("Open vs Closed ICS Accounts")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_balance_tiers(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of ICS accounts by Balance Tier."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        bars = ax.bar(
            df["Balance Tier"], df["Count"], color=TEAL,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.55,
        )

        for bar, val in zip(bars, df["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold", color=NAVY,
            )

        ax.set_xlabel("Balance Tier")
        ax.set_ylabel("Count")
        ax.set_title("ICS Accounts by Balance Tier")
        ax.tick_params(axis="x", rotation=-30)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_stat_open_close(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar of count + line of avg balance by Stat Code."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (fig, ax):
        data = df[~df["Stat Code"].isin(["Total", "Grand Total"])].copy()

        bars = ax.bar(
            data["Stat Code"], data["Count"], color=NAVY,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA,
            width=0.5, label="Count",
        )

        if "Avg Curr Bal" in data.columns:
            ax2 = ax.twinx()
            bal = pd.to_numeric(data["Avg Curr Bal"], errors="coerce")
            ax2.plot(
                data["Stat Code"], bal, color=TEAL,
                marker="D", markersize=MARKER_SIZE, linewidth=LINE_WIDTH,
                label="Avg Balance", zorder=5,
            )
            ax2.set_ylabel("Avg Current Balance")
            ax2.yaxis.set_major_formatter(DOLLAR_FORMATTER)
            ax2.grid(False)
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

        ax.set_xlabel("Stat Code")
        ax.set_ylabel("Count")
        ax.set_title("Stat Code: Count & Avg Balance")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_age_vs_balance(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Dual-axis bar+line of account count and avg balance by age range."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (fig, ax):
        bars = ax.bar(
            df["Age Range"], df["Count"], color=NAVY,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA,
            width=0.55, label="Count",
        )

        if "Avg Curr Bal" in df.columns:
            ax2 = ax.twinx()
            ax2.plot(
                df["Age Range"], df["Avg Curr Bal"], color=TEAL,
                marker="D", markersize=MARKER_SIZE, linewidth=LINE_WIDTH,
                label="Avg Balance", zorder=5,
            )
            ax2.set_ylabel("Avg Current Balance ($)")
            ax2.yaxis.set_major_formatter(DOLLAR_FORMATTER)
            ax2.grid(False)
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        ax.set_xlabel("Age Range")
        ax.set_ylabel("Count")
        ax.set_title("Account Age vs Balance")
        ax.tick_params(axis="x", rotation=-30)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_balance_tier_detail(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of count + avg swipes by balance tier."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        x = np.arange(len(df))
        width = 0.3

        ax.bar(x - width / 2, df["Count"], width, label="Count",
               color=NAVY, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)

        if "Avg Swipes" in df.columns:
            ax.bar(x + width / 2, df["Avg Swipes"], width, label="Avg Swipes",
                   color=TEAL, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)

        ax.set_xticks(x)
        ax.set_xticklabels(df["Balance Tier"], rotation=-30, ha="left")
        ax.set_xlabel("Balance Tier")
        ax.set_ylabel("Value")
        ax.set_title("Balance Tier Detail")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_age_dist(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of ICS Stat O age distribution."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        bars = ax.bar(
            df["Age Range"], df["Count"], color=TEAL,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.55,
        )

        for bar, val in zip(bars, df["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold", color=NAVY,
            )

        ax.set_xlabel("Age Range")
        ax.set_ylabel("Count")
        ax.set_title("Open Account Age Distribution")
        ax.tick_params(axis="x", rotation=-30)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_balance_trajectory(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of Avg Bal vs Curr Bal by Branch."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df
        x = np.arange(len(data))
        width = 0.3

        ax.bar(x - width / 2, pd.to_numeric(data["Avg Bal"], errors="coerce"),
               width, label="Avg Balance", color=TEAL,
               edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)
        ax.bar(x + width / 2, pd.to_numeric(data["Curr Bal"], errors="coerce"),
               width, label="Current Balance", color=NAVY,
               edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)

        ax.set_xticks(x)
        ax.set_xticklabels(data["Branch"].astype(str), rotation=45, ha="right")
        ax.set_xlabel("Branch")
        ax.set_ylabel("Average Balance ($)")
        ax.set_title("Balance Trajectory by Branch")
        ax.yaxis.set_major_formatter(DOLLAR_FORMATTER)
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
