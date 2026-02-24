"""M15: Recurring payment charts."""

from __future__ import annotations

import plotly.graph_objects as go

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import ACCENT, ACCENT_SECONDARY, insight_title
from txn_analysis.settings import ChartConfig


def chart_recurring_merchants(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Top recurring merchants by account count."""
    df = result.df
    if df.empty or "Merchant" not in df.columns:
        return go.Figure()

    data = df.head(20).sort_values("Recurring Accounts", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=data["Recurring Accounts"].tolist(),
            y=data["Merchant"].tolist(),
            orientation="h",
            marker_color=ACCENT,
            text=data["Recurring Accounts"].tolist(),
            textposition="outside",
            textfont_size=9,
        )
    )
    fig.update_layout(
        title=insight_title(
            "Top Recurring Merchants",
            f"{len(result.df)} merchants with 3+ month relationships",
        ),
        xaxis_title="Accounts with Recurring Relationship",
        template=config.theme,
        width=config.width,
        height=max(config.height, len(data) * 24),
        margin=dict(l=200, r=80, t=80, b=40),
    )
    return fig


def chart_recurring_onsets(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """New recurring relationships by month -- when subscriptions start."""
    onsets = result.data.get("onsets")
    if onsets is None or onsets.empty:
        return go.Figure()

    fig = go.Figure()

    # Bar: new recurring relationships count
    fig.add_trace(
        go.Bar(
            x=onsets["Month"].tolist(),
            y=onsets["New Recurring Relationships"].tolist(),
            name="New Recurring",
            marker_color=ACCENT,
            text=onsets["New Recurring Relationships"].tolist(),
            textposition="outside",
            textfont_size=10,
        )
    )

    # Line: spend at onset on secondary y-axis
    if onsets["Spend at Onset"].sum() > 0:
        fig.add_trace(
            go.Scatter(
                x=onsets["Month"].tolist(),
                y=onsets["Spend at Onset"].tolist(),
                name="Spend at Onset",
                mode="lines+markers",
                line=dict(color=ACCENT_SECONDARY, width=2),
                marker=dict(size=6),
                yaxis="y2",
            )
        )

    total = int(onsets["New Recurring Relationships"].sum())
    fig.update_layout(
        title=insight_title(
            "New Recurring Relationships by Month",
            f"{total} total new subscriptions detected across {len(onsets)} months",
        ),
        xaxis_title="Month",
        yaxis=dict(title="New Relationships"),
        yaxis2=dict(
            title="Spend ($)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        template=config.theme,
        width=config.width,
        height=config.height,
        margin=dict(l=60, r=80, t=80, b=40),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
    )

    return fig
