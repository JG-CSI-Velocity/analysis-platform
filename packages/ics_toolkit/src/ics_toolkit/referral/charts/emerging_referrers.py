"""Chart for R02: Emerging Referrers -- scatter timeline."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_emerging_referrers(df, config: ChartConfig) -> go.Figure:
    """Scatter plot: Referrer (y) x First Referral date (x), size = Burst Count."""
    data = df.copy()
    marker_size = data["Burst Count"].clip(lower=1) * 8

    fig = go.Figure(
        go.Scatter(
            x=data["First Referral"],
            y=data["Referrer"],
            mode="markers",
            marker=dict(
                size=marker_size,
                color=data["Influence Score"],
                colorscale="Blues",
                showscale=True,
                colorbar=dict(title="Score"),
            ),
            text=data.apply(
                lambda r: f"Score: {r['Influence Score']}<br>Bursts: {r['Burst Count']}",
                axis=1,
            ),
            hoverinfo="text+y",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="First Referral Date",
        yaxis_title="Referrer",
        **LAYOUT_DEFAULTS,
    )
    return fig
