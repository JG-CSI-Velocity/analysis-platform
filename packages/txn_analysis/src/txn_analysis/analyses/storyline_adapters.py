"""Thin adapters bridging V4 storyline run() functions into ANALYSIS_REGISTRY.

Each adapter converts main pipeline arguments (df, settings, context) into the
V4 context dict, calls the storyline's run(), and wraps the result in an
AnalysisResult.  If no ODD data is available, adapters that require it return
a graceful empty result.
"""

from __future__ import annotations

import logging

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)


def _build_storyline_ctx(
    df: pd.DataFrame,
    settings: Settings,
    context: dict | None,
) -> dict:
    """Convert main pipeline args to V4 storyline context dict."""
    ctx = context or {}
    return {
        "combined_df": df,
        "odd_df": ctx.get("odd_df", pd.DataFrame()),
        "config": {
            "client_name": settings.client_name or "",
            "client_id": settings.client_id or "",
        },
    }


def _wrap_storyline_result(
    name: str,
    result: dict,
) -> AnalysisResult:
    """Convert a V4 storyline result dict into an AnalysisResult."""
    sheets = result.get("sheets", [])
    primary_df = sheets[0]["df"] if sheets else pd.DataFrame()
    return AnalysisResult(
        name=name,
        title=result.get("title", name),
        df=primary_df,
        metadata={
            "storyline": result,
            "section_count": len(result.get("sections", [])),
            "chart_count": sum(len(s.get("figures", [])) for s in result.get("sections", [])),
            "sheet_count": len(sheets),
        },
    )


def analyze_demographics(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None,
) -> AnalysisResult:
    """M11: Demographics & Branch Performance (requires ODD)."""
    from txn_analysis.storylines.v4_s5_demographics import run

    ctx = _build_storyline_ctx(df, settings, context)
    result = run(ctx)
    return _wrap_storyline_result("demographics", result)


def analyze_campaigns(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None,
) -> AnalysisResult:
    """M12: Campaign Effectiveness (requires ODD campaign columns)."""
    from txn_analysis.storylines.v4_s7_campaigns import run

    ctx = _build_storyline_ctx(df, settings, context)
    result = run(ctx)
    return _wrap_storyline_result("campaigns", result)


def analyze_payroll(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None,
) -> AnalysisResult:
    """M13: Payroll & Circular Economy."""
    from txn_analysis.storylines.v4_s8_payroll import run

    ctx = _build_storyline_ctx(df, settings, context)
    result = run(ctx)
    return _wrap_storyline_result("payroll", result)


def analyze_lifecycle(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None,
) -> AnalysisResult:
    """M14: Lifecycle Management (requires ODD)."""
    from txn_analysis.storylines.v4_s9_lifecycle import run

    ctx = _build_storyline_ctx(df, settings, context)
    result = run(ctx)
    return _wrap_storyline_result("lifecycle", result)
