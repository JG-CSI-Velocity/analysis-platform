"""Charts for DM source deep-dive analyses (ax45-ax52)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_dm_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax46: Horizontal bar of DM count by Branch with debit % as text."""
    data = df[df["Branch"] != "Total"].copy()
    colors = config.colors

    data = data.sort_values("Count", ascending=True)

    # Build text labels: "123 (45.0% debit)"
    text_labels = data.apply(
        lambda r: (
            f"{int(r['Count'])}  ({r['Debit %']:.1f}% debit)"
            if "Debit %" in data.columns and pd.notna(r.get("Debit %"))
            else str(int(r["Count"]))
        ),
        axis=1,
    )

    fig = go.Figure(
        go.Bar(
            y=data["Branch"].astype(str),
            x=data["Count"],
            orientation="h",
            marker_color=colors[0],
            text=text_labels,
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        yaxis_title="Branch",
        xaxis_title="DM Account Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_dm_by_year(df, config: ChartConfig) -> go.Figure:
    """ax49: Vertical bar of DM count by Year Opened."""
    data = df[df["Year Opened"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=data["Year Opened"].astype(str),
            y=data["Count"],
            marker_color=colors[0],
            text=data["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Year Opened",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_dm_activity_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax51: Grouped bar of count + activation rate by Branch."""
    data = df[df["Branch"] != "Total"].copy()
    colors = config.colors

    data = data.sort_values("Count", ascending=False)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data["Branch"].astype(str),
            y=data["Count"],
            name="Count",
            marker_color=colors[0],
            yaxis="y",
        )
    )

    if "Activation %" in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data["Branch"].astype(str),
                y=pd.to_numeric(data["Activation %"], errors="coerce"),
                name="Activation %",
                mode="lines+markers",
                marker=dict(color=colors[3], size=8),
                line=dict(color=colors[3], width=2),
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Branch",
        yaxis=dict(title="Count", side="left"),
        yaxis2=dict(
            title="Activation %",
            side="right",
            overlaying="y",
            range=[0, 105],
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_dm_monthly_trends(df, config: ChartConfig) -> go.Figure:
    """ax52: Dual-axis line of Swipes + Spend over L12M."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Total Swipes"],
            name="Total Swipes",
            mode="lines+markers",
            marker=dict(color=colors[0], size=6),
            line=dict(color=colors[0], width=2),
            yaxis="y",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Active Accounts"],
            name="Active Accounts",
            mode="lines+markers",
            marker=dict(color=colors[2], size=6),
            line=dict(color=colors[2], width=2),
            yaxis="y",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Total Spend"],
            name="Total Spend",
            mode="lines+markers",
            marker=dict(color=colors[3], size=6),
            line=dict(color=colors[3], width=2, dash="dash"),
            yaxis="y2",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Month",
        yaxis=dict(title="Swipes / Active Accounts", side="left"),
        yaxis2=dict(title="Total Spend ($)", side="right", overlaying="y"),
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig
