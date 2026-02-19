"""Shared mailer constants and helpers used by insights, response, and impact.

Ported from mailer_common.py (144 lines).
"""

from __future__ import annotations

import re

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# Segment constants
# ---------------------------------------------------------------------------

RESPONSE_SEGMENTS = ["NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"]
MAILED_SEGMENTS = ["NU", "TH-10", "TH-15", "TH-20", "TH-25"]
TH_SEGMENTS = ["TH-10", "TH-15", "TH-20", "TH-25"]

# Column-name patterns
SPEND_PATTERN = re.compile(r"^[A-Z][a-z]{2}\d{2} Spend$")
SWIPE_PATTERN = re.compile(r"^[A-Z][a-z]{2}\d{2} Swipes$")

# Segment colors (shared across all mailer modules)
SEGMENT_COLORS: dict[str, str] = {
    "No-Mail": "#F5F5F5",
    "Non-Responders": "#404040",
    "NU 5+": "#E74C3C",
    "NU": "#E74C3C",
    "TH-10": "#3498DB",
    "TH-15": "#2ECC71",
    "TH-20": "#F39C12",
    "TH-25": "#9B59B6",
}

# Valid response mapping per mailed segment
VALID_RESPONSES: dict[str, list[str]] = {
    "NU": ["NU 5+"],
    "TH-10": ["TH-10"],
    "TH-15": ["TH-15"],
    "TH-20": ["TH-20"],
    "TH-25": ["TH-25"],
}

# Account-age buckets for A14.2
AGE_SEGMENTS: list[tuple[str, int, int]] = [
    ("< 2 years", 0, 2),
    ("2-5 years", 2, 5),
    ("5-10 years", 5, 10),
    ("10-20 years", 10, 20),
    ("> 20 years", 20, 999),
]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_month(col_name: str) -> pd.Timestamp:
    """Parse MmmYY from a column name like 'Aug25 Mail' -> Timestamp."""
    try:
        return pd.to_datetime(col_name.split(" ")[0], format="%b%y")
    except Exception:
        return pd.NaT


def format_title(month_str: str) -> str:
    """Convert 'Aug25' -> 'August 2025'."""
    try:
        dt = pd.to_datetime(month_str, format="%b%y")
        return dt.strftime("%B %Y")
    except Exception:
        return month_str


# ---------------------------------------------------------------------------
# Column discovery
# ---------------------------------------------------------------------------


def discover_pairs(ctx: PipelineContext) -> list[tuple[str, str, str]]:
    """Return sorted list of (month, resp_col, mail_col) tuples.

    Caches result in ctx.results['_mailer_pairs'].
    """
    cached = ctx.results.get("_mailer_pairs")
    if cached:
        return cached

    if ctx.data is None:
        return []

    cols = list(ctx.data.columns)
    mail_cols = sorted(
        [c for c in cols if re.match(r"^[A-Z][a-z]{2}\d{2} Mail$", c)],
        key=parse_month,
    )

    pairs: list[tuple[str, str, str]] = []
    for mc in mail_cols:
        month = mc.replace(" Mail", "")
        rc = f"{month} Resp"
        if rc in cols and ctx.data[rc].notna().any():
            pairs.append((month, rc, mc))

    # Client-specific cutoff for client 1200
    if ctx.client.client_id == "1200" and pairs:
        cutoff = pd.to_datetime("Apr24", format="%b%y")
        pairs = [(m, r, ml) for m, r, ml in pairs if parse_month(m) >= cutoff]

    ctx.results["_mailer_pairs"] = pairs
    return pairs


def discover_metric_cols(
    ctx: PipelineContext,
) -> tuple[list[str], list[str]]:
    """Return (spend_cols, swipe_cols) sorted chronologically."""
    if ctx.data is None:
        return [], []

    cols = list(ctx.data.columns)
    spend_cols = sorted(
        [c for c in cols if SPEND_PATTERN.match(c)], key=parse_month
    )
    swipe_cols = sorted(
        [c for c in cols if SWIPE_PATTERN.match(c)], key=parse_month
    )

    if ctx.client.client_id == "1200":
        cutoff = pd.to_datetime("Apr24", format="%b%y")
        spend_cols = [c for c in spend_cols if parse_month(c) >= cutoff]
        swipe_cols = [c for c in swipe_cols if parse_month(c) >= cutoff]

    return spend_cols, swipe_cols


# ---------------------------------------------------------------------------
# Mask builders
# ---------------------------------------------------------------------------


def build_responder_mask(
    data: pd.DataFrame, pairs: list[tuple[str, str, str]]
) -> pd.Series:
    """Boolean Series: True for any account that responded in any month."""
    mask = pd.Series(False, index=data.index)
    for _, resp_col, _ in pairs:
        mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
    return mask


def build_mailed_mask(
    data: pd.DataFrame, pairs: list[tuple[str, str, str]]
) -> pd.Series:
    """Boolean Series: True for any account mailed in any month."""
    mask = pd.Series(False, index=data.index)
    for _, _, mail_col in pairs:
        mask |= data[mail_col].isin(MAILED_SEGMENTS)
    return mask


# ---------------------------------------------------------------------------
# Month-level segment analysis (used by response module)
# ---------------------------------------------------------------------------


def analyze_month(
    data: pd.DataFrame, resp_col: str, mail_col: str
) -> tuple[dict, int, int, float]:
    """Compute response stats for one mail month.

    Returns (seg_details, total_mailed, total_resp, overall_rate).
    seg_details: dict keyed by display segment with {mailed, responders, rate}.
    """
    seg_details: dict = {}
    for seg in MAILED_SEGMENTS:
        seg_data = data[data[mail_col] == seg]
        n_mailed = len(seg_data)
        if n_mailed == 0:
            continue
        valid = VALID_RESPONSES[seg]
        n_resp = len(seg_data[seg_data[resp_col].isin(valid)])
        rate = n_resp / n_mailed * 100 if n_mailed > 0 else 0
        display = "NU 5+" if seg == "NU" else seg
        seg_details[display] = {
            "mailed": n_mailed,
            "responders": n_resp,
            "rate": rate,
        }

    total_mailed = sum(d["mailed"] for d in seg_details.values())
    total_resp = sum(d["responders"] for d in seg_details.values())
    overall_rate = total_resp / total_mailed * 100 if total_mailed > 0 else 0

    return seg_details, total_mailed, total_resp, overall_rate


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
