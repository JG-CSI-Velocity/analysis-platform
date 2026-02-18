"""M6: Competitor analysis charts (consultant style)."""

from __future__ import annotations

import plotly.graph_objects as go

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import ACCENT, CORAL, GRAY_BASE, TEAL, insight_title
from txn_analysis.settings import ChartConfig

# Navy sequential colorscale for heatmaps and scatter
_NAVY_SCALE = [
    [0.0, "#E8E8E8"],
    [0.25, "#B0C4DE"],
    [0.5, "#6699CC"],
    [0.75, "#005EB8"],
    [1.0, "#051C2C"],
]


def chart_threat_scatter(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Competitor threat scatter: penetration vs spend, sized by growth."""
    df = result.df
    if df.empty:
        return go.Figure()

    fig = go.Figure(
        go.Scatter(
            x=df["penetration_pct"].tolist(),
            y=(
                df["total_spend"].tolist()
                if "total_spend" in df.columns
                else df["threat_score"].tolist()
            ),
            mode="markers+text",
            text=df["competitor"].tolist(),
            textposition="top center",
            textfont_size=9,
            marker=dict(
                size=[max(8, min(40, abs(g) + 10)) for g in df["growth_rate"]],
                color=df["threat_score"].tolist(),
                colorscale=_NAVY_SCALE,
                showscale=True,
                colorbar=dict(title="Threat Score"),
            ),
        )
    )

    # Quadrant annotations
    quadrants = [
        (0.02, 0.98, "Monitor", "#888888"),
        (0.98, 0.98, "High Threat", CORAL),
        (0.02, 0.02, "Low Priority", GRAY_BASE),
        (0.98, 0.02, "Watch", ACCENT),
    ]
    for qx, qy, label, color in quadrants:
        fig.add_annotation(
            text=label,
            xref="paper",
            yref="paper",
            x=qx,
            y=qy,
            showarrow=False,
            font=dict(size=11, color=color),
            xanchor="left" if qx < 0.5 else "right",
            yanchor="top" if qy > 0.5 else "bottom",
            opacity=0.6,
        )

    fig.update_layout(
        title=insight_title("Competitor Threat Assessment"),
        xaxis_title="Account Penetration (%)",
        yaxis_title="Threat Score",
        template=config.theme,
        width=config.width,
        height=config.height,
        margin=dict(l=60, r=60, t=80, b=40),
    )

    return fig


def chart_segmentation_bar(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Competitor account segmentation stacked bar."""
    df = result.df
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    segment_colors = {
        "Heavy": CORAL,
        "Balanced": ACCENT,
        "CU-Focused": TEAL,
    }

    for segment in ["Heavy", "Balanced", "CU-Focused"]:
        seg_data = df[df["segment"] == segment]
        if not seg_data.empty:
            fig.add_trace(
                go.Bar(
                    y=(
                        seg_data["competitor"].tolist()
                        if "competitor" in seg_data.columns
                        else seg_data.index.tolist()
                    ),
                    x=seg_data["account_count"].tolist(),
                    name=segment,
                    orientation="h",
                    marker_color=segment_colors.get(segment, GRAY_BASE),
                )
            )

    fig.update_layout(
        barmode="stack",
        title=insight_title("Competitor Account Segmentation"),
        xaxis_title="Account Count",
        template=config.theme,
        width=config.width,
        height=max(config.height, 400),
        margin=dict(l=180, r=40, t=80, b=40),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
    )

    return fig


def chart_competitor_heatmap(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Top 20 competitor spend heatmap by category."""
    df = result.df
    if df.empty:
        return go.Figure()

    if "category" not in df.columns or "pct_of_competitor_spend" not in df.columns:
        return go.Figure()

    if "competitor" not in df.columns:
        return go.Figure()

    pivot = df.pivot_table(
        index="competitor",
        columns="category",
        values="pct_of_competitor_spend",
        fill_value=0,
    )

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=_NAVY_SCALE,
            text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont_size=10,
            colorbar=dict(title="% of Spend"),
        )
    )

    fig.update_layout(
        title=insight_title("Competitor Spend by Category"),
        template=config.theme,
        width=config.width + 200,
        height=max(config.height, len(pivot) * 28),
        margin=dict(l=180, r=60, t=80, b=80),
    )

    return fig
