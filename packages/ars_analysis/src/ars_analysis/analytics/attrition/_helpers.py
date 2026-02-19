"""Shared attrition constants, categorization helpers, and data prep.

Ported from attrition.py helpers/categorization sections (~170 lines).
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# Ordered category constants
# ---------------------------------------------------------------------------

DURATION_ORDER = [
    "0-1 Month",
    "1-3 Months",
    "3-6 Months",
    "6-12 Months",
    "1-2 Years",
    "2-5 Years",
    "5-10 Years",
    "10+ Years",
]

TENURE_ORDER = [
    "0-6 Months",
    "6-12 Months",
    "1-2 Years",
    "2-5 Years",
    "5-10 Years",
    "10+ Years",
]

BALANCE_ORDER = [
    "Negative",
    "$0",
    "$1-$499",
    "$500-$999",
    "$1K-$2.5K",
    "$2.5K-$5K",
    "$5K-$10K",
    "$10K+",
]


# ---------------------------------------------------------------------------
# Categorization functions
# ---------------------------------------------------------------------------


def categorize_duration(days: float) -> str | None:
    """Bucket account lifespan (days open -> close) into duration categories."""
    if pd.isna(days) or days < 0:
        return None
    months = days / 30.44
    if months <= 1:
        return "0-1 Month"
    if months <= 3:
        return "1-3 Months"
    if months <= 6:
        return "3-6 Months"
    if months <= 12:
        return "6-12 Months"
    years = days / 365.25
    if years <= 2:
        return "1-2 Years"
    if years <= 5:
        return "2-5 Years"
    if years <= 10:
        return "5-10 Years"
    return "10+ Years"


def categorize_tenure(days: float) -> str | None:
    """Bucket account tenure (days since opened) into categories."""
    if pd.isna(days) or days < 0:
        return None
    months = days / 30.44
    if months <= 6:
        return "0-6 Months"
    if months <= 12:
        return "6-12 Months"
    years = days / 365.25
    if years <= 2:
        return "1-2 Years"
    if years <= 5:
        return "2-5 Years"
    if years <= 10:
        return "5-10 Years"
    return "10+ Years"


def categorize_balance(bal: float) -> str | None:
    """Bucket average balance into tiers."""
    if pd.isna(bal):
        return None
    if bal < 0:
        return "Negative"
    if bal == 0:
        return "$0"
    if bal < 500:
        return "$1-$499"
    if bal < 1000:
        return "$500-$999"
    if bal < 2500:
        return "$1K-$2.5K"
    if bal < 5000:
        return "$2.5K-$5K"
    if bal < 10000:
        return "$5K-$10K"
    return "$10K+"


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------


def product_col(df: pd.DataFrame) -> str | None:
    """Detect product code column ('Product Code' or legacy 'Prod Code')."""
    if "Product Code" in df.columns:
        return "Product Code"
    if "Prod Code" in df.columns:
        return "Prod Code"
    return None


# ---------------------------------------------------------------------------
# Data preparation (cached)
# ---------------------------------------------------------------------------


def prepare_attrition_data(
    ctx: PipelineContext,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (all_data, open_accts, closed_accts), cached in ctx.results."""
    cached = ctx.results.get("_attrition_data")
    if cached is not None:
        return cached

    data = ctx.data
    if data is None:
        empty = pd.DataFrame()
        return empty, empty, empty

    open_accts = data[data["Date Closed"].isna()].copy()
    closed_accts = data[data["Date Closed"].notna()].copy()

    if not closed_accts.empty:
        closed_accts["_duration_days"] = (
            closed_accts["Date Closed"] - closed_accts["Date Opened"]
        ).dt.days
        closed_accts["_duration_cat"] = closed_accts["_duration_days"].apply(
            categorize_duration
        )

    result = (data, open_accts, closed_accts)
    ctx.results["_attrition_data"] = result
    return result


# ---------------------------------------------------------------------------
# Safe wrapper
# ---------------------------------------------------------------------------


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run analysis function, catch errors, return failed result on exception."""
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(
            slide_id=label, title=label, success=False, error=str(exc),
        )]
