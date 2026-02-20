"""Analysis registry and orchestration."""

import logging
from collections.abc import Callable

import pandas as pd

from ics_toolkit.analysis.analyses.activity import (
    analyze_activity_by_balance,
    analyze_activity_by_branch,
    analyze_activity_by_debit_source,
    analyze_activity_by_source_comparison,
    analyze_activity_summary,
    analyze_business_vs_personal,
    analyze_monthly_interchange,
    analyze_monthly_trends,
)
from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.cohort import (
    analyze_cohort_activation,
    analyze_cohort_heatmap,
)
from ics_toolkit.analysis.analyses.cohort_detail import (
    analyze_activation_personas,
    analyze_activation_summary,
    analyze_branch_activation,
    analyze_cohort_milestones,
    analyze_growth_patterns,
)
from ics_toolkit.analysis.analyses.demographics import (
    analyze_age_comparison,
    analyze_age_dist,
    analyze_age_vs_balance,
    analyze_balance_tier_detail,
    analyze_balance_tiers,
    analyze_balance_trajectory,
    analyze_closures,
    analyze_open_vs_close,
    analyze_stat_open_close,
)
from ics_toolkit.analysis.analyses.dm_source import (
    analyze_dm_activity,
    analyze_dm_activity_by_branch,
    analyze_dm_by_branch,
    analyze_dm_by_debit,
    analyze_dm_by_product,
    analyze_dm_by_year,
    analyze_dm_monthly_trends,
    analyze_dm_overview,
)
from ics_toolkit.analysis.analyses.executive_summary import analyze_executive_summary
from ics_toolkit.analysis.analyses.performance import (
    analyze_branch_performance_index,
    analyze_days_to_first_use,
    analyze_product_code_performance,
)
from ics_toolkit.analysis.analyses.persona import (
    analyze_persona_by_balance,
    analyze_persona_by_branch,
    analyze_persona_by_source,
    analyze_persona_cohort_trend,
    analyze_persona_contribution,
    analyze_persona_overview,
    analyze_persona_revenue,
    analyze_persona_velocity,
)
from ics_toolkit.analysis.analyses.portfolio import (
    analyze_closure_by_account_age,
    analyze_closure_by_branch,
    analyze_closure_by_source,
    analyze_closure_rate_trend,
    analyze_concentration,
    analyze_engagement_decay,
    analyze_net_growth_by_source,
    analyze_net_portfolio_growth,
)
from ics_toolkit.analysis.analyses.ref_source import (
    analyze_ref_activity,
    analyze_ref_activity_by_branch,
    analyze_ref_by_branch,
    analyze_ref_by_debit,
    analyze_ref_by_product,
    analyze_ref_by_year,
    analyze_ref_monthly_trends,
    analyze_ref_overview,
)
from ics_toolkit.analysis.analyses.source import (
    analyze_account_type,
    analyze_source_acquisition_mix,
    analyze_source_by_branch,
    analyze_source_by_prod,
    analyze_source_by_stat,
    analyze_source_by_year,
    analyze_source_dist,
)
from ics_toolkit.analysis.analyses.strategic import (
    analyze_activation_funnel,
    analyze_dormant_high_balance,
    analyze_revenue_by_branch,
    analyze_revenue_by_source,
    analyze_revenue_impact,
)
from ics_toolkit.analysis.analyses.summary import (
    analyze_debit_by_branch,
    analyze_debit_by_prod,
    analyze_debit_dist,
    analyze_open_ics,
    analyze_penetration_by_branch,
    analyze_prod_code,
    analyze_stat_code,
    analyze_total_ics,
)
from ics_toolkit.settings import AnalysisSettings as Settings

logger = logging.getLogger(__name__)

# Ordered list of (name, function) for all analyses.
# Each function has signature:
#   (df, ics_all, ics_stat_o, ics_stat_o_debit, settings) -> AnalysisResult
ANALYSIS_REGISTRY: list[tuple[str, Callable]] = [
    # Summary (ax01-ax07, ax64)
    ("Total ICS Accounts", analyze_total_ics),
    ("Open ICS Accounts", analyze_open_ics),
    ("ICS by Stat Code", analyze_stat_code),
    ("Product Code Distribution", analyze_prod_code),
    ("Debit Distribution", analyze_debit_dist),
    ("Debit x Prod Code", analyze_debit_by_prod),
    ("Debit x Branch", analyze_debit_by_branch),
    ("ICS Penetration by Branch", analyze_penetration_by_branch),
    # Source (ax08-ax13, ax85)
    ("Source Distribution", analyze_source_dist),
    ("Source x Stat Code", analyze_source_by_stat),
    ("Source x Prod Code", analyze_source_by_prod),
    ("Source x Branch", analyze_source_by_branch),
    ("Account Type", analyze_account_type),
    ("Source by Year", analyze_source_by_year),
    ("Source Acquisition Mix", analyze_source_acquisition_mix),
    # DM Source Deep-Dive (ax45-ax52)
    ("DM Overview", analyze_dm_overview),
    ("DM by Branch", analyze_dm_by_branch),
    ("DM by Debit Status", analyze_dm_by_debit),
    ("DM by Product", analyze_dm_by_product),
    ("DM by Year Opened", analyze_dm_by_year),
    ("DM Activity Summary", analyze_dm_activity),
    ("DM Activity by Branch", analyze_dm_activity_by_branch),
    ("DM Monthly Trends", analyze_dm_monthly_trends),
    # REF Source Deep-Dive (ax73-ax80)
    ("REF Overview", analyze_ref_overview),
    ("REF by Branch", analyze_ref_by_branch),
    ("REF by Debit Status", analyze_ref_by_debit),
    ("REF by Product", analyze_ref_by_product),
    ("REF by Year Opened", analyze_ref_by_year),
    ("REF Activity Summary", analyze_ref_activity),
    ("REF Activity by Branch", analyze_ref_activity_by_branch),
    ("REF Monthly Trends", analyze_ref_monthly_trends),
    # Demographics (ax14-ax21, ax83)
    ("Age Comparison", analyze_age_comparison),
    ("Closures", analyze_closures),
    ("Open vs Close", analyze_open_vs_close),
    ("Balance Tiers", analyze_balance_tiers),
    ("Stat Open Close", analyze_stat_open_close),
    ("Age vs Balance", analyze_age_vs_balance),
    ("Balance Tier Detail", analyze_balance_tier_detail),
    ("Age Distribution", analyze_age_dist),
    ("Balance Trajectory", analyze_balance_trajectory),
    # Activity (ax22-ax26, ax63, ax71-ax72)
    ("Activity Summary", analyze_activity_summary),
    ("Activity by Debit+Source", analyze_activity_by_debit_source),
    ("Activity by Balance", analyze_activity_by_balance),
    ("Activity by Branch", analyze_activity_by_branch),
    ("Monthly Trends", analyze_monthly_trends),
    ("Activity by Source Comparison", analyze_activity_by_source_comparison),
    ("Monthly Interchange Trend", analyze_monthly_interchange),
    ("Business vs Personal", analyze_business_vs_personal),
    # Cohort (ax27-ax36)
    ("Cohort Activation", analyze_cohort_activation),
    ("Cohort Heatmap", analyze_cohort_heatmap),
    ("Cohort Milestones", analyze_cohort_milestones),
    ("Activation Summary", analyze_activation_summary),
    ("Growth Patterns", analyze_growth_patterns),
    ("Activation Personas", analyze_activation_personas),
    ("Branch Activation", analyze_branch_activation),
    # Strategic (ax38-ax39, ax65-ax66, ax84)
    ("Activation Funnel", analyze_activation_funnel),
    ("Revenue Impact", analyze_revenue_impact),
    ("Revenue by Branch", analyze_revenue_by_branch),
    ("Revenue by Source", analyze_revenue_by_source),
    ("Dormant High-Balance", analyze_dormant_high_balance),
    # Portfolio (ax40-ax42, ax67-ax70, ax82)
    ("Engagement Decay", analyze_engagement_decay),
    ("Net Portfolio Growth", analyze_net_portfolio_growth),
    ("Spend Concentration", analyze_concentration),
    ("Closure by Source", analyze_closure_by_source),
    ("Closure by Branch", analyze_closure_by_branch),
    ("Closure by Account Age", analyze_closure_by_account_age),
    ("Net Growth by Source", analyze_net_growth_by_source),
    ("Closure Rate Trend", analyze_closure_rate_trend),
    # Performance (ax43-ax44, ax81)
    ("Days to First Use", analyze_days_to_first_use),
    ("Branch Performance Index", analyze_branch_performance_index),
    ("Product Code Performance", analyze_product_code_performance),
    # Persona Deep-Dive (ax55-ax62)
    ("Persona Overview", analyze_persona_overview),
    ("Persona Swipe Contribution", analyze_persona_contribution),
    ("Persona by Branch", analyze_persona_by_branch),
    ("Persona by Source", analyze_persona_by_source),
    ("Persona Revenue Impact", analyze_persona_revenue),
    ("Persona by Balance Tier", analyze_persona_by_balance),
    ("Persona Velocity", analyze_persona_velocity),
    ("Persona Cohort Trend", analyze_persona_cohort_trend),
]

# Executive summary is run separately after all other analyses.
EXECUTIVE_SUMMARY = ("Executive Summary", analyze_executive_summary)


def run_all_analyses(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
    on_progress: Callable | None = None,
) -> list[AnalysisResult]:
    """Run all registered analyses and return results."""
    results = []
    total = len(ANALYSIS_REGISTRY)

    for i, (name, func) in enumerate(ANALYSIS_REGISTRY):
        if on_progress:
            on_progress(i, total, name)

        try:
            result = func(df, ics_all, ics_stat_o, ics_stat_o_debit, settings)
            results.append(result)
            logger.info("  [%d/%d] %s", i + 1, total, name)
        except Exception as e:
            logger.warning("  [%d/%d] %s FAILED: %s", i + 1, total, name, e)
            results.append(
                AnalysisResult(
                    name=name,
                    title=name,
                    df=pd.DataFrame(),
                    error=str(e),
                )
            )

    # Run executive summary last with prior results
    name, func = EXECUTIVE_SUMMARY
    if on_progress:
        on_progress(total, total + 1, name)
    try:
        result = func(
            df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            settings,
            prior_results=results,
        )
        results.append(result)
        logger.info("  [%d/%d] %s", total + 1, total + 1, name)
    except Exception as e:
        logger.warning("  [%d/%d] %s FAILED: %s", total + 1, total + 1, name, e)
        results.append(
            AnalysisResult(
                name=name,
                title=name,
                df=pd.DataFrame(),
                error=str(e),
            )
        )

    return results
