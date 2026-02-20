"""Generic chart builders for V4 storyline analyses.

Each builder returns a go.Figure themed with the 'v4_consultant' template.
Import chart constants (COLORS, palettes) from charts.theme.
"""

from __future__ import annotations

from collections.abc import Sequence

import plotly.graph_objects as go

from txn_analysis.charts.theme import (
    CATEGORY_PALETTE,
    COLORS,
    FONT_FAMILY,
    _fmt_value,
    ensure_theme,
    format_currency,
)

_V4_TEMPLATE = "v4_consultant"


def _themed_figure(*args, **kwargs) -> go.Figure:
    """Create a go.Figure with the V4 consultant template applied."""
    ensure_theme()
    fig = go.Figure(*args, **kwargs)
    fig.update_layout(template=_V4_TEMPLATE)
    return fig


# ---------------------------------------------------------------------------
# V4 Annotation Helpers
# ---------------------------------------------------------------------------


def insight_title(main: str, subtitle: str = "") -> dict:
    """Build a Plotly title dict with bold main text and gray subtitle."""
    if subtitle:
        text = (
            f"<b>{main}</b><br>"
            f"<span style='font-size:12px;color:#8B95A2;font-weight:normal'>"
            f"{subtitle}</span>"
        )
    else:
        text = f"<b>{main}</b>"

    return dict(
        text=text,
        font=dict(family=FONT_FAMILY, size=16, color=COLORS["primary"]),
        x=0.02,
        xanchor="left",
    )


def add_source_footer(
    fig: go.Figure,
    client_name: str = "",
    date_range: str = "",
) -> go.Figure:
    """Add a subtle source footer annotation at the bottom-left."""
    parts = ["Source:"]
    if client_name:
        parts.append(f"{client_name} transaction data")
    if date_range:
        parts.append(f"({date_range})")

    text = " ".join(parts) if len(parts) > 1 else ""
    if not text:
        return fig

    fig.add_annotation(
        text=text,
        xref="paper",
        yref="paper",
        x=0,
        y=-0.13,
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=9, color="#AAAAAA"),
        xanchor="left",
    )
    return fig


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
) -> go.Figure:
    """Horizontal bar chart for rankings (merchants, competitors, etc).

    Data is sorted descending by x_col and limited to top_n rows.
    Bars render bottom-to-top so rank #1 appears at the top.
    """
    bar_color = color or COLORS["primary"]

    subset = df.nlargest(top_n, x_col)
    sorted_df = subset.sort_values(x_col, ascending=True)

    labels = sorted_df[y_col].tolist()
    values = sorted_df[x_col].tolist()

    text_vals = [_fmt_value(v, value_format) for v in values] if show_values else None

    fig = _themed_figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=bar_color, line=dict(width=0)),
            text=text_vals,
            textposition="outside",
            textfont=dict(size=10, color=COLORS["dark_text"]),
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        )
    )

    row_height = max(22, 500 // max(len(labels), 1))
    chart_height = max(400, len(labels) * row_height + 120)

    fig.update_layout(
        title=dict(text=title),
        xaxis=dict(visible=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        margin=dict(l=200, r=100, t=80, b=40),
        height=chart_height,
        showlegend=False,
    )

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
) -> go.Figure:
    """Lollipop chart (dot + stem line) for cleaner ranking visualization.

    Top accent_n items receive the accent color; the rest are neutral gray.
    """
    dot_color = color or COLORS["secondary"]

    subset = df.nlargest(top_n, x_col)
    sorted_df = subset.sort_values(x_col, ascending=True)

    labels = sorted_df[y_col].tolist()
    values = sorted_df[x_col].tolist()
    n = len(labels)

    if n == 0:
        return go.Figure()

    accent_n = min(accent_n, n)
    colors = [COLORS["neutral"]] * (n - accent_n) + [dot_color] * accent_n

    stem_x: list[float | None] = []
    stem_y: list[str | None] = []
    for label, val in zip(labels, values):
        stem_x.extend([0, val, None])
        stem_y.extend([label, label, None])

    fig = _themed_figure()

    fig.add_trace(
        go.Scatter(
            x=stem_x,
            y=stem_y,
            mode="lines",
            line=dict(color=COLORS["neutral"], width=1.5),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=values,
            y=labels,
            mode="markers+text",
            marker=dict(size=10, color=colors),
            text=[_fmt_value(v, value_format) for v in values],
            textposition="middle right",
            textfont=dict(size=10, color=COLORS["dark_text"]),
            showlegend=False,
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    )

    row_height = max(22, 500 // max(n, 1))
    chart_height = max(400, n * row_height + 120)

    fig.update_layout(
        title=dict(text=title),
        xaxis=dict(visible=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        margin=dict(l=200, r=100, t=80, b=40),
        height=chart_height,
        showlegend=False,
    )

    return fig


def line_trend(
    df,
    x_col: str,
    y_cols: list[str],
    title: str,
    *,
    colors: list[str] | None = None,
    y_format: str | None = None,
) -> go.Figure:
    """Multi-line trend chart for time series data."""
    line_colors = colors or CATEGORY_PALETTE

    fig = _themed_figure()

    for idx, col in enumerate(y_cols):
        c = line_colors[idx % len(line_colors)]
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                mode="lines+markers",
                name=col,
                line=dict(color=c, width=2.5),
                marker=dict(size=5, color=c),
                hovertemplate="%{x}<br>" + col + ": %{y:,.0f}<extra></extra>",
            )
        )

    y_axis_opts: dict = dict(title=None)
    if y_format:
        y_axis_opts["tickformat"] = y_format

    fig.update_layout(
        title=dict(text=title),
        xaxis=dict(title=None, tickangle=-45 if len(df) > 12 else 0),
        yaxis=y_axis_opts,
        showlegend=len(y_cols) > 1,
        height=500,
    )

    return fig


def stacked_bar(
    df,
    x_col: str,
    y_cols: list[str],
    title: str,
    *,
    colors: list[str] | None = None,
    as_percentage: bool = False,
) -> go.Figure:
    """Stacked bar chart for composition over categories.

    When as_percentage=True, values are normalized to 100%.
    """
    bar_colors = colors or CATEGORY_PALETTE

    fig = _themed_figure()

    if as_percentage:
        totals = df[y_cols].sum(axis=1).replace(0, 1)
        plot_df = df[y_cols].div(totals, axis=0) * 100
    else:
        plot_df = df

    for idx, col in enumerate(y_cols):
        c = bar_colors[idx % len(bar_colors)]
        y_values = plot_df[col] if as_percentage else df[col]
        hover_fmt = "%{y:.1f}%" if as_percentage else "%{y:,.0f}"

        fig.add_trace(
            go.Bar(
                x=df[x_col],
                y=y_values,
                name=col,
                marker=dict(color=c, line=dict(width=0)),
                hovertemplate="%{x}<br>" + col + ": " + hover_fmt + "<extra></extra>",
            )
        )

    y_axis_opts: dict = dict(title=None)
    if as_percentage:
        y_axis_opts["ticksuffix"] = "%"
        y_axis_opts["range"] = [0, 100]

    fig.update_layout(
        barmode="stack",
        title=dict(text=title),
        xaxis=dict(title=None, tickangle=-45 if len(df) > 8 else 0),
        yaxis=y_axis_opts,
        height=500,
    )

    return fig


def donut_chart(
    labels: Sequence[str],
    values: Sequence[float],
    title: str,
    *,
    colors: list[str] | None = None,
    hole: float = 0.4,
) -> go.Figure:
    """Donut/pie chart for composition breakdowns."""
    fill_colors = colors or CATEGORY_PALETTE

    pull_values = [0.0] * len(values)
    if len(values) > 0:
        max_idx = max(range(len(values)), key=lambda i: values[i])
        pull_values[max_idx] = 0.04

    fig = _themed_figure(
        go.Pie(
            labels=list(labels),
            values=list(values),
            hole=hole,
            marker=dict(
                colors=fill_colors[: len(labels)],
                line=dict(color="white", width=2),
            ),
            pull=pull_values,
            textinfo="label+percent",
            textposition="outside",
            textfont=dict(size=11),
            hovertemplate="%{label}: %{value:,.0f} (%{percent})<extra></extra>",
            sort=False,
        )
    )

    fig.update_layout(
        title=dict(text=title),
        showlegend=False,
        height=500,
        margin=dict(l=40, r=40, t=80, b=60),
    )

    return fig


def heatmap(
    df,
    title: str,
    *,
    colorscale: str = "Blues",
    fmt: str = ".0f",
) -> go.Figure:
    """Heatmap for matrix data (monthly ranks, correlations, etc).

    DataFrame index becomes y-axis labels, columns become x-axis labels.
    """
    z_values = df.values.tolist()
    x_labels = [str(c) for c in df.columns]
    y_labels = [str(i) for i in df.index]

    annotations = []
    for row_idx, row in enumerate(z_values):
        for col_idx, val in enumerate(row):
            text = f"{val:{fmt}}" if val is not None else ""
            annotations.append(
                dict(
                    x=x_labels[col_idx],
                    y=y_labels[row_idx],
                    text=text,
                    showarrow=False,
                    font=dict(
                        size=10,
                        color="white"
                        if val and val > (max(max(r) for r in z_values) * 0.6)
                        else COLORS["dark_text"],
                    ),
                )
            )

    fig = _themed_figure(
        go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(thickness=15, len=0.8),
            hovertemplate="Row: %{y}<br>Col: %{x}<br>Value: %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=title),
        xaxis=dict(side="bottom", tickangle=-45 if len(x_labels) > 8 else 0),
        yaxis=dict(autorange="reversed"),
        annotations=annotations,
        height=max(400, len(y_labels) * 30 + 150),
        margin=dict(l=120, r=40, t=80, b=80),
    )

    return fig


def bullet_chart(
    value: float,
    target: float,
    title: str,
    *,
    ranges: list[float] | None = None,
) -> go.Figure:
    """Bullet chart for KPI scorecards.

    Shows a single KPI value against a target, with optional background
    ranges for poor/ok/good bands.
    """
    if ranges is None:
        ranges = [target * 0.5, target * 0.75, target * 1.2]

    ranges_sorted = sorted(ranges)

    fig = _themed_figure()

    band_colors = ["#EEEEEE", "#DDDDDD", "#CCCCCC"]
    prev = 0.0
    for idx, r in enumerate(ranges_sorted):
        fig.add_trace(
            go.Bar(
                x=[r - prev],
                y=[title],
                orientation="h",
                base=prev,
                marker=dict(color=band_colors[idx % len(band_colors)]),
                showlegend=False,
                hoverinfo="skip",
                width=0.6,
            )
        )
        prev = r

    fig.add_trace(
        go.Bar(
            x=[value],
            y=[title],
            orientation="h",
            marker=dict(color=COLORS["primary"]),
            showlegend=False,
            hovertemplate=f"Actual: {value:,.0f}<extra></extra>",
            width=0.3,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[target, target],
            y=[title, title],
            mode="markers",
            marker=dict(
                symbol="line-ns",
                size=20,
                line=dict(width=3, color=COLORS["negative"]),
                color=COLORS["negative"],
            ),
            showlegend=False,
            hovertemplate=f"Target: {target:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=title),
        barmode="overlay",
        xaxis=dict(
            showgrid=False,
            range=[0, max(ranges_sorted[-1], value) * 1.1],
        ),
        yaxis=dict(visible=False),
        height=180,
        margin=dict(l=20, r=40, t=60, b=40),
        showlegend=False,
    )

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
) -> go.Figure:
    """Scatter plot with optional bubble sizing and color encoding."""
    marker_opts: dict = dict(
        color=COLORS["primary"],
        size=8,
        opacity=0.7,
        line=dict(width=0.5, color="white"),
    )

    if size_col is not None:
        sizes = df[size_col].fillna(0)
        max_size = sizes.max() if sizes.max() > 0 else 1
        marker_opts["size"] = (sizes / max_size * 40 + 5).tolist()
        marker_opts["sizemode"] = "area"

    if color_col is not None:
        unique_vals = df[color_col].unique()
        color_map = {
            v: CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)] for i, v in enumerate(unique_vals)
        }
        marker_opts["color"] = df[color_col].map(color_map).tolist()

    hover_text = df[hover_col].tolist() if hover_col else None
    hover_tmpl = (
        "%{text}<br>" + x_col + ": %{x:,.0f}<br>" + y_col + ": %{y:,.0f}<extra></extra>"
        if hover_col
        else x_col + ": %{x:,.0f}<br>" + y_col + ": %{y:,.0f}<extra></extra>"
    )

    fig = _themed_figure(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="markers",
            marker=marker_opts,
            text=hover_text,
            hovertemplate=hover_tmpl,
            showlegend=False,
        )
    )

    fig.update_layout(
        title=dict(text=title),
        xaxis=dict(title=dict(text=x_col, font=dict(size=12))),
        yaxis=dict(title=dict(text=y_col, font=dict(size=12))),
        height=500,
    )

    if color_col is not None:
        unique_vals = df[color_col].unique()
        color_map = {
            v: CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)] for i, v in enumerate(unique_vals)
        }
        for val, c in color_map.items():
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker=dict(size=8, color=c),
                    name=str(val),
                    showlegend=True,
                )
            )
        fig.update_layout(showlegend=True)

    return fig


def grouped_bar(
    df,
    x_col: str,
    y_cols: list[str],
    title: str,
    *,
    colors: list[str] | None = None,
) -> go.Figure:
    """Side-by-side grouped bar chart for comparing metrics across categories."""
    bar_colors = colors or CATEGORY_PALETTE

    fig = _themed_figure()

    for idx, col in enumerate(y_cols):
        c = bar_colors[idx % len(bar_colors)]
        fig.add_trace(
            go.Bar(
                x=df[x_col],
                y=df[col],
                name=col,
                marker=dict(color=c, line=dict(width=0)),
                hovertemplate="%{x}<br>" + col + ": %{y:,.0f}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="group",
        title=dict(text=title),
        xaxis=dict(title=None, tickangle=-45 if len(df) > 8 else 0),
        yaxis=dict(title=None),
        height=500,
    )

    return fig


def waterfall_chart(
    categories: Sequence[str],
    values: Sequence[float],
    title: str,
) -> go.Figure:
    """Waterfall chart for showing composition or sequential changes.

    The last category is treated as the total.
    """
    n = len(categories)
    if n == 0:
        return go.Figure()

    measures = ["relative"] * (n - 1) + ["total"]

    text_values = []
    for i, val in enumerate(values):
        if measures[i] == "total":
            text_values.append(format_currency(val))
        elif val >= 0:
            text_values.append(f"+{format_currency(val)}")
        else:
            text_values.append(format_currency(val))

    fig = _themed_figure(
        go.Waterfall(
            x=list(categories),
            y=list(values),
            measure=measures,
            text=text_values,
            textposition="outside",
            textfont=dict(size=10),
            increasing=dict(marker=dict(color=COLORS["positive"])),
            decreasing=dict(marker=dict(color=COLORS["negative"])),
            totals=dict(marker=dict(color=COLORS["primary"])),
            connector=dict(line=dict(color=COLORS["neutral"], width=1, dash="dot")),
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=title),
        xaxis=dict(title=None, tickangle=-45 if n > 8 else 0),
        yaxis=dict(title=None, showgrid=True),
        showlegend=False,
        height=500,
    )

    return fig
