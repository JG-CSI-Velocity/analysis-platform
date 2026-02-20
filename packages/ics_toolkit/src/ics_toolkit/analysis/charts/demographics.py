"""Charts for demographics analyses (ax14-ax21)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_age_comparison(df, config: ChartConfig) -> go.Figure:
    """ax14: Bar chart of ICS account age distribution."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Age Range"],
            y=df["Count"],
            marker_color=colors[0],
            text=df["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Age Range",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_closures(df, config: ChartConfig) -> go.Figure:
    """ax15: Bar chart of closures by month."""
    data = df[df["Month Closed"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=data["Month Closed"],
            y=data["Count"],
            marker_color=colors[4],
            text=data["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Month Closed",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_balance_tiers(df, config: ChartConfig) -> go.Figure:
    """ax17: Bar chart of ICS accounts by Balance Tier."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Balance Tier"],
            y=df["Count"],
            marker_color=colors[1],
            text=df["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Balance Tier",
        yaxis_title="Count",
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_age_vs_balance(df, config: ChartConfig) -> go.Figure:
    """ax19: Dual-axis bar+line of account count and avg balance by age range."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Age Range"],
            y=df["Count"],
            name="Count",
            marker_color=colors[0],
            yaxis="y",
        )
    )

    if "Avg Curr Bal" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Age Range"],
                y=df["Avg Curr Bal"],
                name="Avg Balance",
                mode="lines+markers",
                marker=dict(color=colors[3], size=8),
                line=dict(color=colors[3], width=2),
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Age Range",
        yaxis=dict(title="Count", side="left"),
        yaxis2=dict(title="Avg Current Balance", side="right", overlaying="y"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_balance_tier_detail(df, config: ChartConfig) -> go.Figure:
    """ax20: Grouped bar of count + avg swipes/spend by balance tier."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Balance Tier"],
            y=df["Count"],
            name="Count",
            marker_color=colors[0],
        )
    )

    if "Avg Swipes" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df["Balance Tier"],
                y=df["Avg Swipes"],
                name="Avg Swipes",
                marker_color=colors[2],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Balance Tier",
        yaxis_title="Value",
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_open_vs_close(df, config: ChartConfig) -> go.Figure:
    """ax16: Bar chart of Open vs Closed counts."""
    colors = config.colors

    open_row = df[df["Metric"] == "Open (Stat Code O)"]
    closed_row = df[df["Metric"] == "Closed (Stat Code C)"]

    labels = []
    values = []
    if not open_row.empty:
        labels.append("Open")
        values.append(open_row["Value"].iloc[0])
    if not closed_row.empty:
        labels.append("Closed")
        values.append(closed_row["Value"].iloc[0])

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=[colors[0], colors[4]] if len(values) == 2 else colors[: len(values)],
            text=values,
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Status",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_stat_open_close(df, config: ChartConfig) -> go.Figure:
    """ax18: Grouped bar of count + line of avg balance by Stat Code."""
    data = df[~df["Stat Code"].isin(["Total", "Grand Total"])].copy()
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data["Stat Code"],
            y=data["Count"],
            name="Count",
            marker_color=colors[0],
            yaxis="y",
        )
    )

    if "Avg Curr Bal" in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data["Stat Code"],
                y=pd.to_numeric(data["Avg Curr Bal"], errors="coerce"),
                name="Avg Balance",
                mode="lines+markers",
                marker=dict(color=colors[3], size=8),
                line=dict(color=colors[3], width=2),
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Stat Code",
        yaxis=dict(title="Count", side="left"),
        yaxis2=dict(title="Avg Current Balance", side="right", overlaying="y"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_age_dist(df, config: ChartConfig) -> go.Figure:
    """ax21: Bar chart of ICS Stat O age distribution."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Age Range"],
            y=df["Count"],
            marker_color=colors[1],
            text=df["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Age Range",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_balance_trajectory(df, config: ChartConfig) -> go.Figure:
    """ax83: Grouped bar of Avg Bal vs Curr Bal by Branch."""
    data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data["Branch"].astype(str),
            y=pd.to_numeric(data["Avg Bal"], errors="coerce"),
            name="Avg Bal",
            marker_color=colors[1],
        )
    )

    fig.add_trace(
        go.Bar(
            x=data["Branch"].astype(str),
            y=pd.to_numeric(data["Curr Bal"], errors="coerce"),
            name="Curr Bal",
            marker_color=colors[0],
        )
    )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Branch",
        yaxis_title="Average Balance ($)",
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        **LAYOUT_DEFAULTS,
    )
    return fig
