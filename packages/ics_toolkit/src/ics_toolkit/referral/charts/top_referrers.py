"""Chart for R01: Top Referrers -- horizontal bar by influence score."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_top_referrers(df, config: ChartConfig) -> go.Figure:
    """Horizontal bar chart of top referrers ranked by influence score."""
    data = df.sort_values("Influence Score", ascending=True).copy()

    fig = go.Figure(
        go.Bar(
            x=data["Influence Score"],
            y=data["Referrer"],
            orientation="h",
            marker_color=config.colors[0],
            text=data["Influence Score"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Influence Score",
        yaxis_title="Referrer",
        **LAYOUT_DEFAULTS,
    )
    return fig
