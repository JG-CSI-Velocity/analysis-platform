"""Chart registry and rendering."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import plotly.graph_objects as go

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.business import (
    chart_business_top_by_accounts,
    chart_business_top_by_spend,
    chart_business_top_by_transactions,
)
from txn_analysis.charts.competitor import (
    chart_competitor_heatmap,
    chart_segmentation_bar,
    chart_threat_scatter,
)
from txn_analysis.charts.overall import (
    chart_top_by_accounts,
    chart_top_by_spend,
    chart_top_by_transactions,
)
from txn_analysis.charts.personal import (
    chart_personal_top_by_accounts,
    chart_personal_top_by_spend,
    chart_personal_top_by_transactions,
)
from txn_analysis.charts.scorecard import chart_scorecard_bullets
from txn_analysis.charts.trends import (
    chart_cohort_summary,
    chart_growth_leaders,
    chart_rank_trajectory,
)
from txn_analysis.settings import ChartConfig

logger = logging.getLogger(__name__)

ChartFunc = Callable[[AnalysisResult, ChartConfig], go.Figure]

# Maps analysis name -> chart function.
# Composite keys (e.g. "name:variant") support multiple charts per analysis.
# MCC comparison is special (needs 3 results) -- handled separately.
CHART_REGISTRY: dict[str, ChartFunc] = {
    # M1: Overall
    "top_merchants_by_spend": chart_top_by_spend,
    "top_merchants_by_transactions": chart_top_by_transactions,
    "top_merchants_by_accounts": chart_top_by_accounts,
    # M3: Business
    "business_top_by_spend": chart_business_top_by_spend,
    "business_top_by_transactions": chart_business_top_by_transactions,
    "business_top_by_accounts": chart_business_top_by_accounts,
    # M4: Personal
    "personal_top_by_spend": chart_personal_top_by_spend,
    "personal_top_by_transactions": chart_personal_top_by_transactions,
    "personal_top_by_accounts": chart_personal_top_by_accounts,
    # M5: Trends
    "monthly_rank_tracking": chart_rank_trajectory,
    "growth_leaders_decliners": chart_growth_leaders,
    "new_vs_declining_merchants": chart_cohort_summary,
    # M6: Competitor
    "competitor_threat_assessment": chart_threat_scatter,
    "competitor_segmentation": chart_segmentation_bar,
    "competitor_categories": chart_competitor_heatmap,
    # M9: Scorecard
    "portfolio_scorecard": chart_scorecard_bullets,
}


def create_charts(
    results: list[AnalysisResult],
    config: ChartConfig,
    client_name: str = "",
    date_range: str = "",
) -> dict[str, go.Figure]:
    """Generate all registered charts from analysis results.

    Returns mapping of chart name -> Plotly Figure.
    """
    from txn_analysis.charts.mcc import chart_mcc_comparison
    from txn_analysis.charts.theme import add_source_footer, ensure_theme

    ensure_theme()

    results_by_name = {r.name: r for r in results}
    charts: dict[str, go.Figure] = {}

    # Standard single-result charts (supports composite keys like "name:variant")
    for key, func in CHART_REGISTRY.items():
        analysis_name = key.split(":")[0]
        result = results_by_name.get(analysis_name)
        if result is None or result.error or result.df.empty:
            continue
        try:
            fig = func(result, config)
            if fig.data:
                add_source_footer(fig, client_name, date_range)
                charts[key] = fig
        except Exception as e:
            logger.warning("Chart '%s' failed: %s", key, e)

    # MCC comparison (needs 3 results)
    mcc_names = ("mcc_by_accounts", "mcc_by_transactions", "mcc_by_spend")
    mcc_results = [results_by_name.get(n) for n in mcc_names]
    if all(r and not r.error and not r.df.empty for r in mcc_results):
        try:
            fig = chart_mcc_comparison(mcc_results[0], mcc_results[1], mcc_results[2], config)
            if fig.data:
                add_source_footer(fig, client_name, date_range)
                charts["mcc_comparison"] = fig
        except Exception as e:
            logger.warning("Chart 'mcc_comparison' failed: %s", e)

    return charts


def render_chart_png(
    fig: go.Figure,
    output_path: Path,
    config: ChartConfig,
    scale: int | None = None,
) -> Path:
    """Write a Plotly figure to PNG using kaleido."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(
        str(output_path),
        width=config.width,
        height=config.height,
        scale=scale or config.scale,
        engine="kaleido",
    )
    return output_path
