"""Charts for strategic analyses: Activation Funnel and Revenue Impact."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_activation_funnel(df, config: ChartConfig) -> go.Figure:
    """Funnel chart showing account activation pipeline."""
    fig = go.Figure(
        go.Funnel(
            y=df["Stage"],
            x=df["Count"],
            textinfo="value+percent initial",
            marker=dict(color=config.colors[: len(df)]),
        )
    )

    fig.update_layout(
        template=config.theme,
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_revenue_impact(df, config: ChartConfig) -> go.Figure:
    """Bar chart of key revenue KPIs."""
    colors = config.colors

    # Extract numeric metrics (skip count)
    revenue_metrics = []
    for _, row in df.iterrows():
        metric = str(row["Metric"])
        value = row["Value"]
        if "Count" not in metric and isinstance(value, (int, float)):
            revenue_metrics.append((metric, float(value)))

    if not revenue_metrics:
        fig = go.Figure()
        fig.add_annotation(text="No revenue data available", showarrow=False)
        return fig

    labels = [m[0] for m in revenue_metrics]
    values = [m[1] for m in revenue_metrics]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors[: len(values)],
            text=[f"${v:,.0f}" for v in values],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        yaxis_title="USD",
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        xaxis=dict(tickangle=-25),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_revenue_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax65: Horizontal bar chart of interchange by branch."""
    data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df
    colors = config.colors

    data = data.sort_values("Est. Interchange", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=data["Branch"].astype(str),
            x=data["Est. Interchange"],
            orientation="h",
            marker_color=colors[0],
            text=data["Est. Interchange"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Estimated Interchange ($)",
        xaxis=dict(tickprefix="$", tickformat=",.0f"),
        yaxis_title="Branch",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_revenue_by_source(df, config: ChartConfig) -> go.Figure:
    """ax66: Bar chart of interchange by source channel."""
    data = df[df["Source"] != "Total"].copy() if "Source" in df.columns else df
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=data["Source"],
            y=data["Est. Interchange"],
            marker_color=colors[: len(data)],
            text=data["Est. Interchange"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Source",
        yaxis_title="Estimated Interchange ($)",
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        **LAYOUT_DEFAULTS,
    )
    return fig
