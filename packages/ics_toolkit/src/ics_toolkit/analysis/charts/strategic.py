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
