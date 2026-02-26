"""Generic chart builders for V4 storyline analyses (matplotlib).

Each builder returns a matplotlib Figure. Import chart constants from charts.theme.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from matplotlib.figure import Figure

from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import (
    CATEGORY_PALETTE,
    COLORS,
    _fmt_value,
    format_currency,
)

# ---------------------------------------------------------------------------
# Chart Builders
# ---------------------------------------------------------------------------


def horizontal_bar(
    df,
    x_col: str,
    y_col: str,
    title: str,
    *,
    color: str | None = None,
    top_n: int = 25,
    show_values: bool = True,
    value_format: str = "${:,.0f}",
) -> Figure:
    """Horizontal bar chart for rankings (merchants, competitors, etc).

    Data is sorted descending by x_col and limited to top_n rows.
    Bars render bottom-to-top so rank #1 appears at the top.
    """
    bar_color = color or COLORS["primary"]

    subset = df.nlargest(top_n, x_col)
    sorted_df = subset.sort_values(x_col, ascending=True)

    labels = sorted_df[y_col].tolist()
    values = sorted_df[x_col].tolist()
    n = len(labels)

    row_height = 0.35
    fig_height = max(4, n * row_height + 1.5)

    with chart_figure(figsize=(10, fig_height)) as (fig, ax):
        y_pos = list(range(n))
        ax.barh(y_pos, values, color=bar_color, height=0.6)

        if show_values:
            for i, val in enumerate(values):
                ax.annotate(
                    _fmt_value(val, value_format),
                    xy=(val, i),
                    xytext=(4, 0),
                    textcoords="offset points",
                    fontsize=9,
                    color=COLORS["dark_text"],
                    va="center",
                )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.xaxis.set_visible(False)
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def lollipop_chart(
    df,
    x_col: str,
    y_col: str,
    title: str,
    *,
    color: str | None = None,
    top_n: int = 25,
    accent_n: int = 3,
    value_format: str = "${:,.0f}",
) -> Figure:
    """Lollipop chart (dot + stem line) for cleaner ranking visualization."""
    dot_color = color or COLORS["secondary"]

    subset = df.nlargest(top_n, x_col)
    sorted_df = subset.sort_values(x_col, ascending=True)

    labels = sorted_df[y_col].tolist()
    values = sorted_df[x_col].tolist()
    n = len(labels)

    if n == 0:
        return Figure()

    accent_n = min(accent_n, n)
    colors = [COLORS["neutral"]] * (n - accent_n) + [dot_color] * accent_n

    row_height = 0.35
    fig_height = max(4, n * row_height + 1.5)

    with chart_figure(figsize=(10, fig_height)) as (fig, ax):
        y_pos = list(range(n))

        ax.hlines(y=y_pos, xmin=0, xmax=values, color=COLORS["neutral"], linewidth=1.5)
        ax.scatter(values, y_pos, color=colors, s=80, zorder=5)

        for i, val in enumerate(values):
            ax.annotate(
                _fmt_value(val, value_format),
                xy=(val, i),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=9,
                color=COLORS["dark_text"],
                va="center",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.xaxis.set_visible(False)
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def line_trend(
    df,
    x_col: str,
    y_cols: list[str],
    title: str,
    *,
    colors: list[str] | None = None,
    y_format: str | None = None,
) -> Figure:
    """Multi-line trend chart for time series data."""
    line_colors = colors or CATEGORY_PALETTE

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        for idx, col in enumerate(y_cols):
            c = line_colors[idx % len(line_colors)]
            ax.plot(
                df[x_col],
                df[col],
                color=c,
                linewidth=2.5,
                marker="o",
                markersize=4,
                label=col,
            )

        if len(y_cols) > 1:
            ax.legend(loc="best", frameon=False)

        if len(df) > 12:
            ax.tick_params(axis="x", rotation=-45)

        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def stacked_bar(
    df,
    x_col: str,
    y_cols: list[str],
    title: str,
    *,
    colors: list[str] | None = None,
    as_percentage: bool = False,
) -> Figure:
    """Stacked bar chart for composition over categories."""
    bar_colors = colors or CATEGORY_PALETTE

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        if as_percentage:
            totals = df[y_cols].sum(axis=1).replace(0, 1)
            plot_data = df[y_cols].div(totals, axis=0) * 100
        else:
            plot_data = df[y_cols]

        x = np.arange(len(df))
        bottom = np.zeros(len(df))

        for idx, col in enumerate(y_cols):
            c = bar_colors[idx % len(bar_colors)]
            vals = plot_data[col].values
            ax.bar(x, vals, bottom=bottom, color=c, label=col, width=0.7)
            bottom += vals

        ax.set_xticks(x)
        x_labels = df[x_col].tolist()
        rotation = -45 if len(df) > 8 else 0
        ax.set_xticklabels(x_labels, rotation=rotation, ha="right" if rotation else "center")

        if as_percentage:
            ax.set_ylim(0, 100)
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=min(len(y_cols), 4))
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def donut_chart(
    labels: Sequence[str],
    values: Sequence[float],
    title: str,
    *,
    colors: list[str] | None = None,
    hole: float = 0.4,
) -> Figure:
    """Donut/pie chart for composition breakdowns."""
    fill_colors = colors or CATEGORY_PALETTE

    with chart_figure(figsize=(8, 6)) as (fig, ax):
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=fill_colors[: len(labels)],
            autopct="%1.1f%%",
            pctdistance=0.75,
            wedgeprops={"width": 1.0 - hole, "edgecolor": "white", "linewidth": 2},
            textprops={"fontsize": 9},
        )
        for t in autotexts:
            t.set_fontsize(8)

        ax.set_title(title, fontsize=16, fontweight="bold", loc="left", pad=20)

    return fig


def heatmap(
    df,
    title: str,
    *,
    colorscale: str = "Blues",
    fmt: str = ".0f",
) -> Figure:
    """Heatmap for matrix data (monthly ranks, correlations, etc)."""
    z_values = df.values
    x_labels = [str(c) for c in df.columns]
    y_labels = [str(i) for i in df.index]
    n_rows = len(y_labels)
    n_cols = len(x_labels)

    fig_height = max(4, n_rows * 0.4 + 2)

    with chart_figure(figsize=(max(8, n_cols * 0.8 + 3), fig_height)) as (fig, ax):
        im = ax.imshow(z_values, cmap=colorscale, aspect="auto")
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)

        ax.set_xticks(np.arange(n_cols))
        ax.set_yticks(np.arange(n_rows))
        ax.set_xticklabels(x_labels, fontsize=9, rotation=-45, ha="right")
        ax.set_yticklabels(y_labels, fontsize=9)

        # Text annotations
        vmax = np.nanmax(z_values) if z_values.size > 0 else 1
        for row_idx in range(n_rows):
            for col_idx in range(n_cols):
                val = z_values[row_idx, col_idx]
                text_color = "white" if val > vmax * 0.6 else COLORS["dark_text"]
                ax.text(
                    col_idx,
                    row_idx,
                    f"{val:{fmt}}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color,
                )

        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def bullet_chart(
    value: float,
    target: float,
    title: str,
    *,
    ranges: list[float] | None = None,
) -> Figure:
    """Bullet chart for KPI scorecards."""
    if ranges is None:
        ranges = [target * 0.5, target * 0.75, target * 1.2]

    ranges_sorted = sorted(ranges)
    max_val = max(ranges_sorted[-1], value) * 1.1

    with chart_figure(figsize=(8, 2)) as (fig, ax):
        # Background bands (widest to narrowest)
        band_colors = ["#EEEEEE", "#DDDDDD", "#CCCCCC"]
        band_widths = [max_val] + list(reversed(ranges_sorted))
        for bw, bc in zip(band_widths, band_colors):
            ax.barh(0, bw, height=0.6, color=bc)

        # Actual value bar
        ax.barh(0, value, height=0.3, color=COLORS["primary"])

        # Target marker
        ax.plot(
            [target, target],
            [-0.35, 0.35],
            color=COLORS["negative"],
            linewidth=3,
            zorder=10,
        )

        ax.set_xlim(0, max_val)
        ax.set_yticks([])
        ax.xaxis.set_visible(False)
        ax.set_title(title, fontsize=14, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def scatter_plot(
    df,
    x_col: str,
    y_col: str,
    title: str,
    *,
    size_col: str | None = None,
    color_col: str | None = None,
    hover_col: str | None = None,
) -> Figure:
    """Scatter plot with optional bubble sizing and color encoding."""
    with chart_figure(figsize=(10, 6)) as (fig, ax):
        sizes = 50
        if size_col is not None:
            s_vals = df[size_col].fillna(0)
            max_s = s_vals.max() if s_vals.max() > 0 else 1
            sizes = (s_vals / max_s * 400 + 20).values

        point_colors = COLORS["primary"]
        if color_col is not None:
            unique_vals = df[color_col].unique()
            color_map = {
                v: CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)]
                for i, v in enumerate(unique_vals)
            }
            point_colors = df[color_col].map(color_map).tolist()
            # Legend entries
            for val, c in color_map.items():
                ax.scatter([], [], color=c, s=50, label=str(val))
            ax.legend(loc="best", frameon=False)

        ax.scatter(
            df[x_col],
            df[y_col],
            s=sizes,
            c=point_colors,
            alpha=0.7,
            edgecolors="white",
            linewidth=0.5,
        )

        # Text labels if hover_col provided
        if hover_col is not None:
            for _, row in df.iterrows():
                ax.annotate(
                    str(row[hover_col]),
                    xy=(row[x_col], row[y_col]),
                    fontsize=7,
                    ha="center",
                    va="bottom",
                    alpha=0.8,
                )

        ax.set_xlabel(x_col, fontsize=11)
        ax.set_ylabel(y_col, fontsize=11)
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def grouped_bar(
    df,
    x_col: str,
    y_cols: list[str],
    title: str,
    *,
    colors: list[str] | None = None,
) -> Figure:
    """Side-by-side grouped bar chart for comparing metrics across categories."""
    bar_colors = colors or CATEGORY_PALETTE
    n_groups = len(df)
    n_bars = len(y_cols)

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        x = np.arange(n_groups)
        total_width = 0.7
        bar_width = total_width / n_bars

        for idx, col in enumerate(y_cols):
            c = bar_colors[idx % len(bar_colors)]
            offset = (idx - n_bars / 2 + 0.5) * bar_width
            ax.bar(x + offset, df[col], width=bar_width, color=c, label=col)

        ax.set_xticks(x)
        x_labels = df[x_col].tolist()
        rotation = -45 if n_groups > 8 else 0
        ax.set_xticklabels(x_labels, rotation=rotation, ha="right" if rotation else "center")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=min(n_bars, 4))
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig


def waterfall_chart(
    categories: Sequence[str],
    values: Sequence[float],
    title: str,
) -> Figure:
    """Waterfall chart for showing composition or sequential changes."""
    n = len(categories)
    if n == 0:
        return Figure()

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        cumulative = 0.0
        bottoms = []
        heights = []
        bar_colors = []

        for i, val in enumerate(values):
            if i == n - 1:
                # Total bar starts from zero
                bottoms.append(0)
                heights.append(val)
                bar_colors.append(COLORS["primary"])
            else:
                if val >= 0:
                    bottoms.append(cumulative)
                    heights.append(val)
                    bar_colors.append(COLORS["positive"])
                else:
                    bottoms.append(cumulative + val)
                    heights.append(abs(val))
                    bar_colors.append(COLORS["negative"])
                cumulative += val

        x = np.arange(n)
        ax.bar(x, heights, bottom=bottoms, color=bar_colors, width=0.6)

        # Value labels
        for i, val in enumerate(values):
            y_pos = bottoms[i] + heights[i]
            text = format_currency(val) if i == n - 1 else f"+{format_currency(val)}" if val >= 0 else format_currency(val)
            ax.annotate(
                text,
                xy=(i, y_pos),
                xytext=(0, 4),
                textcoords="offset points",
                fontsize=9,
                ha="center",
                va="bottom",
            )

        # Connector lines
        for i in range(n - 2):
            top = bottoms[i] + heights[i] if values[i] >= 0 else bottoms[i]
            ax.plot(
                [i + 0.3, i + 0.7],
                [cumulative if i == n - 3 else bottoms[i] + (values[i] if values[i] >= 0 else 0)] * 2,
                color=COLORS["neutral"],
                linewidth=1,
                linestyle=":",
            )

        ax.set_xticks(x)
        rotation = -45 if n > 8 else 0
        ax.set_xticklabels(
            list(categories), rotation=rotation, ha="right" if rotation else "center"
        )
        ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
        fig.tight_layout()

    return fig
