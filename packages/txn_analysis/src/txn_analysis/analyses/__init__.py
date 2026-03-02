"""Analysis registry and runner."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pandas as pd

from txn_analysis.analyses.activation import analyze_activation
from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.business import (
    analyze_business_top_by_accounts,
    analyze_business_top_by_spend,
    analyze_business_top_by_transactions,
)
from txn_analysis.analyses.competitor_detect import analyze_competitor_detection
from txn_analysis.analyses.competitor_metrics import (
    analyze_competitor_biz_personal,
    analyze_competitor_categories,
    analyze_competitor_high_level,
    analyze_competitor_monthly_trends,
    analyze_top_20_competitors,
)
from txn_analysis.analyses.competitor_segment import analyze_competitor_segmentation
from txn_analysis.analyses.competitor_threat import analyze_threat_assessment
from txn_analysis.analyses.discover_unmatched_financial import analyze_unmatched_financial
from txn_analysis.analyses.financial_services import (
    analyze_financial_services_detection,
    analyze_financial_services_summary,
)
from txn_analysis.analyses.interchange import analyze_interchange_summary
from txn_analysis.analyses.mailer_effectiveness import analyze_mailer_effectiveness
from txn_analysis.analyses.mcc import (
    analyze_mcc_by_accounts,
    analyze_mcc_by_spend,
    analyze_mcc_by_transactions,
)
from txn_analysis.analyses.member_segments import analyze_member_segments
from txn_analysis.analyses.overall import (
    analyze_top_by_accounts,
    analyze_top_by_spend,
    analyze_top_by_transactions,
)
from txn_analysis.analyses.personal import (
    analyze_personal_top_by_accounts,
    analyze_personal_top_by_spend,
    analyze_personal_top_by_transactions,
)
from txn_analysis.analyses.recurring import analyze_recurring_payments
from txn_analysis.analyses.rfm import analyze_rfm
from txn_analysis.analyses.scorecard import analyze_portfolio_scorecard
from txn_analysis.analyses.segment_comparison import analyze_segment_comparison
from txn_analysis.analyses.spending_behavior import analyze_spending_behavior
from txn_analysis.analyses.spending_profile import analyze_spending_profile
from txn_analysis.analyses.spending_trends import analyze_spending_trends
from txn_analysis.analyses.storyline_adapters import (
    analyze_campaigns,
    analyze_demographics,
    analyze_lifecycle,
    analyze_payroll,
)
from txn_analysis.analyses.time_patterns import analyze_time_patterns
from txn_analysis.analyses.trends_cohort import analyze_new_vs_declining
from txn_analysis.analyses.trends_consistency import analyze_spending_consistency
from txn_analysis.analyses.trends_growth import analyze_growth_leaders_decliners
from txn_analysis.analyses.trends_movers import analyze_business_movers, analyze_personal_movers
from txn_analysis.analyses.trends_rank import analyze_monthly_rank_tracking
from txn_analysis.analyses.txn_distribution import analyze_txn_distribution
from txn_analysis.analyses.wallet_radar import analyze_wallet_radar
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)

AnalysisFunc = Callable[
    [pd.DataFrame, pd.DataFrame, pd.DataFrame, Settings, dict | None],
    AnalysisResult,
]

# Deterministic ordering -- dependency constraints:
#   M6A (competitor_detection) MUST precede M6B-* (populates context)
#   M7A (financial_services_detection) MUST precede M7B (reads completed_results)
#   M8 (interchange) MUST precede M9 (scorecard reads interchange_summary)
#   M10 (member_segments) MUST precede M9 (scorecard reads member_segments)
ANALYSIS_REGISTRY: list[tuple[str, AnalysisFunc]] = [
    # M1: Overall
    ("top_merchants_by_spend", analyze_top_by_spend),
    ("top_merchants_by_transactions", analyze_top_by_transactions),
    ("top_merchants_by_accounts", analyze_top_by_accounts),
    # M2: MCC
    ("mcc_by_accounts", analyze_mcc_by_accounts),
    ("mcc_by_transactions", analyze_mcc_by_transactions),
    ("mcc_by_spend", analyze_mcc_by_spend),
    # M3: Business
    ("business_top_by_spend", analyze_business_top_by_spend),
    ("business_top_by_transactions", analyze_business_top_by_transactions),
    ("business_top_by_accounts", analyze_business_top_by_accounts),
    # M4: Personal
    ("personal_top_by_spend", analyze_personal_top_by_spend),
    ("personal_top_by_transactions", analyze_personal_top_by_transactions),
    ("personal_top_by_accounts", analyze_personal_top_by_accounts),
    # M5: Trends
    ("monthly_rank_tracking", analyze_monthly_rank_tracking),
    ("growth_leaders_decliners", analyze_growth_leaders_decliners),
    ("spending_consistency", analyze_spending_consistency),
    ("new_vs_declining_merchants", analyze_new_vs_declining),
    ("business_monthly_movers", analyze_business_movers),
    ("personal_monthly_movers", analyze_personal_movers),
    # M6: Competitor (detection MUST be first -- populates context)
    ("competitor_detection", analyze_competitor_detection),
    ("competitor_high_level", analyze_competitor_high_level),
    ("top_20_competitors", analyze_top_20_competitors),
    ("competitor_categories", analyze_competitor_categories),
    ("competitor_biz_personal", analyze_competitor_biz_personal),
    ("competitor_monthly_trends", analyze_competitor_monthly_trends),
    ("competitor_threat_assessment", analyze_threat_assessment),
    ("competitor_segmentation", analyze_competitor_segmentation),
    ("unmatched_financial", analyze_unmatched_financial),  # M6B-7
    # M7: Financial Services (detection before summary)
    ("financial_services_detection", analyze_financial_services_detection),
    ("financial_services_summary", analyze_financial_services_summary),
    # M8: Interchange Revenue (before M9 scorecard)
    ("interchange_summary", analyze_interchange_summary),
    # M10: Member Segmentation (before M9 scorecard)
    ("member_segments", analyze_member_segments),
    # M11: Demographics & Branch (requires ODD)
    ("demographics", analyze_demographics),
    # M12: Campaign Effectiveness (requires ODD campaign columns)
    ("campaigns", analyze_campaigns),
    # M13: Payroll & Circular Economy
    ("payroll", analyze_payroll),
    # M14: Lifecycle Management (requires ODD)
    ("lifecycle", analyze_lifecycle),
    # M15: Recurring Payments (pure TXN, no ODD needed)
    ("recurring_payments", analyze_recurring_payments),
    # M16: Time-of-Day / Day-of-Week / Day-of-Month Patterns (pure TXN, no ODD needed)
    ("time_patterns", analyze_time_patterns),
    # M17: Spending Behavior by Demographics + Response Timing (requires ODD)
    ("spending_behavior", analyze_spending_behavior),
    # M18: Share of Wallet Radar (requires ODD for segment split)
    ("wallet_radar", analyze_wallet_radar),
    # M19: Spending Trends by Segment (requires ODD)
    ("spending_trends", analyze_spending_trends),
    # M20: Spending Segment Profile (tier classification)
    ("spending_profile", analyze_spending_profile),
    # M21: Transaction Amount Distribution (violin plot data)
    ("txn_distribution", analyze_txn_distribution),
    # M22: Segment Behavioral Comparison (requires ODD)
    ("segment_comparison", analyze_segment_comparison),
    # M23: Mailer Effectiveness (DiD, ITS, decay -- requires ODD for responder flags)
    ("mailer_effectiveness", analyze_mailer_effectiveness),
    # M24: Activation & Dormancy (dormancy is pure TXN; activation requires ODD)
    ("activation", analyze_activation),
    # M25: RFM Segmentation (pure TXN; migration uses ODD if available)
    ("rfm", analyze_rfm),
    # M9: Scorecard (MUST be last -- reads completed_results from all prior analyses)
    ("portfolio_scorecard", analyze_portfolio_scorecard),
]


def run_all_analyses(
    df: pd.DataFrame,
    settings: Settings,
    on_progress: Callable[[str], None] | None = None,
    odd_df: pd.DataFrame | None = None,
) -> list[AnalysisResult]:
    """Execute every registered analysis and return results.

    Failed analyses produce an AnalysisResult with error set (no crash).
    Populates context['completed_results'] so downstream analyses (M7B, M9)
    can read prior results without re-running expensive computations.

    The optional *odd_df* (account-level demographics) is stored in
    ``context["odd_df"]`` for analyses that require ODD enrichment.
    """
    business_df = df[df["business_flag"] == "Yes"]
    personal_df = df[df["business_flag"] == "No"]
    context: dict = {"completed_results": {}}
    if odd_df is not None:
        context["odd_df"] = odd_df
    results: list[AnalysisResult] = []

    for name, func in ANALYSIS_REGISTRY:
        if on_progress:
            on_progress(name)
        try:
            result = func(df, business_df, personal_df, settings, context)
            results.append(result)
            context["completed_results"][name] = result
        except Exception as e:
            logger.warning("Analysis '%s' failed: %s", name, e)
            results.append(AnalysisResult.from_df(name, name, pd.DataFrame(), error=str(e)))

    return results
