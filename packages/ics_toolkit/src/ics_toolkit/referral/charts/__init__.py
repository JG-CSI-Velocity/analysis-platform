"""Referral chart registry and dispatcher."""

import logging
from collections.abc import Callable

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.charts.branch_density import chart_branch_density
from ics_toolkit.referral.charts.code_health import chart_code_health
from ics_toolkit.referral.charts.emerging_referrers import chart_emerging_referrers
from ics_toolkit.referral.charts.staff_multipliers import chart_staff_multipliers
from ics_toolkit.referral.charts.top_referrers import chart_top_referrers
from ics_toolkit.settings import ChartConfig

logger = logging.getLogger(__name__)

REFERRAL_CHART_REGISTRY: dict[str, Callable] = {
    "Top Referrers": chart_top_referrers,
    "Emerging Referrers": chart_emerging_referrers,
    "Staff Multipliers": chart_staff_multipliers,
    "Branch Influence Density": chart_branch_density,
    "Code Health Report": chart_code_health,
}


def create_referral_charts(
    analyses: list[AnalysisResult],
    config: ChartConfig,
) -> dict[str, bytes]:
    """Build chart PNGs for referral analyses that have chart builders."""
    chart_pngs: dict[str, bytes] = {}

    for analysis in analyses:
        if analysis.error is not None or analysis.df.empty:
            continue

        builder = REFERRAL_CHART_REGISTRY.get(analysis.name)
        if builder is None:
            continue

        try:
            png_bytes = builder(analysis.df, config)
            if png_bytes:
                chart_pngs[analysis.name] = png_bytes
        except Exception as e:
            logger.warning("Chart for '%s' failed: %s", analysis.name, e)

    return chart_pngs
