"""Chart for R05: Staff Multipliers -- grouped bar."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_staff_multipliers(df, config: ChartConfig) -> go.Figure:
    """Grouped bar: multiplier score (primary) and referrals processed (secondary)."""
    data = df.sort_values("Multiplier Score", ascending=False).copy()
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data["Staff"],
            y=data["Multiplier Score"],
            name="Multiplier Score",
            marker_color=colors[0],
            yaxis="y",
        )
    )

    if "Referrals Processed" in data.columns:
        fig.add_trace(
            go.Bar(
                x=data["Staff"],
                y=data["Referrals Processed"],
                name="Referrals Processed",
                marker_color=colors[1],
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Staff",
        yaxis=dict(title="Multiplier Score"),
        yaxis2=dict(title="Referrals Processed", overlaying="y", side="right"),
        **LAYOUT_DEFAULTS,
    )
    return fig
