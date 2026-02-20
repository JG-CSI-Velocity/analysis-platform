"""Charts for activity analyses (ax22-ax26)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_activity_by_source(df, config: ChartConfig) -> go.Figure:
    """ax23: Grouped bar of activation rate + avg swipes by Source."""
    data = df[df["Source"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data["Source"],
            y=data["Count"],
            name="Count",
            marker_color=colors[0],
            yaxis="y",
        )
    )

    if "Activation Rate" in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data["Source"],
                y=pd.to_numeric(data["Activation Rate"], errors="coerce"),
                name="Activation Rate",
                mode="lines+markers",
                marker=dict(color=colors[3], size=8),
                line=dict(color=colors[3], width=2),
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Source",
        yaxis=dict(title="Count", side="left"),
        yaxis2=dict(
            title="Activation Rate",
            side="right",
            overlaying="y",
            range=[0, 1.1],
            tickformat=".0%",
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_activity_by_balance(df, config: ChartConfig) -> go.Figure:
    """ax24: Grouped bar of count + activation rate by Balance Tier."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Balance Tier"],
            y=df["Count"],
            name="Count",
            marker_color=colors[0],
            yaxis="y",
        )
    )

    if "Activation Rate" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Balance Tier"],
                y=pd.to_numeric(df["Activation Rate"], errors="coerce"),
                name="Activation Rate",
                mode="lines+markers",
                marker=dict(color=colors[2], size=8),
                line=dict(color=colors[2], width=2),
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Balance Tier",
        yaxis=dict(title="Count", side="left"),
        yaxis2=dict(
            title="Activation Rate",
            side="right",
            overlaying="y",
            range=[0, 1.1],
            tickformat=".0%",
        ),
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_activity_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax25: Horizontal bar of activation rate by Branch."""
    data = df[df["Branch"] != "Total"].copy()
    colors = config.colors

    if "Activation %" not in data.columns:
        data["Activation %"] = 0

    data = data.sort_values("Activation %", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=data["Branch"].astype(str),
            x=pd.to_numeric(data["Activation %"], errors="coerce"),
            orientation="h",
            marker_color=colors[2],
            text=data["Activation %"].apply(
                lambda v: f"{v:.1%}" if isinstance(v, (int, float)) else str(v)
            ),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Activation %",
        xaxis=dict(tickformat=".0%"),
        yaxis_title="Branch",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_monthly_trends(df, config: ChartConfig) -> go.Figure:
    """ax26: Line chart of monthly swipes, spend, and active accounts."""
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


def chart_activity_source_comparison(df, config: ChartConfig) -> go.Figure:
    """ax63: Grouped horizontal bars comparing DM vs Referral KPIs."""
    # Select numeric metrics for chart (skip Total Accounts row)
    chart_metrics = [
        "% Active",
        "Avg Swipes / Account",
        "Avg Spend / Account",
        "Avg Swipes / Active",
        "Avg Spend / Active",
    ]
    data = df[df["Metric"].isin(chart_metrics)].copy()

    if data.empty:
        return go.Figure()

    dm_navy = "#1B365D"
    ref_teal = "#1ABC9C"

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=data["Metric"],
            x=pd.to_numeric(data["DM"], errors="coerce"),
            name="DM",
            orientation="h",
            marker_color=dm_navy,
        )
    )

    fig.add_trace(
        go.Bar(
            y=data["Metric"],
            x=pd.to_numeric(data["Referral"], errors="coerce"),
            name="Referral",
            orientation="h",
            marker_color=ref_teal,
        )
    )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Value",
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(reversed(chart_metrics)),
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_monthly_interchange(df, config: ChartConfig) -> go.Figure:
    """ax71: Line chart of monthly interchange revenue."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=df["Total Spend"],
            name="Total Spend",
            marker_color=colors[1],
            opacity=0.4,
            yaxis="y",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Est. Interchange"],
            name="Est. Interchange",
            mode="lines+markers",
            marker=dict(color=colors[0], size=8),
            line=dict(color=colors[0], width=3),
            yaxis="y2",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Month",
        yaxis=dict(title="Total Spend ($)", side="left", tickprefix="$", tickformat=",.0f"),
        yaxis2=dict(
            title="Est. Interchange ($)",
            side="right",
            overlaying="y",
            tickprefix="$",
            tickformat=",.0f",
        ),
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_business_vs_personal(df, config: ChartConfig) -> go.Figure:
    """ax72: Grouped bars comparing Business vs Personal KPIs."""
    chart_metrics = [
        "% Active",
        "Avg Swipes / Account",
        "Avg Spend / Account",
        "Avg Swipes / Active",
        "Avg Spend / Active",
    ]
    data = df[df["Metric"].isin(chart_metrics)].copy()

    if data.empty:
        return go.Figure()

    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=data["Metric"],
            x=pd.to_numeric(data["Business"], errors="coerce"),
            name="Business",
            orientation="h",
            marker_color=colors[0],
        )
    )

    fig.add_trace(
        go.Bar(
            y=data["Metric"],
            x=pd.to_numeric(data["Personal"], errors="coerce"),
            name="Personal",
            orientation="h",
            marker_color=colors[2],
        )
    )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Value",
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(reversed(chart_metrics)),
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig
