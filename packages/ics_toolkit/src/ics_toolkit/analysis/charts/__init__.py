"""Chart creation registry and dispatcher."""

import logging
from collections.abc import Callable
from pathlib import Path

import plotly.graph_objects as go

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.charts.activity import (
    chart_activity_by_balance,
    chart_activity_by_branch,
    chart_activity_by_source,
    chart_activity_source_comparison,
    chart_business_vs_personal,
    chart_monthly_interchange,
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
    chart_balance_trajectory,
    chart_closures,
    chart_open_vs_close,
    chart_stat_open_close,
)
from ics_toolkit.analysis.charts.dm_source import (
    chart_dm_activity_by_branch,
    chart_dm_by_branch,
    chart_dm_by_year,
    chart_dm_monthly_trends,
)
from ics_toolkit.analysis.charts.performance import (
    chart_branch_performance_index,
    chart_days_to_first_use,
    chart_product_code_performance,
)
from ics_toolkit.analysis.charts.persona import (
    chart_persona_by_branch,
    chart_persona_by_source,
    chart_persona_cohort_trend,
    chart_persona_contribution,
    chart_persona_map,
    chart_persona_revenue,
)
from ics_toolkit.analysis.charts.portfolio import (
    chart_closure_by_account_age,
    chart_closure_by_branch,
    chart_closure_by_source,
    chart_closure_rate_trend,
    chart_concentration,
    chart_engagement_decay,
    chart_net_growth_by_source,
    chart_net_portfolio_growth,
)
from ics_toolkit.analysis.charts.renderer import render_all_chart_pngs as render_all_chart_pngs
from ics_toolkit.analysis.charts.source import (
    chart_account_type,
    chart_source_acquisition_mix,
    chart_source_by_branch,
    chart_source_by_prod,
    chart_source_by_stat,
    chart_source_by_year,
    chart_source_dist,
)
from ics_toolkit.analysis.charts.strategic import (
    chart_activation_funnel,
    chart_revenue_by_branch,
    chart_revenue_by_source,
    chart_revenue_impact,
)
from ics_toolkit.analysis.charts.summary import (
    chart_debit_by_branch,
    chart_debit_by_prod,
    chart_debit_dist,
    chart_penetration_by_branch,
    chart_prod_code,
    chart_stat_code,
    chart_total_ics,
)
from ics_toolkit.settings import AnalysisSettings as Settings

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
    "ICS Penetration by Branch": chart_penetration_by_branch,
    # Source
    "Source Distribution": chart_source_dist,
    "Source x Stat Code": chart_source_by_stat,
    "Source x Prod Code": chart_source_by_prod,
    "Source x Branch": chart_source_by_branch,
    "Account Type": chart_account_type,
    "Source by Year": chart_source_by_year,
    "Source Acquisition Mix": chart_source_acquisition_mix,
    # DM Source Deep-Dive
    "DM by Branch": chart_dm_by_branch,
    "DM by Year Opened": chart_dm_by_year,
    "DM Activity by Branch": chart_dm_activity_by_branch,
    "DM Monthly Trends": chart_dm_monthly_trends,
    # REF Source Deep-Dive (reuse DM chart functions -- same column structure)
    "REF by Branch": chart_dm_by_branch,
    "REF by Year Opened": chart_dm_by_year,
    "REF Activity by Branch": chart_dm_activity_by_branch,
    "REF Monthly Trends": chart_dm_monthly_trends,
    # Demographics
    "Age Comparison": chart_age_comparison,
    "Closures": chart_closures,
    "Open vs Close": chart_open_vs_close,
    "Balance Tiers": chart_balance_tiers,
    "Stat Open Close": chart_stat_open_close,
    "Age vs Balance": chart_age_vs_balance,
    "Balance Tier Detail": chart_balance_tier_detail,
    "Age Distribution": chart_age_dist,
    "Balance Trajectory": chart_balance_trajectory,
    # Activity
    "Activity by Debit+Source": chart_activity_by_source,
    "Activity by Balance": chart_activity_by_balance,
    "Activity by Branch": chart_activity_by_branch,
    "Monthly Trends": chart_monthly_trends,
    "Activity by Source Comparison": chart_activity_source_comparison,
    "Monthly Interchange Trend": chart_monthly_interchange,
    "Business vs Personal": chart_business_vs_personal,
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
    "Revenue by Branch": chart_revenue_by_branch,
    "Revenue by Source": chart_revenue_by_source,
    # Portfolio
    "Engagement Decay": chart_engagement_decay,
    "Net Portfolio Growth": chart_net_portfolio_growth,
    "Spend Concentration": chart_concentration,
    "Closure by Source": chart_closure_by_source,
    "Closure by Branch": chart_closure_by_branch,
    "Closure by Account Age": chart_closure_by_account_age,
    "Net Growth by Source": chart_net_growth_by_source,
    "Closure Rate Trend": chart_closure_rate_trend,
    # Performance
    "Days to First Use": chart_days_to_first_use,
    "Branch Performance Index": chart_branch_performance_index,
    "Product Code Performance": chart_product_code_performance,
    # Persona Deep-Dive
    "Persona Overview": chart_persona_map,
    "Persona Swipe Contribution": chart_persona_contribution,
    "Persona by Branch": chart_persona_by_branch,
    "Persona by Source": chart_persona_by_source,
    "Persona Revenue Impact": chart_persona_revenue,
    "Persona Cohort Trend": chart_persona_cohort_trend,
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
            # Hide legend for single-trace charts (Pie handles its own labels)
            if len(fig.data) == 1 and not isinstance(fig.data[0], go.Pie):
                fig.update_layout(showlegend=False)
            charts[analysis.name] = fig
        except Exception as e:
            logger.warning("Chart for '%s' failed: %s", analysis.name, e)

    return charts


def save_charts_html(
    charts: dict[str, go.Figure],
    output_dir: Path,
) -> list[Path]:
    """Save all charts as standalone interactive HTML files.

    Returns list of generated file paths.
    """
    if not charts:
        return []

    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    total = len(charts)

    for i, (name, fig) in enumerate(charts.items(), start=1):
        try:
            safe_name = name.replace(" ", "_").replace("/", "_").replace("+", "")
            path = charts_dir / f"{safe_name}.html"
            fig.write_html(str(path), include_plotlyjs="cdn")
            paths.append(path)
            logger.info("  Chart [%d/%d] %s", i, total, name)
        except Exception as e:
            logger.warning("  Chart HTML for '%s' failed: %s", name, e)

    return paths
