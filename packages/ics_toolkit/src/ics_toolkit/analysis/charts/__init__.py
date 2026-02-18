"""Chart creation registry and dispatcher."""

import logging
from typing import Callable

import plotly.graph_objects as go

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.charts.activity import (
    chart_activity_by_balance,
    chart_activity_by_branch,
    chart_activity_by_source,
    chart_monthly_trends,
)
from ics_toolkit.analysis.charts.cohort import (
    chart_activation_personas,
    chart_activation_summary,
    chart_branch_activation,
    chart_cohort_activation,
    chart_cohort_heatmap,
    chart_cohort_milestones,
    chart_growth_patterns,
)
from ics_toolkit.analysis.charts.demographics import (
    chart_age_comparison,
    chart_age_dist,
    chart_age_vs_balance,
    chart_balance_tier_detail,
    chart_balance_tiers,
    chart_closures,
    chart_open_vs_close,
    chart_stat_open_close,
)
from ics_toolkit.analysis.charts.performance import (
    chart_branch_performance_index,
    chart_days_to_first_use,
)
from ics_toolkit.analysis.charts.portfolio import (
    chart_concentration,
    chart_engagement_decay,
    chart_net_portfolio_growth,
)
from ics_toolkit.analysis.charts.source import (
    chart_account_type,
    chart_source_by_branch,
    chart_source_by_prod,
    chart_source_by_stat,
    chart_source_by_year,
    chart_source_dist,
)
from ics_toolkit.analysis.charts.strategic import (
    chart_activation_funnel,
    chart_revenue_impact,
)
from ics_toolkit.analysis.charts.summary import (
    chart_debit_by_branch,
    chart_debit_by_prod,
    chart_debit_dist,
    chart_prod_code,
    chart_stat_code,
    chart_total_ics,
)
from ics_toolkit.settings import AnalysisSettings as Settings
from ics_toolkit.settings import ChartConfig

logger = logging.getLogger(__name__)

# Maps analysis name -> chart builder function.
# Signature: (df: pd.DataFrame, config: ChartConfig) -> go.Figure
CHART_REGISTRY: dict[str, Callable] = {
    # Summary
    "Total ICS Accounts": chart_total_ics,
    "ICS by Stat Code": chart_stat_code,
    "Product Code Distribution": chart_prod_code,
    "Debit Distribution": chart_debit_dist,
    "Debit x Prod Code": chart_debit_by_prod,
    "Debit x Branch": chart_debit_by_branch,
    # Source
    "Source Distribution": chart_source_dist,
    "Source x Stat Code": chart_source_by_stat,
    "Source x Prod Code": chart_source_by_prod,
    "Source x Branch": chart_source_by_branch,
    "Account Type": chart_account_type,
    "Source by Year": chart_source_by_year,
    # Demographics
    "Age Comparison": chart_age_comparison,
    "Closures": chart_closures,
    "Open vs Close": chart_open_vs_close,
    "Balance Tiers": chart_balance_tiers,
    "Stat Open Close": chart_stat_open_close,
    "Age vs Balance": chart_age_vs_balance,
    "Balance Tier Detail": chart_balance_tier_detail,
    "Age Distribution": chart_age_dist,
    # Activity
    "Activity by Debit+Source": chart_activity_by_source,
    "Activity by Balance": chart_activity_by_balance,
    "Activity by Branch": chart_activity_by_branch,
    "Monthly Trends": chart_monthly_trends,
    # Cohort
    "Cohort Activation": chart_cohort_activation,
    "Cohort Heatmap": chart_cohort_heatmap,
    "Cohort Milestones": chart_cohort_milestones,
    "Activation Summary": chart_activation_summary,
    "Growth Patterns": chart_growth_patterns,
    "Activation Personas": chart_activation_personas,
    "Branch Activation": chart_branch_activation,
    # Strategic
    "Activation Funnel": chart_activation_funnel,
    "Revenue Impact": chart_revenue_impact,
    # Portfolio
    "Engagement Decay": chart_engagement_decay,
    "Net Portfolio Growth": chart_net_portfolio_growth,
    "Spend Concentration": chart_concentration,
    # Performance
    "Days to First Use": chart_days_to_first_use,
    "Branch Performance Index": chart_branch_performance_index,
}


def create_charts(
    analyses: list[AnalysisResult],
    settings: Settings,
) -> dict[str, go.Figure]:
    """Build Plotly figures for all successful analyses."""
    charts = {}
    config = settings.charts

    for analysis in analyses:
        if analysis.error is not None or analysis.df.empty:
            continue

        builder = CHART_REGISTRY.get(analysis.name)
        if builder is None:
            logger.debug("No chart builder for '%s'", analysis.name)
            continue

        try:
            fig = builder(analysis.df, config)
            fig.update_layout(title_text=analysis.title)
            charts[analysis.name] = fig
        except Exception as e:
            logger.warning("Chart for '%s' failed: %s", analysis.name, e)

    return charts


def render_chart_png(fig: go.Figure, config: ChartConfig) -> bytes:
    """Render a Plotly figure to PNG bytes.

    Requires kaleido: ``pip install kaleido``
    """
    return fig.to_image(
        format="png",
        width=config.width,
        height=config.height,
        scale=config.scale,
    )


def render_all_chart_pngs(
    charts: dict[str, go.Figure],
    config: ChartConfig,
) -> dict[str, bytes]:
    """Render all charts to PNG bytes once, with progress logging.

    Returns an empty dict if kaleido is not installed.
    """
    if not charts:
        return {}

    try:
        import kaleido  # noqa: F401
    except ImportError:
        logger.warning("kaleido not installed; skipping chart PNG rendering")
        return {}

    pngs: dict[str, bytes] = {}
    total = len(charts)
    for i, (name, fig) in enumerate(charts.items(), start=1):
        try:
            logger.info("  Rendering chart [%d/%d] %s", i, total, name)
            pngs[name] = render_chart_png(fig, config)
        except Exception as e:
            logger.warning("  Chart PNG for '%s' failed: %s", name, e)
    return pngs
