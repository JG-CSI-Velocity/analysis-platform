"""Chart for R07: Code Health -- stacked bar by reliability tier."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_code_health(df, config: ChartConfig) -> go.Figure:
    """Stacked bar chart: code category distribution by Reliability tier."""
    data = df.copy()
    colors = config.colors

    # Group by Channel+Type, split by Reliability
    reliabilities = data["Reliability"].unique()
    data["Label"] = data["Channel"] + " / " + data["Type"]

    fig = go.Figure()
    for i, rel in enumerate(reliabilities):
        subset = data[data["Reliability"] == rel]
        fig.add_trace(
            go.Bar(
                x=subset["Label"],
                y=subset["Count"],
                name=rel,
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="stack",
        xaxis_title="Channel / Type",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig
