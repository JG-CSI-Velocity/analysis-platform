"""M4: Personal segment top merchant charts."""

from __future__ import annotations

import plotly.graph_objects as go

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.bar_charts import lollipop_chart
from txn_analysis.settings import ChartConfig


def chart_personal_top_by_spend(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Personal merchants by total spend."""
    df = result.df
    if df.empty:
        return go.Figure()
    data = df[df["merchant_consolidated"] != "Grand Total"].head(25)
    return lollipop_chart(
        labels=data["merchant_consolidated"].tolist(),
        values=data["total_amount"].tolist(),
        title="Top 25 Personal Merchants by Spend",
        config=config,
        value_format="$,.0f",
        subtitle="Personal accounts only",
    )


def chart_personal_top_by_transactions(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Personal merchants by transaction count."""
    df = result.df
    if df.empty:
        return go.Figure()
    data = df[df["merchant_consolidated"] != "Grand Total"].head(25)
    return lollipop_chart(
        labels=data["merchant_consolidated"].tolist(),
        values=data["transaction_count"].tolist(),
        title="Top 25 Personal Merchants by Transactions",
        config=config,
        value_format=",.0f",
        subtitle="Personal accounts only",
    )


def chart_personal_top_by_accounts(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Personal merchants by unique accounts."""
    df = result.df
    if df.empty:
        return go.Figure()
    data = df[df["merchant_consolidated"] != "Grand Total"].head(25)
    return lollipop_chart(
        labels=data["merchant_consolidated"].tolist(),
        values=data["unique_accounts"].tolist(),
        title="Top 25 Personal Merchants by Account Reach",
        config=config,
        value_format=",.0f",
        subtitle="Personal accounts only",
    )
