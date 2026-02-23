"""Charts for source analyses -- distribution, cross-tabs, acquisition mix."""

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    DATA_LABEL_SIZE,
    NAVY,
    PALETTE,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def _crosstab_data(df: pd.DataFrame) -> tuple[pd.DataFrame, str, list[str]]:
    """Strip Total row/col from a crosstab DataFrame."""
    row_col = df.columns[0]
    data = df[df[row_col] != "Total"].copy()
    value_cols = [c for c in data.columns if c not in (row_col, "Total")]
    return data, row_col, value_cols


def chart_source_dist(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of ICS accounts by Source."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 8), save_path=buf) as (_fig, ax):
        data = df[df["Source"] != "Total"].copy()
        colors = [NAVY, TEAL][: len(data)] + PALETTE[2 : len(data)]

        bars = ax.bar(
            data["Source"],
            data["Count"],
            color=colors[: len(data)],
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.5,
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

        ax.set_xlabel("Source")
        ax.set_ylabel("Account Count")
        ax.set_title("ICS Accounts by Source")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_source_by_stat(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked bar of Source x Stat Code."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        data, row_col, value_cols = _crosstab_data(df)
        x = np.arange(len(data))
        bottom = np.zeros(len(data))

        for i, col in enumerate(value_cols):
            vals = pd.to_numeric(data[col], errors="coerce").fillna(0)
            ax.bar(
                x,
                vals,
                bottom=bottom,
                label=str(col),
                color=PALETTE[i % len(PALETTE)],
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
                width=0.55,
            )
            bottom += vals.values

        ax.set_xticks(x)
        ax.set_xticklabels(list(data[row_col]))
        ax.set_xlabel("Source")
        ax.set_ylabel("Count")
        ax.set_title("Source x Stat Code")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_source_by_prod(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of Source x Prod Code."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        data, row_col, value_cols = _crosstab_data(df)
        x = np.arange(len(data))
        n_bars = len(value_cols)
        width = 0.7 / max(n_bars, 1)

        for i, col in enumerate(value_cols):
            vals = pd.to_numeric(data[col], errors="coerce").fillna(0)
            offset = (i - n_bars / 2 + 0.5) * width
            ax.bar(
                x + offset,
                vals,
                width,
                label=str(col),
                color=PALETTE[i % len(PALETTE)],
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(list(data[row_col]))
        ax.set_xlabel("Source")
        ax.set_ylabel("Count")
        ax.set_title("Source x Product Code")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_source_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Heatmap of Source x Branch."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 10), save_path=buf) as (fig, ax):
        data, row_col, value_cols = _crosstab_data(df)
        z_data = data[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0).values

        im = ax.imshow(z_data, aspect="auto", cmap="YlGnBu", interpolation="nearest")
        cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.ax.tick_params(labelsize=12)
        cbar.set_label("Accounts", fontsize=14)

        ax.set_xticks(range(len(value_cols)))
        ax.set_xticklabels([str(c) for c in value_cols], rotation=45, ha="right", fontsize=11)
        ax.set_yticks(range(len(data)))
        ax.set_yticklabels(data[row_col].tolist(), fontsize=12)

        z_max = z_data.max() if z_data.size > 0 else 1
        for row_i in range(z_data.shape[0]):
            for col_i in range(z_data.shape[1]):
                val = z_data[row_i, col_i]
                text_color = "white" if val > z_max * 0.55 else "#333"
                ax.text(
                    col_i,
                    row_i,
                    f"{int(val):,}",
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=text_color,
                    fontweight="bold",
                )

        ax.set_xlabel("Branch")
        ax.set_ylabel("Source")
        ax.set_title("Source x Branch Heatmap")

    buf.seek(0)
    return buf.read()


def chart_account_type(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Donut chart of Personal vs Business ICS accounts."""
    buf = BytesIO()
    with chart_figure(figsize=(10, 10), save_path=buf) as (_fig, ax):
        data = df[df["Business?"] != "Total"].copy()
        colors = [NAVY, TEAL][: len(data)]

        wedges, _, autotexts = ax.pie(
            data["Count"],
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        centre = __import__("matplotlib.patches", fromlist=["Circle"]).Circle(
            (0, 0), 0.35, fc="white"
        )
        ax.add_patch(centre)

        for t in autotexts:
            t.set_fontsize(14)
            t.set_fontweight("bold")

        legend_labels = [f"{lbl}  ({val:,})" for lbl, val in zip(data["Business?"], data["Count"])]
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(0.85, 0.5),
            fontsize=13,
            frameon=False,
        )

        ax.set_title("Personal vs Business", fontsize=22, fontweight="bold", pad=20)
        ax.set_aspect("equal")

    buf.seek(0)
    return buf.read()


def chart_source_by_year(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked bar of Source by Year Opened."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        data, row_col, value_cols = _crosstab_data(df)
        year_cols = sorted(value_cols, key=lambda c: str(c))
        x = np.arange(len(data))
        bottom = np.zeros(len(data))

        for i, col in enumerate(year_cols):
            vals = pd.to_numeric(data[col], errors="coerce").fillna(0)
            ax.bar(
                x,
                vals,
                bottom=bottom,
                label=str(col),
                color=PALETTE[i % len(PALETTE)],
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
                width=0.55,
            )
            bottom += vals.values

        ax.set_xticks(x)
        ax.set_xticklabels(list(data[row_col]))
        ax.set_xlabel("Source")
        ax.set_ylabel("Count")
        ax.set_title("Source by Year Opened")
        ax.legend(loc="upper right", fontsize=11, ncol=2)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_source_acquisition_mix(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked bar of monthly new account opens by source channel."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        source_cols = [c for c in df.columns if c not in ("Month", "Total")]
        x = np.arange(len(df))
        bottom = np.zeros(len(df))

        for i, col in enumerate(source_cols):
            vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
            ax.bar(
                x,
                vals,
                bottom=bottom,
                label=str(col),
                color=PALETTE[i % len(PALETTE)],
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
                width=0.7,
            )
            bottom += vals.values

        ax.set_xticks(x)
        ax.set_xticklabels(list(df["Month"]), rotation=45, ha="right")
        ax.set_xlabel("Month")
        ax.set_ylabel("New Accounts")
        ax.set_title("Source Acquisition Mix (Monthly)")
        ax.legend(loc="upper left")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
