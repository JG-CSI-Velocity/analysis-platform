"""M9: Bullet chart for portfolio scorecard KPIs (consultant style)."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import ACCENT, CORAL, insight_title
from txn_analysis.settings import ChartConfig

# KPIs that have PULSE benchmarks (row indices by metric name)
_BENCHMARK_KPIS = [
    "Avg Spend/Account/Month",
    "Avg Txn/Account/Month",
    "Average Ticket",
]

# Qualitative band shades (poor -> acceptable -> good)
_BAND_COLORS = ["#F0F0F0", "#E0E0E0", "#D0D0D0"]


def chart_scorecard_bullets(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Horizontal bullet charts for 3 KPIs with PULSE benchmarks."""
    df = result.df
    if df.empty:
        return go.Figure()

    # Filter to only KPIs with numeric benchmarks
    kpi_rows = df[
        (df["metric"].isin(_BENCHMARK_KPIS)) & (df["benchmark"] != "") & (df["benchmark"].notna())
    ]
    if kpi_rows.empty:
        return go.Figure()

    n_kpis = len(kpi_rows)
    fig = make_subplots(
        rows=n_kpis,
        cols=1,
        subplot_titles=[row["metric"] for _, row in kpi_rows.iterrows()],
        vertical_spacing=0.15,
    )

    for idx, (_, row) in enumerate(kpi_rows.iterrows(), start=1):
        actual = float(row["value"])
        benchmark = float(row["benchmark"])

        # Qualitative bands: 70%, 85%, 115% of benchmark
        bands = [benchmark * 0.70, benchmark * 0.85, benchmark * 1.15]
        max_val = max(actual, benchmark * 1.15) * 1.1

        # Background band bars (widest to narrowest)
        for band_val, band_color in zip([max_val, bands[2], bands[1]], _BAND_COLORS):
            fig.add_trace(
                go.Bar(
                    x=[band_val],
                    y=[row["metric"]],
                    orientation="h",
                    marker_color=band_color,
                    showlegend=False,
                    hoverinfo="skip",
                    width=0.6,
                ),
                row=idx,
                col=1,
            )

        # Actual value bar (thick)
        bar_color = ACCENT if row["status"] in ("Above", "At") else CORAL
        fig.add_trace(
            go.Bar(
                x=[actual],
                y=[row["metric"]],
                orientation="h",
                marker_color=bar_color,
                showlegend=False,
                width=0.25,
                text=[f"{actual:,.1f}"],
                textposition="outside",
                textfont_size=11,
            ),
            row=idx,
            col=1,
        )

        # Benchmark target line
        fig.add_trace(
            go.Scatter(
                x=[benchmark, benchmark],
                y=[row["metric"], row["metric"]],
                mode="markers",
                marker=dict(symbol="line-ns", size=18, color="#333333", line_width=2),
                showlegend=False,
                hovertemplate=f"Benchmark: {benchmark:,.1f}<extra></extra>",
            ),
            row=idx,
            col=1,
        )

    # Clean up axes
    for i in range(1, n_kpis + 1):
        fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, row=i, col=1)
        fig.update_yaxes(showticklabels=False, row=i, col=1)

    above_count = sum(1 for _, r in kpi_rows.iterrows() if r["status"] in ("Above", "At"))
    fig.update_layout(
        title=insight_title(
            f"{above_count} of {n_kpis} KPIs meet PULSE benchmark",
            "PULSE 2024 Debit Issuer Study",
        ),
        barmode="overlay",
        template=config.theme,
        width=config.width,
        height=180 + n_kpis * 100,
        margin=dict(l=40, r=80, t=80, b=40),
    )

    return fig
