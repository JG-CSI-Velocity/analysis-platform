"""Reg E suite runner -- orchestrates A8.0 through A8.16."""

import traceback

from ars_analysis.reg_e._core import (
    run_reg_e_1,
    run_reg_e_2,
    run_reg_e_3,
    run_reg_e_4,
    run_reg_e_4b,
    run_reg_e_5,
    run_reg_e_6,
    run_reg_e_7,
    run_reg_e_8,
    run_reg_e_9,
    run_reg_e_10,
    run_reg_e_11,
    run_reg_e_12,
    run_reg_e_13,
    run_reg_e_cohort,
    run_reg_e_executive_summary,
    run_reg_e_opportunity,
    run_reg_e_seasonality,
)
from ars_analysis.reg_e._helpers import _reg_col, _report

# -- Slide ordering (narrative arc) ----------------------------------------

REG_ORDER = [
    # Act 0: Executive Summary (placed first)
    "A8.0 - Reg E Executive Summary",
    # Act 1: The Headline
    "A8.1 - Reg E Overall Status",
    # Act 2: Trajectory
    "A8.12 - Reg E Trend",
    "A8.3 - Reg E L12M Monthly",
    # Act 3: The Funnel (Diagnosis)
    "A8.11 - Reg E L12M Funnel",
    "A8.10 - Reg E All-Time Funnel",
    # Act 4: The Opportunity
    "A8.14 - Reg E Opportunity",
    "A8.5 - Reg E by Account Age",
    "A8.6 - Reg E by Holder Age",
    "A8.15 - Reg E Cohort Analysis",
    "A8.7 - Reg E by Product",
    # Act 5: Branch Accountability
    "A8.4b - Reg E by Branch (Vertical)",
    "A8.4a - Reg E by Branch",
    "A8.4c - Reg E Branch Scatter",
    # Act 6: Historical Context
    "A8.2 - Reg E Historical",
    # Act 7: Appendix
    "A8.16 - Reg E Seasonality",
    "A8.8a - Reg E Heatmap (Open Personal)",
    "A8.8b - Reg E Heatmap (Eligible Personal)",
    "A8.9a - Reg E Branch Summary (Open)",
    "A8.9b - Reg E Branch Summary (Eligible)",
]

# -- Slide merges and appendix IDs (moved from pipeline.py) ----------------

REGE_MERGES = [
    (
        "A8.10 - Reg E All-Time Funnel",
        "A8.11 - Reg E L12M Funnel",
        "Reg E Funnel: All-Time vs TTM",
    ),
    (
        "A8.5 - Reg E by Account Age",
        "A8.6 - Reg E by Holder Age",
        "Reg E Opportunity: Age Analysis",
    ),
]

REGE_APPENDIX_IDS = {
    "A8.7 - Reg E by Product",
    "A8.4c - Reg E Branch Scatter",
    "A8.2 - Reg E Historical",
    "A8.1 - Reg E Overall Status",
    "A8.12 - Reg E Trend",
    "A8.4b - Reg E by Branch (Vertical)",
    "A8.16 - Reg E Seasonality",
    "A8.8a - Reg E Heatmap (Open Personal)",
    "A8.8b - Reg E Heatmap (Eligible Personal)",
    "A8.9a - Reg E Branch Summary (Open)",
    "A8.9b - Reg E Branch Summary (Eligible)",
}


# -- Suite runner -----------------------------------------------------------


def run_reg_e_suite(ctx):
    """Run the full Reg E analysis suite (A8)."""
    from ars_analysis.pipeline import save_to_excel

    ctx["_save_to_excel"] = save_to_excel

    # Guard -- skip if no Reg E data
    if ctx.get("reg_e_eligible_base") is None or ctx["reg_e_eligible_base"].empty:
        _report(ctx, "\n⚠️ A8 — Skipped (no Reg E eligible accounts)")
        return ctx
    if _reg_col(ctx) is None:
        _report(ctx, "\n⚠️ A8 — Skipped (no Reg E column found)")
        return ctx

    def _safe(fn, label):
        """Run an analysis function; log errors and continue."""
        try:
            return fn(ctx)
        except Exception as e:
            _report(ctx, f"   ⚠️ {label} failed: {e}")
            traceback.print_exc()
            return ctx

    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "📋 A8 — REG E OPT-IN ANALYSIS")
    _report(ctx, "=" * 60)

    # Core data analyses
    _report(ctx, "\n── A8: Core Reg E Data ──")
    ctx = _safe(run_reg_e_1, "A8.1")
    ctx = _safe(run_reg_e_2, "A8.2")
    ctx = _safe(run_reg_e_3, "A8.3")

    _report(ctx, "\n── A8: Branch & Dimensional ──")
    ctx = _safe(run_reg_e_4, "A8.4")
    ctx = _safe(run_reg_e_4b, "A8.4b")
    ctx = _safe(run_reg_e_5, "A8.5")
    ctx = _safe(run_reg_e_6, "A8.6")
    ctx = _safe(run_reg_e_7, "A8.7")

    _report(ctx, "\n── A8: Heatmaps & Summaries ──")
    ctx = _safe(run_reg_e_8, "A8.8")
    ctx = _safe(run_reg_e_9, "A8.9")

    _report(ctx, "\n── A8: Funnels & Trends ──")
    ctx = _safe(run_reg_e_10, "A8.10")
    ctx = _safe(run_reg_e_11, "A8.11")
    ctx = _safe(run_reg_e_12, "A8.12")
    ctx = _safe(run_reg_e_13, "A8.13")

    # New analyses (Sprint 3+4)
    _report(ctx, "\n── A8: Opportunity, Cohort & Summary ──")
    ctx = _safe(run_reg_e_opportunity, "A8.14")
    ctx = _safe(run_reg_e_cohort, "A8.15")
    ctx = _safe(run_reg_e_seasonality, "A8.16")
    ctx = _safe(run_reg_e_executive_summary, "A8.0")

    # Reorder slides to narrative arc
    reg_slides = [s for s in ctx["all_slides"] if s["category"] == "Reg E"]
    non_reg = [s for s in ctx["all_slides"] if s["category"] != "Reg E"]
    order_map = {sid: i for i, sid in enumerate(REG_ORDER)}
    reg_slides.sort(key=lambda s: order_map.get(s["id"], 999))
    ctx["all_slides"] = non_reg + reg_slides

    slides = len(reg_slides)
    _report(ctx, f"\n✅ A8 complete — {slides} Reg E slides created (reordered to mapping)")
    return ctx
