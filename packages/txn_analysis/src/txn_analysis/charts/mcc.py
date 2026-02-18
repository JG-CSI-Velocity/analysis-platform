"""M2: MCC triple-subplot chart (consultant style)."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.bar_charts import _fmt
from txn_analysis.charts.theme import ACCENT, ACCENT_SECONDARY, TEAL, insight_title
from txn_analysis.settings import ChartConfig


def chart_mcc_comparison(
    mcc_accounts: AnalysisResult,
    mcc_transactions: AnalysisResult,
    mcc_spend: AnalysisResult,
    config: ChartConfig,
) -> go.Figure:
    """Triple horizontal bar: MCC by accounts, transactions, and spend."""
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("By Accounts", "By Transactions", "By Spend"),
        shared_yaxes=True,
        horizontal_spacing=0.08,
    )

    datasets = [
        (mcc_accounts, "unique_accounts", ACCENT_SECONDARY, ",.0f"),
        (mcc_transactions, "transaction_count", TEAL, ",.0f"),
        (mcc_spend, "total_amount", ACCENT, "$,.0f"),
    ]

    top_n = 15
    for col_idx, (result, value_col, color, fmt) in enumerate(datasets, start=1):
        df = result.df
        if df.empty:
            continue
        data = df[df["mcc_description"].astype(str) != "Grand Total"].head(top_n)
        labels = list(reversed(data["mcc_description"].tolist()))
        values = list(reversed(data[value_col].tolist()))

        fig.add_trace(
            go.Bar(
                x=values,
                y=labels,
                orientation="h",
                marker_color=color,
                text=[_fmt(v, fmt) for v in values],
                textposition="outside",
                textfont_size=9,
                showlegend=False,
            ),
            row=1,
            col=col_idx,
        )

    fig.update_layout(
        title=insight_title("MCC Code Comparison"),
        template=config.theme,
        width=config.width + 400,
        height=max(config.height, top_n * 28),
        margin=dict(l=220, r=60, t=80, b=40),
    )

    return fig
