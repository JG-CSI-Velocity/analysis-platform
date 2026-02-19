"""Safe accessors for upstream ctx.results -- zero defaults on missing data."""

from __future__ import annotations

from loguru import logger

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.pipeline.context import PipelineContext

# -- Safe wrapper ------------------------------------------------------------


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run analysis function, catch errors, return failed result on exception."""
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(
            slide_id=label, title=label, success=False, error=str(exc),
        )]


# -- Value accessors ---------------------------------------------------------


def get_value_1(ctx: PipelineContext) -> dict:
    """Debit card value results from A11.1."""
    return ctx.results.get("value_1", {
        "delta": 0, "accts_with": 0, "accts_without": 0,
        "rev_per_with": 0, "rev_per_without": 0,
        "hist_dctr": 0, "l12m_dctr": 0,
        "pot_hist": 0, "pot_l12m": 0, "pot_100": 0,
    })


def get_value_2(ctx: PipelineContext) -> dict:
    """Reg E value results from A11.2."""
    return ctx.results.get("value_2", {
        "delta": 0, "accts_with": 0, "accts_without": 0,
        "rev_per_with": 0, "rev_per_without": 0,
        "hist_rege": 0, "l12m_rege": 0,
        "pot_hist": 0, "pot_l12m": 0, "pot_100": 0,
    })


# -- Attrition accessors -----------------------------------------------------


def get_attrition_1(ctx: PipelineContext) -> dict:
    """Overall attrition results from A9.1."""
    return ctx.results.get("attrition_1", {
        "overall_rate": 0, "l12m_rate": 0, "total": 0, "closed": 0,
    })


def get_attrition_9(ctx: PipelineContext) -> dict:
    """Debit retention lift from A9.9."""
    return ctx.results.get("attrition_9", {"retention_lift": 0})


def get_attrition_10(ctx: PipelineContext) -> dict:
    """Mailer retention lift from A9.10."""
    return ctx.results.get("attrition_10", {"lift": 0})


def get_attrition_11(ctx: PipelineContext) -> dict:
    """Revenue impact from A9.11."""
    return ctx.results.get("attrition_11", {"total_lost": 0, "avg_lost": 0})


def get_attrition_12(ctx: PipelineContext) -> dict:
    """Velocity data from A9.12."""
    return ctx.results.get("attrition_12", {"total_l12m": 0, "trend": ""})


# -- DCTR accessors ----------------------------------------------------------


def get_dctr_1(ctx: PipelineContext) -> dict:
    """Historical DCTR from DCTR-1."""
    r = ctx.results.get("dctr_1", {})
    return r.get("insights", {
        "overall_dctr": 0, "recent_dctr": 0, "total_accounts": 0,
    })


def get_dctr_3(ctx: PipelineContext) -> dict:
    """L12M DCTR from DCTR-3."""
    r = ctx.results.get("dctr_3", {})
    return r.get("insights", {"dctr": 0, "total_accounts": 0})


def get_dctr_9(ctx: PipelineContext) -> dict:
    """Branch DCTR insights from DCTR-9."""
    r = ctx.results.get("dctr_9", {})
    return r.get("all", {
        "total_branches": 0,
        "best_branch": "", "best_dctr": 0,
        "worst_branch": "", "worst_dctr": 0,
    })


# -- Reg E accessors ---------------------------------------------------------


def get_reg_e_1(ctx: PipelineContext) -> dict:
    """Reg E status from A8.1."""
    return ctx.results.get("reg_e_1", {
        "opt_in_rate": 0, "l12m_rate": 0,
        "total_base": 0, "opted_in": 0, "opted_out": 0,
    })


# -- Mailer accessors --------------------------------------------------------


def get_market_reach(ctx: PipelineContext) -> dict:
    """Market reach from A15.1."""
    return ctx.results.get("market_reach", {
        "n_eligible": 0, "n_responders": 0, "n_mailed": 0, "penetration": 0,
    })


def get_revenue_attribution(ctx: PipelineContext) -> dict:
    """Revenue attribution from A15.3."""
    return ctx.results.get("revenue_attribution", {
        "resp_ic": 0, "non_ic": 0, "incremental_total": 0,
    })


def get_pre_post_delta(ctx: PipelineContext) -> dict:
    """Pre/post spend delta from A15.4."""
    return ctx.results.get("pre_post_delta", {
        "resp_pre": 0, "resp_post": 0, "resp_delta": 0,
        "non_pre": 0, "non_post": 0, "non_delta": 0,
    })


# -- Overview accessors ------------------------------------------------------


def get_a3(ctx: PipelineContext) -> dict:
    """Eligibility funnel insights from A3."""
    r = ctx.results.get("a3", {})
    return r.get("insights", {
        "total_accounts": 0, "eligible_accounts": 0, "eligibility_rate": 0,
    })
