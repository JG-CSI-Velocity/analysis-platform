"""M5: Merchant trend charts (consultant style)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import (
    ACCENT,
    ACCENT_SECONDARY,
    CORAL,
    GRAY_BASE,
    TEAL,
    insight_title,
)
from txn_analysis.settings import ChartConfig


def chart_rank_trajectory(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Monthly rank trajectory: top 3 colored, rest gray with direct labels."""
    df = result.df
    if df.empty:
        return go.Figure()

    month_cols = [c for c in df.columns if len(c) == 7 and c[4:5] == "-"]
    if not month_cols:
        return go.Figure()

    fig = go.Figure()
    top_merchants = df.head(10)
    accent_colors = [ACCENT, CORAL, TEAL]

    for idx, (_, row) in enumerate(top_merchants.iterrows()):
        name = row["merchant_consolidated"]
        ranks = [row[m] if row[m] > 0 else None for m in month_cols]
        is_top3 = idx < 3

        fig.add_trace(
            go.Scatter(
                x=month_cols,
                y=ranks,
                mode="lines+markers" if is_top3 else "lines",
                name=name[:30],
                line=dict(
                    color=accent_colors[idx] if is_top3 else GRAY_BASE,
                    width=2.5 if is_top3 else 1,
                    shape="spline",
                    smoothing=1.3,
                ),
                marker=dict(size=7) if is_top3 else None,
                opacity=1.0 if is_top3 else 0.4,
                connectgaps=False,
                showlegend=False,
            )
        )

        # Direct label at endpoint for top 3
        if is_top3:
            last_rank = None
            for m in reversed(month_cols):
                if row[m] > 0:
                    last_rank = row[m]
                    last_month = m
                    break
            if last_rank is not None:
                fig.add_annotation(
                    x=last_month,
                    y=last_rank,
                    text=f"  {name[:20]}",
                    showarrow=False,
                    font=dict(size=10, color=accent_colors[idx]),
                    xanchor="left",
                )

    fig.update_layout(
        title=insight_title(
            "Merchant Rank Trajectory",
            f"Top 10 merchants across {len(month_cols)} months",
        ),
        xaxis_title="Month",
        yaxis=dict(title="Rank", autorange="reversed"),
        template=config.theme,
        width=config.width + 100,
        height=config.height + 50,
        margin=dict(l=60, r=180, t=80, b=40),
    )

    return fig


def chart_growth_leaders(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Growth leaders and decliners as a diverging bar chart."""
    df = result.df
    if df.empty:
        return go.Figure()

    if "spend_change_pct" not in df.columns:
        return go.Figure()

    growers = df[df["spend_change_pct"] > 0].head(15)
    decliners = df[df["spend_change_pct"] < 0].tail(15)
    combined = pd.concat([growers, decliners]).sort_values("spend_change_pct")

    fig = go.Figure(
        go.Bar(
            x=combined["spend_change_pct"].tolist(),
            y=combined["merchant_consolidated"].tolist(),
            orientation="h",
            marker_color=[ACCENT if v >= 0 else CORAL for v in combined["spend_change_pct"]],
            text=[f"{v:+.1f}%" for v in combined["spend_change_pct"]],
            textposition="outside",
            textfont_size=9,
        )
    )

    n_growers = len(growers)
    n_decliners = len(decliners)
    fig.update_layout(
        title=insight_title(
            f"{n_growers} growing, {n_decliners} declining merchants",
            "Month-over-month spend change",
        ),
        xaxis_title="Spend Change %",
        template=config.theme,
        width=config.width,
        height=max(config.height, len(combined) * 24),
        margin=dict(l=200, r=80, t=80, b=40),
    )

    return fig


def chart_cohort_summary(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """New vs declining merchants stacked bar by month."""
    df = result.df
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    cohort_cols = [c for c in df.columns if c not in ("year_month",)]
    colors = {
        "new_merchants": ACCENT,
        "lost_merchants": CORAL,
        "returning_merchants": ACCENT_SECONDARY,
    }

    for col in cohort_cols:
        if col in df.columns:
            fig.add_trace(
                go.Bar(
                    x=df["year_month"].tolist(),
                    y=df[col].tolist(),
                    name=col.replace("_", " ").title(),
                    marker_color=colors.get(col, GRAY_BASE),
                )
            )

    fig.update_layout(
        barmode="group",
        title=insight_title("New vs Declining Merchants by Month"),
        xaxis_title="Month",
        yaxis_title="Count",
        template=config.theme,
        width=config.width,
        height=config.height,
        margin=dict(l=60, r=40, t=80, b=40),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
    )

    return fig
