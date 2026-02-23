"""Charts for activity analyses -- engagement, trends, interchange."""

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
    LINE_WIDTH,
    MARKER_SIZE,
    NAVY,
    SPEND,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def _dual_axis_setup(ax, ax2):
    """Standard dual-axis formatting."""
    ax.grid(axis="y", alpha=0.15, linestyle="--")
    ax.set_axisbelow(True)
    ax2.grid(False)


def chart_activity_by_source(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of count + activation rate by Source."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (fig, ax):
        data = df[df["Source"] != "Total"].copy()

        bars = ax.bar(
            data["Source"], data["Count"], color=NAVY,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA,
            width=0.5, label="Count",
        )

        for bar, val in zip(bars, data["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold", color=NAVY,
            )

        if "Activation Rate" in data.columns:
            ax2 = ax.twinx()
            rates = pd.to_numeric(data["Activation Rate"], errors="coerce")
            ax2.plot(
                data["Source"], rates, color=ACQUISITION,
                marker="D", markersize=MARKER_SIZE + 2, linewidth=LINE_WIDTH,
                label="Activation Rate", zorder=5,
            )
            for x, y in zip(data["Source"], rates):
                if pd.notna(y):
                    ax2.text(x, y, f" {y:.0%}", fontsize=DATA_LABEL_SIZE - 2,
                             color=ACQUISITION, fontweight="bold", va="bottom")
            ax2.set_ylabel("Activation Rate")
            ax2.set_ylim(0, 1.15)
            ax2.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
            _dual_axis_setup(ax, ax2)
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        ax.set_xlabel("Source")
        ax.set_ylabel("Account Count")
        ax.set_title("Activity by Source")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_activity_by_balance(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of count + activation rate by Balance Tier."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (fig, ax):
        bars = ax.bar(
            df["Balance Tier"], df["Count"], color=NAVY,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA,
            width=0.55, label="Count",
        )

        for bar, val in zip(bars, df["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE - 3, fontweight="bold", color=NAVY,
            )

        if "Activation Rate" in df.columns:
            ax2 = ax.twinx()
            rates = pd.to_numeric(df["Activation Rate"], errors="coerce")
            ax2.plot(
                df["Balance Tier"], rates, color=ACQUISITION,
                marker="D", markersize=MARKER_SIZE, linewidth=LINE_WIDTH,
                label="Activation Rate", zorder=5,
            )
            ax2.set_ylabel("Activation Rate")
            ax2.set_ylim(0, 1.15)
            ax2.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
            _dual_axis_setup(ax, ax2)
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

        ax.set_xlabel("Balance Tier")
        ax.set_ylabel("Account Count")
        ax.set_title("Activity by Balance Tier")
        ax.tick_params(axis="x", rotation=-30)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_activity_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar of activation rate by Branch."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy()
        if "Activation %" not in data.columns:
            data["Activation %"] = 0
        data = data.sort_values("Activation %", ascending=True)

        rates = pd.to_numeric(data["Activation %"], errors="coerce")
        n = len(data)
        colors = [ACQUISITION if r >= rates.median() else NAVY for r in rates]

        bars = ax.barh(
            range(n), rates, color=colors,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Branch"].astype(str))

        for bar, val in zip(bars, rates):
            label = f"{val:.1%}" if isinstance(val, float) else str(val)
            ax.text(
                bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f"  {label}", va="center", ha="left",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold",
            )

        ax.set_xlabel("Activation Rate")
        ax.set_title("Activation Rate by Branch")
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_monthly_trends(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Multi-line of monthly swipes, active accounts, and spend."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (fig, ax):
        x = range(len(df))
        months = list(df["Month"])

        ax.plot(x, df["Total Swipes"], color=NAVY, marker="o",
                markersize=MARKER_SIZE, linewidth=LINE_WIDTH, label="Total Swipes")
        ax.plot(x, df["Active Accounts"], color=TEAL, marker="s",
                markersize=MARKER_SIZE, linewidth=LINE_WIDTH, label="Active Accounts")

        ax2 = ax.twinx()
        ax2.plot(x, df["Total Spend"], color=SPEND, marker="^",
                 markersize=MARKER_SIZE, linewidth=LINE_WIDTH, linestyle="--",
                 label="Total Spend")
        ax2.set_ylabel("Total Spend ($)")
        ax2.yaxis.set_major_formatter(DOLLAR_FORMATTER)
        ax2.grid(False)

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_ylabel("Swipes / Active Accounts")
        ax.set_title("Monthly Activity Trends")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    buf.seek(0)
    return buf.read()


def chart_activity_source_comparison(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped horizontal bars comparing DM vs Referral KPIs."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        chart_metrics = [
            "% Active", "Avg Swipes / Account", "Avg Spend / Account",
            "Avg Swipes / Active", "Avg Spend / Active",
        ]
        data = df[df["Metric"].isin(chart_metrics)].copy()
        if data.empty:
            ax.text(0.5, 0.5, "No comparison data", transform=ax.transAxes,
                    ha="center", va="center", fontsize=18)
        else:
            y = np.arange(len(data))
            height = 0.35

            dm_vals = pd.to_numeric(data["DM"], errors="coerce")
            ref_vals = pd.to_numeric(data["Referral"], errors="coerce")

            ax.barh(y - height / 2, dm_vals, height, label="DM",
                    color=NAVY, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)
            ax.barh(y + height / 2, ref_vals, height, label="Referral",
                    color=TEAL, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)

            ax.set_yticks(y)
            ax.set_yticklabels(list(reversed(chart_metrics)))
            ax.set_xlabel("Value")
            ax.set_title("DM vs Referral: Source Comparison")
            ax.legend(loc="lower right", fontsize=14)
            ax.grid(axis="x", alpha=0.15, linestyle="--")
            ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_monthly_interchange(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Dual-axis: spend bars + interchange line."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (fig, ax):
        x = np.arange(len(df))
        months = list(df["Month"])

        ax.bar(x, df["Total Spend"], color=SPEND, alpha=0.35,
               edgecolor="none", width=0.7, label="Total Spend")
        ax.set_ylabel("Total Spend ($)")
        ax.yaxis.set_major_formatter(DOLLAR_FORMATTER)

        ax2 = ax.twinx()
        ax2.plot(x, df["Est. Interchange"], color=INTERCHANGE,
                 marker="o", markersize=MARKER_SIZE + 2, linewidth=LINE_WIDTH + 0.5,
                 label="Est. Interchange", zorder=5)
        ax2.set_ylabel("Est. Interchange ($)")
        ax2.yaxis.set_major_formatter(DOLLAR_FORMATTER)
        ax2.grid(False)

        # Endpoint annotation
        if len(df) > 0:
            last_ic = df["Est. Interchange"].iloc[-1]
            ax2.annotate(
                f"${last_ic:,.0f}", xy=(x[-1], last_ic),
                xytext=(10, 10), textcoords="offset points",
                fontsize=DATA_LABEL_SIZE, fontweight="bold", color=INTERCHANGE,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_title("Monthly Interchange Trend")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    buf.seek(0)
    return buf.read()


def chart_business_vs_personal(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bars comparing Business vs Personal KPIs."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        chart_metrics = [
            "% Active", "Avg Swipes / Account", "Avg Spend / Account",
            "Avg Swipes / Active", "Avg Spend / Active",
        ]
        data = df[df["Metric"].isin(chart_metrics)].copy()
        if data.empty:
            ax.text(0.5, 0.5, "No comparison data", transform=ax.transAxes,
                    ha="center", va="center", fontsize=18)
        else:
            y = np.arange(len(data))
            height = 0.35

            biz_vals = pd.to_numeric(data["Business"], errors="coerce")
            per_vals = pd.to_numeric(data["Personal"], errors="coerce")

            ax.barh(y - height / 2, biz_vals, height, label="Business",
                    color=NAVY, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)
            ax.barh(y + height / 2, per_vals, height, label="Personal",
                    color=TEAL, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)

            ax.set_yticks(y)
            ax.set_yticklabels(list(reversed(chart_metrics)))
            ax.set_xlabel("Value")
            ax.set_title("Business vs Personal Accounts")
            ax.legend(loc="lower right", fontsize=14)
            ax.grid(axis="x", alpha=0.15, linestyle="--")
            ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
