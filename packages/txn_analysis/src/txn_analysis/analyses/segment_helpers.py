"""Shared helpers for M18-M22: 3-way ARS segmentation + ODD merge.

Extracts Responder / Non-Responder / Control segments from ODD
Segmentation columns (created by format_odd step 7) and merges
them onto transaction data for cross-segment analysis.
"""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

_SEG_COL_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Segmentation$")

SEGMENT_ORDER = ["Responder", "Non-Responder", "Control"]


def detect_acct_col(odd_df: pd.DataFrame) -> str | None:
    """Find the account number column in ODD."""
    for col in ("Acct Number", "Account Number", "Account_Number"):
        if col in odd_df.columns:
            return col
    return None


def extract_ars_segments(odd_df: pd.DataFrame) -> dict[str, set[str]]:
    """Extract 3-way ARS segmentation from ODD Segmentation columns.

    Returns ``{"Responder": {accts}, "Non-Responder": {accts}, "Control": {accts}}``.
    Uses the **latest** ``MmmYY Segmentation`` column found in ODD
    (sorted alphabetically -- the last is the most recent campaign month).
    """
    seg_cols = sorted(c for c in odd_df.columns if _SEG_COL_RE.match(c))
    if not seg_cols:
        logger.info("No Segmentation columns found in ODD")
        return {}

    acct_col = detect_acct_col(odd_df)
    if acct_col is None:
        logger.warning("No account number column found in ODD")
        return {}

    latest = seg_cols[-1]
    logger.info("Using segmentation column: %s", latest)

    result: dict[str, set[str]] = {}
    for label in SEGMENT_ORDER:
        mask = odd_df[latest].astype(str).str.strip() == label
        accts = set(odd_df.loc[mask, acct_col].dropna().astype(str).str.strip())
        if accts:
            result[label] = accts

    total = sum(len(v) for v in result.values())
    logger.info(
        "ARS segments: %s (%d total accounts)", {k: len(v) for k, v in result.items()}, total
    )
    return result


def merge_segments_to_txn(
    txn_df: pd.DataFrame,
    odd_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add ``ars_segment`` column to *txn_df* via account number merge.

    Accounts not found in any segment are labelled "Unknown".
    Returns a copy -- does not mutate *txn_df*.
    """
    segments = extract_ars_segments(odd_df)
    if not segments:
        out = txn_df.copy()
        out["ars_segment"] = "Unknown"
        return out

    acct_col = detect_acct_col(odd_df)
    if acct_col is None:
        out = txn_df.copy()
        out["ars_segment"] = "Unknown"
        return out

    # Build acct -> segment lookup
    lookup: dict[str, str] = {}
    for label, accts in segments.items():
        for a in accts:
            lookup[a] = label

    out = txn_df.copy()
    out["ars_segment"] = (
        out["primary_account_num"].astype(str).str.strip().map(lookup).fillna("Unknown")
    )
    return out


def classify_spending_tiers(
    txn_df: pd.DataFrame,
    *,
    low_pct: float = 33.3,
    high_pct: float = 66.7,
) -> pd.DataFrame:
    """Add ``spending_tier`` column (Low/Medium/High Spender) based on per-account total spend.

    Thresholds are computed from tercile percentiles of per-account spend.
    Returns a copy with the new column.
    """
    acct_spend = txn_df.groupby("primary_account_num")["amount"].sum()
    t_low = acct_spend.quantile(low_pct / 100)
    t_high = acct_spend.quantile(high_pct / 100)

    spend_map = {}
    for acct, total in acct_spend.items():
        if total <= t_low:
            spend_map[acct] = "Low Spender"
        elif total <= t_high:
            spend_map[acct] = "Medium Spender"
        else:
            spend_map[acct] = "High Spender"

    out = txn_df.copy()
    out["spending_tier"] = out["primary_account_num"].map(spend_map).fillna("Low Spender")
    return out


TIER_ORDER = ["Low Spender", "Medium Spender", "High Spender"]
