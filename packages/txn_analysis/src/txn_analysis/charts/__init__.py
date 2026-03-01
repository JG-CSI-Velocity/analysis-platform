"""Chart registry and rendering (matplotlib)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.builders import (  # noqa: F401 -- re-export
    bullet_chart,
    donut_chart,
    grouped_bar,
    heatmap,
    horizontal_bar,
    line_trend,
    lollipop_chart,
    scatter_plot,
    stacked_bar,
    waterfall_chart,
)
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
from txn_analysis.charts.recurring import (
    chart_recurring_merchants,
    chart_recurring_onsets,
)
from txn_analysis.charts.scorecard import chart_scorecard_bullets
from txn_analysis.charts.segment_comparison import chart_segment_comparison_bars
from txn_analysis.charts.spending_profile import (
    chart_spending_profile_table,
    chart_spending_tier_bars,
)
from txn_analysis.charts.spending_trends import chart_spending_trends
from txn_analysis.charts.trends import (
    chart_cohort_summary,
    chart_growth_leaders,
    chart_rank_trajectory,
)
from txn_analysis.charts.txn_distribution import chart_txn_violin
from txn_analysis.charts.wallet_radar import chart_wallet_radar
from txn_analysis.settings import ChartConfig

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

ChartFunc = Callable[[AnalysisResult, ChartConfig], Figure]

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
    # M15: Recurring Payments
    "recurring_payments": chart_recurring_merchants,
    "recurring_payments:onsets": chart_recurring_onsets,
    # M18: Wallet Radar
    "wallet_radar": chart_wallet_radar,
    # M19: Spending Trends
    "spending_trends": chart_spending_trends,
    # M20: Spending Profile
    "spending_profile": chart_spending_profile_table,
    "spending_profile:tiers": chart_spending_tier_bars,
    # M21: Distribution
    "txn_distribution": chart_txn_violin,
    # M22: Segment Comparison
    "segment_comparison": chart_segment_comparison_bars,
    # M9: Scorecard
    "portfolio_scorecard": chart_scorecard_bullets,
}


def create_charts(
    results: list[AnalysisResult],
    config: ChartConfig,
    client_name: str = "",
    date_range: str = "",
) -> dict[str, Figure]:
    """Generate all registered charts from analysis results.

    Returns mapping of chart name -> matplotlib Figure.
    """
    from txn_analysis.charts.mcc import chart_mcc_comparison
    from txn_analysis.charts.theme import add_source_footer

    results_by_name = {r.name: r for r in results}
    charts: dict[str, Figure] = {}

    # Standard single-result charts (supports composite keys like "name:variant")
    for key, func in CHART_REGISTRY.items():
        analysis_name = key.split(":")[0]
        result = results_by_name.get(analysis_name)
        if result is None or result.error or result.df.empty:
            continue
        try:
            fig = func(result, config)
            if fig.get_axes():
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
            if fig.get_axes():
                add_source_footer(fig, client_name, date_range)
                charts["mcc_comparison"] = fig
        except Exception as e:
            logger.warning("Chart 'mcc_comparison' failed: %s", e)

    return charts


def render_chart_png(
    fig: Figure,
    output_path: Path,
    config: ChartConfig,
    scale: int | None = None,
) -> Path:
    """Write a matplotlib figure to PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_dpi = (
        (scale or config.scale) * config.dpi
        if hasattr(config, "dpi")
        else 150 * (scale or config.scale)
    )
    dpi = min(raw_dpi, 300)
    fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def render_chart_png_bytes(fig: Figure, dpi: int = 150) -> bytes:
    """Render a matplotlib figure to PNG bytes for embedding."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()
