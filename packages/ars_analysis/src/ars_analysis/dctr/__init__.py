"""
dctr — Debit Card Take Rate (DCTR) Analysis Package
====================================================
Re-exports all public names for backward compatibility.

Usage:
    from ars_analysis.dctr import run_dctr_suite
    ctx = run_dctr_suite(ctx)
"""

from ars_analysis.dctr._categories import (
    categorize_account_age,
    categorize_balance,
    categorize_holder_age,
    map_to_decade,
    simplify_account_age,
)
from ars_analysis.dctr._constants import AGE_ORDER, BALANCE_ORDER, HOLDER_AGE_ORDER
from ars_analysis.dctr._core import (
    run_dctr_1,
    run_dctr_2,
    run_dctr_3,
    run_dctr_4_5,
    run_dctr_6_7,
    run_dctr_8,
    run_dctr_9,
    run_dctr_10,
    run_dctr_11,
    run_dctr_12,
    run_dctr_13,
    run_dctr_14,
    run_dctr_15,
    run_dctr_16,
)
from ars_analysis.dctr._helpers import _dctr
from ars_analysis.dctr._shared import analyze_historical_dctr
from ars_analysis.dctr._suite import (
    DCTR_APPENDIX_IDS,
    DCTR_MERGES,
    DCTR_ORDER,
    run_dctr_suite,
)
from ars_analysis.dctr._visualizations import (
    run_dctr_branch_l12m,
    run_dctr_branch_trend,
    run_dctr_combo_slide,
    run_dctr_decade_pb,
    run_dctr_decade_trend,
    run_dctr_eligible_vs_non,
    run_dctr_funnel,
    run_dctr_heatmap,
    run_dctr_l12m_funnel,
    run_dctr_l12m_trend,
    run_dctr_seasonality,
    run_dctr_segment_trends,
    run_dctr_vintage,
)

__all__ = [
    # Constants
    "AGE_ORDER",
    "BALANCE_ORDER",
    "HOLDER_AGE_ORDER",
    "DCTR_APPENDIX_IDS",
    "DCTR_MERGES",
    "DCTR_ORDER",
    # Categories
    "categorize_account_age",
    "categorize_balance",
    "categorize_holder_age",
    "map_to_decade",
    "simplify_account_age",
    # Helpers
    "_dctr",
    "analyze_historical_dctr",
    # Core (A6)
    "run_dctr_1",
    "run_dctr_2",
    "run_dctr_3",
    "run_dctr_4_5",
    "run_dctr_6_7",
    "run_dctr_8",
    "run_dctr_9",
    "run_dctr_10",
    "run_dctr_11",
    "run_dctr_12",
    "run_dctr_13",
    "run_dctr_14",
    "run_dctr_15",
    "run_dctr_16",
    # Visualizations (A7)
    "run_dctr_branch_l12m",
    "run_dctr_branch_trend",
    "run_dctr_combo_slide",
    "run_dctr_decade_pb",
    "run_dctr_decade_trend",
    "run_dctr_eligible_vs_non",
    "run_dctr_funnel",
    "run_dctr_heatmap",
    "run_dctr_l12m_funnel",
    "run_dctr_l12m_trend",
    "run_dctr_seasonality",
    "run_dctr_segment_trends",
    "run_dctr_vintage",
    # Suite
    "run_dctr_suite",
]
