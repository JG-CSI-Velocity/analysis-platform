"""Analysis registry and orchestration."""

import logging
from typing import Callable

import pandas as pd

from ics_toolkit.analysis.analyses.activity import (
    analyze_activity_by_balance,
    analyze_activity_by_branch,
    analyze_activity_by_debit_source,
    analyze_activity_summary,
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
    analyze_closures,
    analyze_open_vs_close,
    analyze_stat_open_close,
)
from ics_toolkit.analysis.analyses.executive_summary import analyze_executive_summary
from ics_toolkit.analysis.analyses.performance import (
    analyze_branch_performance_index,
    analyze_days_to_first_use,
)
from ics_toolkit.analysis.analyses.portfolio import (
    analyze_concentration,
    analyze_engagement_decay,
    analyze_net_portfolio_growth,
)
from ics_toolkit.analysis.analyses.source import (
    analyze_account_type,
    analyze_source_by_branch,
    analyze_source_by_prod,
    analyze_source_by_stat,
    analyze_source_by_year,
    analyze_source_dist,
)
from ics_toolkit.analysis.analyses.strategic import (
    analyze_activation_funnel,
    analyze_revenue_impact,
)
from ics_toolkit.analysis.analyses.summary import (
    analyze_debit_by_branch,
    analyze_debit_by_prod,
    analyze_debit_dist,
    analyze_open_ics,
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
    # Summary (ax01-ax07)
    ("Total ICS Accounts", analyze_total_ics),
    ("Open ICS Accounts", analyze_open_ics),
    ("ICS by Stat Code", analyze_stat_code),
    ("Product Code Distribution", analyze_prod_code),
    ("Debit Distribution", analyze_debit_dist),
    ("Debit x Prod Code", analyze_debit_by_prod),
    ("Debit x Branch", analyze_debit_by_branch),
    # Source (ax08-ax13)
    ("Source Distribution", analyze_source_dist),
    ("Source x Stat Code", analyze_source_by_stat),
    ("Source x Prod Code", analyze_source_by_prod),
    ("Source x Branch", analyze_source_by_branch),
    ("Account Type", analyze_account_type),
    ("Source by Year", analyze_source_by_year),
    # Demographics (ax14-ax21)
    ("Age Comparison", analyze_age_comparison),
    ("Closures", analyze_closures),
    ("Open vs Close", analyze_open_vs_close),
    ("Balance Tiers", analyze_balance_tiers),
    ("Stat Open Close", analyze_stat_open_close),
    ("Age vs Balance", analyze_age_vs_balance),
    ("Balance Tier Detail", analyze_balance_tier_detail),
    ("Age Distribution", analyze_age_dist),
    # Activity (ax22-ax26)
    ("Activity Summary", analyze_activity_summary),
    ("Activity by Debit+Source", analyze_activity_by_debit_source),
    ("Activity by Balance", analyze_activity_by_balance),
    ("Activity by Branch", analyze_activity_by_branch),
    ("Monthly Trends", analyze_monthly_trends),
    # Cohort (ax27-ax36)
    ("Cohort Activation", analyze_cohort_activation),
    ("Cohort Heatmap", analyze_cohort_heatmap),
    ("Cohort Milestones", analyze_cohort_milestones),
    ("Activation Summary", analyze_activation_summary),
    ("Growth Patterns", analyze_growth_patterns),
    ("Activation Personas", analyze_activation_personas),
    ("Branch Activation", analyze_branch_activation),
    # Strategic (ax38-ax39)
    ("Activation Funnel", analyze_activation_funnel),
    ("Revenue Impact", analyze_revenue_impact),
    # Portfolio (ax40-ax42)
    ("Engagement Decay", analyze_engagement_decay),
    ("Net Portfolio Growth", analyze_net_portfolio_growth),
    ("Spend Concentration", analyze_concentration),
    # Performance (ax43-ax44)
    ("Days to First Use", analyze_days_to_first_use),
    ("Branch Performance Index", analyze_branch_performance_index),
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
