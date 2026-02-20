"""Charts for source analyses (ax08-ax13)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def _crosstab_data(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Strip Total row/col from a crosstab DataFrame; return (data, row_col_name)."""
    row_col = df.columns[0]
    data = df[df[row_col] != "Total"].copy()
    value_cols = [c for c in data.columns if c not in (row_col, "Total")]
    return data, row_col, value_cols


def chart_source_dist(df, config: ChartConfig) -> go.Figure:
    """ax08: Bar chart of ICS accounts by Source."""
    data = df[df["Source"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=data["Source"],
            y=data["Count"],
            marker_color=colors[0],
            text=data["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Source",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_source_by_stat(df, config: ChartConfig) -> go.Figure:
    """ax09: Stacked bar of Source x Stat Code."""
    data, row_col, value_cols = _crosstab_data(df)
    colors = config.colors

    fig = go.Figure()
    for i, col in enumerate(value_cols):
        fig.add_trace(
            go.Bar(
                x=data[row_col],
                y=pd.to_numeric(data[col], errors="coerce"),
                name=str(col),
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="stack",
        xaxis_title="Source",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_source_by_prod(df, config: ChartConfig) -> go.Figure:
    """ax10: Grouped bar of Source x Prod Code."""
    data, row_col, value_cols = _crosstab_data(df)
    colors = config.colors

    fig = go.Figure()
    for i, col in enumerate(value_cols):
        fig.add_trace(
            go.Bar(
                x=data[row_col],
                y=pd.to_numeric(data[col], errors="coerce"),
                name=str(col),
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Source",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_source_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax11: Heatmap of Source x Branch."""
    data, row_col, value_cols = _crosstab_data(df)

    z_data = data[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0).values

    fig = go.Figure(
        go.Heatmap(
            z=z_data,
            x=[str(c) for c in value_cols],
            y=data[row_col].tolist(),
            colorscale="Blues",
            text=z_data.astype(int),
            texttemplate="%{text}",
            textfont=dict(size=12),
        )
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Branch",
        yaxis_title="Source",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_account_type(df, config: ChartConfig) -> go.Figure:
    """ax12: Pie chart of Personal vs Business ICS accounts."""
    data = df[df["Business?"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Pie(
            labels=data["Business?"],
            values=data["Count"],
            marker=dict(colors=colors[: len(data)]),
            textinfo="label+percent+value",
            hole=0.35,
        )
    )

    fig.update_layout(template=config.theme, **LAYOUT_DEFAULTS)
    return fig


def chart_source_by_year(df, config: ChartConfig) -> go.Figure:
    """ax13: Stacked bar of Source by Year Opened."""
    data, row_col, value_cols = _crosstab_data(df)
    colors = config.colors

    # Sort year columns chronologically
    year_cols = sorted(value_cols, key=lambda c: str(c))

    fig = go.Figure()
    for i, col in enumerate(year_cols):
        fig.add_trace(
            go.Bar(
                x=data[row_col],
                y=pd.to_numeric(data[col], errors="coerce"),
                name=str(col),
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="stack",
        xaxis_title="Source",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_source_acquisition_mix(df, config: ChartConfig) -> go.Figure:
    """ax85: Stacked bar of monthly new account opens by source channel."""
    colors = config.colors
    source_cols = [c for c in df.columns if c not in ("Month", "Total")]

    fig = go.Figure()
    for i, col in enumerate(source_cols):
        fig.add_trace(
            go.Bar(
                x=df["Month"],
                y=pd.to_numeric(df[col], errors="coerce"),
                name=str(col),
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="stack",
        xaxis_title="Month",
        yaxis_title="New Accounts",
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig
