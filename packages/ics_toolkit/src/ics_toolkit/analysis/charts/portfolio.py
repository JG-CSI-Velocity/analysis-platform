"""Charts for portfolio analyses -- engagement, growth, closures, concentration."""

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
    DECAY,
    GROWTH,
    LINE_WIDTH,
    MARKER_SIZE,
    NAVY,
)
from ics_toolkit.settings import ChartConfig


def _align_dual_axis_zero(
    y1_values: list,
    y2_values: list,
    pad: float = 0.15,
) -> tuple[list[float], list[float]]:
    """Compute axis ranges so zero is at the same vertical position."""
    y1_nums = [float(v) for v in y1_values if v is not None]
    y2_nums = [float(v) for v in y2_values if v is not None]

    if not y1_nums or not y2_nums:
        return [0, 1], [0, 1]

    y1_min, y1_max = min(y1_nums), max(y1_nums)
    y2_min, y2_max = min(y2_nums), max(y2_nums)

    y1_span = y1_max - y1_min or 1
    y1_lo = y1_min - pad * y1_span
    y1_hi = y1_max + pad * y1_span

    y1_total = y1_hi - y1_lo
    zero_frac = (0 - y1_lo) / y1_total

    y2_span = y2_max - y2_min or 1
    y2_hi = y2_max + pad * y2_span

    if zero_frac >= 1.0:
        y2_lo = y2_min - pad * y2_span
    else:
        y2_lo = -zero_frac * y2_hi / (1 - zero_frac)

    return [y1_lo, y1_hi], [y2_lo, y2_hi]


def chart_engagement_decay(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of engagement decay categories."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        # Color gradient: green for active, orange/red for decaying
        n = len(df)
        gradient = []
        for i in range(n):
            frac = i / max(n - 1, 1)
            if frac < 0.33:
                gradient.append(GROWTH)
            elif frac < 0.66:
                gradient.append(DECAY)
            else:
                gradient.append(CLOSURE)

        bars = ax.bar(
            df["Decay Category"], df["Count"], color=gradient,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.55,
        )

        for bar, val in zip(bars, df["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE, fontweight="bold", color=NAVY,
            )

        ax.set_xlabel("Engagement Category")
        ax.set_ylabel("Account Count")
        ax.set_title("Engagement Decay Analysis")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_net_portfolio_growth(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Dual-axis: bars for opens/closes + cumulative line."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (fig, ax):
        x = np.arange(len(df))
        months = list(df["Month"])

        # Cumulative line on primary axis
        ax.plot(x, df["Cumulative"], color=NAVY, marker="o",
                markersize=MARKER_SIZE, linewidth=LINE_WIDTH + 0.5,
                label="Cumulative Net", zorder=5)

        # Opens/Closes bars on secondary axis
        ax2 = ax.twinx()
        closes_neg = -pd.to_numeric(df["Closes"], errors="coerce").fillna(0)

        ax2.bar(x - 0.2, df["Opens"], 0.4, color=GROWTH, alpha=0.75,
                edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, label="Opens")
        ax2.bar(x + 0.2, closes_neg, 0.4, color=CLOSURE, alpha=0.75,
                edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, label="Closes")

        # Zero line
        ax2.axhline(0, color="#999", linewidth=0.8, zorder=1)

        y1_range, y2_range = _align_dual_axis_zero(
            list(df["Cumulative"]),
            list(df["Opens"]) + list(closes_neg),
        )
        ax.set_ylim(y1_range)
        ax2.set_ylim(y2_range)

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_ylabel("Cumulative Net")
        ax2.set_ylabel("Opens / Closes")
        ax.set_title("Net Portfolio Growth")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)
        ax2.grid(False)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    buf.seek(0)
    return buf.read()


def chart_concentration(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart showing spend share by percentile."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        n = len(df)
        # Gradient: top percentile gets navy, lower gets lighter
        base = np.array([0x1B, 0x36, 0x5D]) / 255
        colors = [(*base, 0.3 + 0.7 * (n - i) / n) for i in range(n)]

        spend_pct = pd.to_numeric(df["Spend Share %"], errors="coerce")
        bars = ax.bar(
            df["Percentile"], spend_pct, color=colors,
            edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH, alpha=BAR_ALPHA, width=0.55,
        )

        for bar, val in zip(bars, spend_pct):
            label = f"{val:.1f}%" if pd.notna(val) else ""
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                label, ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE, fontweight="bold", color=NAVY,
            )

        ax.set_xlabel("Percentile")
        ax.set_ylabel("% of Total Spend")
        ax.set_title("Spend Concentration")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_closure_by_source(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of closures by source channel."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 8), save_path=buf) as (_fig, ax):
        data = df[df["Source"] != "Total"].copy() if "Source" in df.columns else df

        bars = ax.bar(
            data["Source"], data["Closed Count"],
            color=CLOSURE, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA, width=0.5,
        )

        for bar, val in zip(bars, data["Closed Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE, fontweight="bold", color=CLOSURE,
            )

        ax.set_xlabel("Source")
        ax.set_ylabel("Closed Accounts")
        ax.set_title("Closures by Source")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_closure_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar chart of closures by branch."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df
        data = data.sort_values("Closed Count", ascending=True)
        n = len(data)

        bars = ax.barh(
            range(n), data["Closed Count"],
            color=CLOSURE, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH,
            alpha=0.85, height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Branch"].astype(str))

        for bar, val in zip(bars, data["Closed Count"]):
            ax.text(
                bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f"  {val:,}", va="center", ha="left",
                fontsize=DATA_LABEL_SIZE - 2, fontweight="bold", color=CLOSURE,
            )

        ax.set_xlabel("Closed Accounts")
        ax.set_title("Closures by Branch")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_closure_by_account_age(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of closures by account age bucket."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        bars = ax.bar(
            df["Age Range"], df["Closed Count"],
            color=CLOSURE, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA, width=0.55,
        )

        for bar, val in zip(bars, df["Closed Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,}", ha="center", va="bottom",
                fontsize=DATA_LABEL_SIZE, fontweight="bold", color=CLOSURE,
            )

        ax.set_xlabel("Account Age at Closure")
        ax.set_ylabel("Closed Accounts")
        ax.set_title("Closures by Account Age")
        ax.tick_params(axis="x", rotation=-30)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_net_growth_by_source(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar chart of opens/closes/net by source."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        data = df[df["Source"] != "Total"].copy() if "Source" in df.columns else df
        x = np.arange(len(data))
        width = 0.25

        ax.bar(x - width, data["Opens"], width, label="Opens",
               color=GROWTH, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)
        ax.bar(x, data["Closes"], width, label="Closes",
               color=CLOSURE, edgecolor=BAR_EDGE, linewidth=BAR_EDGE_WIDTH)

        # Net as diamond markers
        ax.scatter(x + width, data["Net"], s=120, marker="D",
                   color=NAVY, zorder=5, label="Net")
        for xi, val in zip(x, data["Net"]):
            ax.text(xi + width, val, f" {int(val):+,}",
                    fontsize=DATA_LABEL_SIZE - 2, fontweight="bold",
                    va="bottom", color=NAVY)

        ax.set_xticks(x)
        ax.set_xticklabels(data["Source"])
        ax.set_xlabel("Source")
        ax.set_ylabel("Account Count")
        ax.set_title("Net Growth by Source")
        ax.legend(loc="upper right")
        ax.axhline(0, color="#999", linewidth=0.8)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_closure_rate_trend(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Dual-axis: closure bars + closure rate line."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (fig, ax):
        x = np.arange(len(df))
        months = list(df["Month"])

        ax.bar(x, df["Closures"], color=CLOSURE, alpha=0.45,
               edgecolor="none", width=0.7, label="Closures")
        ax.set_ylabel("Closures")

        ax2 = ax.twinx()
        rates = pd.to_numeric(df["Closure Rate %"], errors="coerce")
        ax2.plot(x, rates, color=NAVY, marker="o",
                 markersize=MARKER_SIZE + 2, linewidth=LINE_WIDTH + 0.5,
                 label="Closure Rate %", zorder=5)
        ax2.set_ylabel("Closure Rate %")
        ax2.grid(False)

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha="right")
        ax.set_title("Closure Rate Trend")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    buf.seek(0)
    return buf.read()
