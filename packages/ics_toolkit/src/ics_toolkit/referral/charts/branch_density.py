"""Chart for R06: Branch Influence Density -- vertical bar."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_branch_density(df, config: ChartConfig) -> go.Figure:
    """Vertical bar of avg influence score per branch, sorted descending."""
    data = df.sort_values("Avg Influence Score", ascending=False).copy()

    fig = go.Figure(
        go.Bar(
            x=data["Branch"],
            y=data["Avg Influence Score"],
            marker_color=config.colors[0],
            text=data["Avg Influence Score"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Branch",
        yaxis_title="Avg Influence Score",
        **LAYOUT_DEFAULTS,
    )
    return fig
