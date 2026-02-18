"""Charts for portfolio analyses: Engagement Decay, Net Growth, Concentration."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_engagement_decay(df, config: ChartConfig) -> go.Figure:
    """Stacked bar of engagement decay categories."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Decay Category"],
            y=df["Count"],
            marker_color=colors[: len(df)],
            text=df["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Category",
        yaxis_title="Account Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_net_portfolio_growth(df, config: ChartConfig) -> go.Figure:
    """Dual-axis: bars for net opens/closes + cumulative line."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=df["Opens"],
            name="Opens",
            marker_color=colors[0],
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=-df["Closes"],
            name="Closes",
            marker_color=colors[4] if len(colors) > 4 else colors[-1],
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Cumulative"],
            name="Cumulative",
            mode="lines+markers",
            marker=dict(color=colors[2], size=6),
            line=dict(color=colors[2], width=2),
            yaxis="y2",
        )
    )

    fig.update_layout(
        template=config.theme,
        barmode="relative",
        xaxis_title="Month",
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Opens / Closes"),
        yaxis2=dict(title="Cumulative Net", side="right", overlaying="y"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_concentration(df, config: ChartConfig) -> go.Figure:
    """Bar chart showing spend share by percentile."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Percentile"],
            y=pd.to_numeric(df["Spend Share %"], errors="coerce"),
            marker_color=colors[: len(df)],
            text=df["Spend Share %"].apply(
                lambda v: f"{v:.1f}%" if isinstance(v, (int, float)) else str(v)
            ),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Percentile",
        yaxis_title="% of Total Spend",
        **LAYOUT_DEFAULTS,
    )
    return fig
