"""M1: Overall top merchant charts."""

from __future__ import annotations

import plotly.graph_objects as go

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.bar_charts import lollipop_chart
from txn_analysis.settings import ChartConfig


def _insight_spend(df, top_k: int = 5) -> str:
    """Compute insight like 'Top 5 merchants capture 62% of total spend'."""
    data = df[df["merchant_consolidated"] != "Grand Total"]
    if data.empty or "pct_of_total_amount" not in data.columns:
        return "Top Merchants by Spend"
    top_pct = data.head(top_k)["pct_of_total_amount"].sum()
    return f"Top {top_k} merchants capture {top_pct:.0f}% of total spend"


def chart_top_by_spend(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Top merchants by total spend."""
    df = result.df
    if df.empty:
        return go.Figure()
    data = df[df["merchant_consolidated"] != "Grand Total"].head(25)
    return lollipop_chart(
        labels=data["merchant_consolidated"].tolist(),
        values=data["total_amount"].tolist(),
        title=_insight_spend(df),
        config=config,
        value_format="$,.0f",
    )


def chart_top_by_transactions(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Top merchants by transaction count."""
    df = result.df
    if df.empty:
        return go.Figure()
    data = df[df["merchant_consolidated"] != "Grand Total"].head(25)
    return lollipop_chart(
        labels=data["merchant_consolidated"].tolist(),
        values=data["transaction_count"].tolist(),
        title="Top 25 Merchants by Transaction Volume",
        config=config,
        value_format=",.0f",
    )


def chart_top_by_accounts(result: AnalysisResult, config: ChartConfig) -> go.Figure:
    """Top merchants by unique accounts."""
    df = result.df
    if df.empty:
        return go.Figure()
    data = df[df["merchant_consolidated"] != "Grand Total"].head(25)
    return lollipop_chart(
        labels=data["merchant_consolidated"].tolist(),
        values=data["unique_accounts"].tolist(),
        title="Top 25 Merchants by Account Reach",
        config=config,
        value_format=",.0f",
    )
