"""Referral analysis artifacts registry and orchestration."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses.base import ReferralContext
from ics_toolkit.referral.analyses.branch_density import analyze_branch_density
from ics_toolkit.referral.analyses.code_health import analyze_code_health
from ics_toolkit.referral.analyses.dormant_referrers import analyze_dormant_referrers
from ics_toolkit.referral.analyses.emerging_referrers import analyze_emerging_referrers
from ics_toolkit.referral.analyses.onetime_vs_repeat import analyze_onetime_vs_repeat
from ics_toolkit.referral.analyses.overview import analyze_overview
from ics_toolkit.referral.analyses.staff_multipliers import analyze_staff_multipliers
from ics_toolkit.referral.analyses.top_referrers import analyze_top_referrers

logger = logging.getLogger(__name__)

# Ordered list of (name, function) for all referral analyses.
# Each function has signature: (ctx: ReferralContext) -> AnalysisResult
REFERRAL_ANALYSIS_REGISTRY: list[tuple[str, Callable]] = [
    ("Top Referrers", analyze_top_referrers),
    ("Emerging Referrers", analyze_emerging_referrers),
    ("Dormant High-Value Referrers", analyze_dormant_referrers),
    ("One-time vs Repeat Referrers", analyze_onetime_vs_repeat),
    ("Staff Multipliers", analyze_staff_multipliers),
    ("Branch Influence Density", analyze_branch_density),
    ("Code Health Report", analyze_code_health),
]

# Overview is run separately after all other analyses (receives prior_results).
OVERVIEW_ANALYSIS = ("Overview KPIs", analyze_overview)


def run_all_referral_analyses(
    ctx: ReferralContext,
    on_progress: Callable | None = None,
) -> list[AnalysisResult]:
    """Run all registered referral analyses and return results."""
    results: list[AnalysisResult] = []
    total = len(REFERRAL_ANALYSIS_REGISTRY)

    for i, (name, func) in enumerate(REFERRAL_ANALYSIS_REGISTRY):
        if on_progress:
            on_progress(i, total, name)

        try:
            result = func(ctx)
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

    # Run overview last with prior results
    name, func = OVERVIEW_ANALYSIS
    if on_progress:
        on_progress(total, total + 1, name)
    try:
        result = func(ctx, prior_results=results)
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
