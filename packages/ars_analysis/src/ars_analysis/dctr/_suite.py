"""DCTR suite runner -- orchestrates all A6/A7 analyses in order."""

import traceback

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
    run_dctr_by_product,
    run_dctr_cohort_capture,
    run_dctr_executive_summary,
    run_dctr_months_to_transact,
    run_dctr_opportunity,
)
from ars_analysis.dctr._helpers import _report
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

# ---------------------------------------------------------------------------
# Slide merge/appendix configuration (used by pipeline.py consolidation)
# ---------------------------------------------------------------------------

DCTR_MERGES = [
    (
        "A7.6a - Last 12 Months DCTR Trend",
        "A7.4 - Segment Trends",
        "DCTR Recent Trend & Account Types",
    ),
    ("A7.7 - Historical Funnel", "A7.8 - L12M Funnel", "DCTR Funnel: Historical vs TTM"),
    (
        "A7.11 - DCTR by Account Holder Age",
        "A7.12 - DCTR by Account Age",
        "DCTR Opportunity: Age Analysis",
    ),
]

DCTR_APPENDIX_IDS = {
    "A7.5 - Decade Trend",
    "A7.6b - Personal vs Business by Decade",
    "A7.13 - Monthly Heatmap",
    "A7.14 - Seasonality",
    "A7.15 - Vintage & Cohort",
    "A7.16 - Branch L12M Table",
    "A7.9 - Eligible vs Non-Eligible DCTR",
    "A7.10b - Branch DCTR (L12M Focus)",
    "A7.10c - Branch Top 10",
    "A7.22 - Holder Age × Balance Heatmap",
    "A7.23 - Account Age × Balance Heatmap",
    "A7.24 - Branch × Account Age Heatmap",
}

# Slide ordering for the final deck
DCTR_ORDER = [
    # Act 0: Executive Summary
    "A7.0 - DCTR Executive Summary",
    # Act 1: The Headline
    "A7 - DCTR Comparison",
    # Act 2: Recent Trajectory
    "A7.6a - Last 12 Months DCTR Trend",
    "A7.4 - Segment Trends",
    "A7.19 - DCTR by Product Type",
    # Act 3: The Funnel (Root Cause)
    "A7.8 - L12M Funnel",
    "A7.7 - Historical Funnel",
    # Act 4: Branch Accountability
    "A7.10a - Branch DCTR (Hist vs L12M)",
    # Act 4b: Activation & Onboarding
    "A7.17 - Months to Transact",
    "A7.20 - Cohort Debit Capture",
    # Act 5: The Opportunity
    "A7.18 - DCTR Opportunity",
    "A7.9 - Eligible vs Non-Eligible DCTR",
    "A7.11 - DCTR by Account Holder Age",
    "A7.12 - DCTR by Account Age",
    # Act 6: Remaining Branch Detail
    "A7.10b - Branch DCTR (L12M Focus)",
    "A7.10c - Branch Top 10",
    # Act 7: Supporting Detail
    "A7.5 - Decade Trend",
    "A7.6b - Personal vs Business by Decade",
    "A7.13 - Monthly Heatmap",
    "A7.14 - Seasonality",
    "A7.15 - Vintage & Cohort",
    "A7.16 - Branch L12M Table",
    "A7.22 - Holder Age × Balance Heatmap",
    "A7.23 - Account Age × Balance Heatmap",
    "A7.24 - Branch × Account Age Heatmap",
]


def run_dctr_suite(ctx):
    """Run the full DCTR analysis suite (A6 + A7 combined)."""
    from ars_analysis.pipeline import save_to_excel

    ctx["_save_to_excel"] = save_to_excel

    def _safe(fn, label):
        """Run an analysis function; log errors and continue."""
        try:
            return fn(ctx)
        except Exception as e:
            _report(ctx, f"   ⚠️ {label} failed: {e}")
            traceback.print_exc()
            return ctx

    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "💳 A6/A7 — DEBIT CARD TAKE RATE (DCTR) ANALYSIS")
    _report(ctx, "=" * 60)

    # Core A6 data analyses
    _report(ctx, "\n── A6: Core DCTR Data ──")
    ctx = _safe(run_dctr_1, "DCTR-1")
    ctx = _safe(run_dctr_2, "DCTR-2")
    ctx = _safe(run_dctr_3, "DCTR-3")
    ctx = _safe(run_dctr_4_5, "DCTR-4/5")
    ctx = _safe(run_dctr_6_7, "DCTR-6/7")
    ctx = _safe(run_dctr_8, "DCTR-8")

    _report(ctx, "\n── A6: Branch & Dimensional ──")
    ctx = _safe(run_dctr_9, "DCTR-9")
    ctx = _safe(run_dctr_10, "DCTR-10")
    ctx = _safe(run_dctr_11, "DCTR-11")
    ctx = _safe(run_dctr_12, "DCTR-12")
    ctx = _safe(run_dctr_13, "DCTR-13")
    ctx = _safe(run_dctr_14, "DCTR-14")
    ctx = _safe(run_dctr_15, "DCTR-15")
    ctx = _safe(run_dctr_16, "DCTR-16")

    # New analyses (Sprints 3 & 4)
    _report(ctx, "\n── A6: New Analyses ──")
    ctx = _safe(run_dctr_opportunity, "Opportunity")
    ctx = _safe(run_dctr_by_product, "Product Type")
    ctx = _safe(run_dctr_months_to_transact, "Months to Transact")
    ctx = _safe(run_dctr_cohort_capture, "Cohort Capture")

    # Extended A7 visualizations
    _report(ctx, "\n── A7: Extended Visualizations ──")
    ctx = _safe(run_dctr_segment_trends, "Segment Trends")
    ctx = _safe(run_dctr_decade_trend, "Decade Trend")
    ctx = _safe(run_dctr_decade_pb, "Decade P/B")
    ctx = _safe(run_dctr_l12m_trend, "L12M Trend")
    ctx = _safe(run_dctr_funnel, "Funnel")
    ctx = _safe(run_dctr_l12m_funnel, "L12M Funnel")
    ctx = _safe(run_dctr_eligible_vs_non, "Eligible vs Non")
    ctx = _safe(run_dctr_branch_trend, "Branch Trend")
    ctx = _safe(run_dctr_branch_l12m, "Branch L12M")
    ctx = _safe(run_dctr_heatmap, "Heatmap")
    ctx = _safe(run_dctr_seasonality, "Seasonality")
    ctx = _safe(run_dctr_vintage, "Vintage")
    ctx = _safe(run_dctr_combo_slide, "Combo Slide")

    # Executive summary runs LAST (reads from all results)
    _report(ctx, "\n── A7: Executive Summary ──")
    ctx = _safe(run_dctr_executive_summary, "Executive Summary")

    # Reorder DCTR slides to match mapping sequence
    order_map = {sid: i for i, sid in enumerate(DCTR_ORDER)}
    dctr_slides = [s for s in ctx["all_slides"] if s["category"] == "DCTR"]
    non_dctr = [s for s in ctx["all_slides"] if s["category"] != "DCTR"]
    dctr_slides.sort(key=lambda s: order_map.get(s["id"], 999))
    ctx["all_slides"] = non_dctr + dctr_slides

    slides = len(dctr_slides)
    _report(ctx, f"\n✅ A6/A7 complete — {slides} DCTR slides created (reordered to mapping)")
    return ctx
