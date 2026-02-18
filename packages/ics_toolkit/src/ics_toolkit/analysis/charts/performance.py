"""Charts for performance analyses: Days to First Use, Branch Performance Index."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_days_to_first_use(df, config: ChartConfig) -> go.Figure:
    """Histogram-style bar of days-to-first-use buckets."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Days Bucket"],
            y=df["Count"],
            marker_color=colors[0],
            text=df["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Days to First Use",
        yaxis_title="Account Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_branch_performance_index(df, config: ChartConfig) -> go.Figure:
    """Radar/spider chart of branch performance indices."""
    colors = config.colors
    categories = [
        "Activation Index",
        "Swipes Index",
        "Spend Index",
        "Balance Index",
    ]

    fig = go.Figure()

    for i, (_, row) in enumerate(df.head(8).iterrows()):
        values = [row.get(c, 100) for c in categories]
        values.append(values[0])  # close the polygon

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                name=str(row["Branch"]),
                line=dict(color=colors[i % len(colors)]),
                fill="toself",
                opacity=0.3,
            )
        )

    fig.update_layout(
        template=config.theme,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(200, df[categories].max().max() + 20)]),
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig
