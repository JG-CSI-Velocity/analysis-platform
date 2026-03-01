"""Segment extraction from ODD data for cross-pipeline filtering.

Builds account-number sets from ODD columns so the transaction pipeline
can run analyses on filtered subsets (e.g. ARS responders only, ICS
account holders only).

No cross-package imports -- duplicates constants to avoid ars_analysis
or ics_toolkit dependency.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


def _normalize_acct(val: str) -> str:
    """Strip trailing '.0' from account numbers (CSV float artifact)."""
    val = val.strip()
    if val.endswith(".0"):
        val = val[:-2]
    return val


# ARS response segment codes (from ars_analysis/analytics/mailer/_helpers.py)
RESPONSE_SEGMENTS: frozenset[str] = frozenset({"NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"})

# Pattern matching MmmYY Resp columns (e.g. "Aug25 Resp", "Jan24 Resp")
_RESP_COL_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Resp$")


def extract_responder_accounts(odd_df: pd.DataFrame) -> set[str]:
    """Return Acct Numbers where the account responded to an ARS mailer.

    An account is a responder if ANY ``MmmYY Resp`` column contains a
    value in RESPONSE_SEGMENTS.  Returns empty set if no Resp columns
    found or no responders detected.
    """
    resp_cols = [c for c in odd_df.columns if _RESP_COL_RE.match(c)]
    if not resp_cols:
        logger.info("No Resp columns found in ODD -- skipping ARS responder segment")
        return set()

    if "Acct Number" not in odd_df.columns:
        logger.warning("ODD missing 'Acct Number' column")
        return set()

    mask = pd.Series(False, index=odd_df.index)
    for col in resp_cols:
        mask |= odd_df[col].isin(RESPONSE_SEGMENTS)

    accts = {_normalize_acct(v) for v in odd_df.loc[mask, "Acct Number"].dropna().astype(str)}
    logger.info(
        "ARS responder segment: %d accounts from %d Resp columns",
        len(accts),
        len(resp_cols),
    )
    return accts


def extract_ics_accounts(odd_df: pd.DataFrame) -> set[str]:
    """Return Acct Numbers where ICS Account == 'Yes'.

    Returns empty set if the ICS Account column is missing.
    """
    # Detect column (handle aliases)
    ics_col = None
    for candidate in ("ICS Account", "ICS Accounts", "Ics Account", "ICS_Account"):
        if candidate in odd_df.columns:
            ics_col = candidate
            break

    if ics_col is None:
        logger.info("No ICS Account column found in ODD -- skipping ICS segment")
        return set()

    if "Acct Number" not in odd_df.columns:
        logger.warning("ODD missing 'Acct Number' column")
        return set()

    mask = odd_df[ics_col].astype(str).str.strip().str.lower() == "yes"
    accts = {_normalize_acct(v) for v in odd_df.loc[mask, "Acct Number"].dropna().astype(str)}
    logger.info("ICS account segment: %d accounts", len(accts))
    return accts


@dataclass(frozen=True)
class SegmentFilter:
    """A named data segment for comparative analysis."""

    name: str  # e.g. "ars_responders"
    label: str  # e.g. "ARS Responders"
    account_numbers: frozenset[str]

    def filter_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return only transactions belonging to this segment's accounts."""
        normalized = df["primary_account_num"].astype(str).map(_normalize_acct)
        return df[normalized.isin(self.account_numbers)]


def build_segment_filters(
    odd_df: pd.DataFrame | None,
    *,
    ars_responders: bool = False,
    ics_accounts: bool = False,
) -> list[SegmentFilter]:
    """Build requested segment filters from ODD data.

    Only creates filters that have at least 1 account.
    """
    if odd_df is None:
        return []

    filters: list[SegmentFilter] = []

    if ars_responders:
        accts = extract_responder_accounts(odd_df)
        if accts:
            filters.append(
                SegmentFilter(
                    name="ars_responders",
                    label="ARS Responders",
                    account_numbers=frozenset(accts),
                )
            )

    if ics_accounts:
        accts = extract_ics_accounts(odd_df)
        if accts:
            filters.append(
                SegmentFilter(
                    name="ics_accounts",
                    label="ICS Account Holders",
                    account_numbers=frozenset(accts),
                )
            )

    return filters
