"""Shared helpers for Reg E analysis modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from ars_analysis.analytics.dctr._helpers import debit_mask, detect_debit_col, filter_l12m
from ars_analysis.pipeline.context import PipelineContext

# -- Reg E-specific age buckets (differ from DCTR) ---------------------------

ACCT_AGE_ORDER = [
    "0-6 months",
    "6-12 months",
    "1-2 years",
    "2-5 years",
    "5-10 years",
    "10-20 years",
    "20+ years",
]

HOLDER_AGE_ORDER = [
    "18-24",
    "25-34",
    "35-44",
    "45-54",
    "55-64",
    "65-74",
    "75+",
]


def categorize_account_age(days: float) -> str:
    """Assign account age bucket (7 buckets for Reg E)."""
    if pd.isna(days):
        return "Unknown"
    if days < 180:
        return "0-6 months"
    if days < 365:
        return "6-12 months"
    if days < 730:
        return "1-2 years"
    if days < 1825:
        return "2-5 years"
    if days < 3650:
        return "5-10 years"
    if days < 7300:
        return "10-20 years"
    return "20+ years"


def categorize_holder_age(age: float) -> str:
    """Assign holder age bucket (7 buckets for Reg E)."""
    if pd.isna(age):
        return "Unknown"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    if age < 75:
        return "65-74"
    return "75+"


# -- Reg E code normalization -------------------------------------------------
# Some institutions use truncated or abbreviated Reg E codes that change
# mid-year. This mapping normalizes known variants to canonical names so
# all months produce consistent analysis. (See issue #63 / client 1615.)

REG_E_CODE_CORRECTIONS: dict[str, str] = {
    "Opt In ATM": "Opt In ATM/POS OD Limit",
    "Opt Out Re": "Opt Out Reply",
    "Mandatory": "Mandatory Opt Out",
}


def normalize_reg_e_codes(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Normalize known truncated Reg E code values in-place."""
    if col in df.columns:
        df[col] = df[col].replace(REG_E_CODE_CORRECTIONS)
    return df


# -- Core Reg E calculation ---------------------------------------------------


def rege(df: pd.DataFrame, col: str, opt_list: list[str]) -> tuple[int, int, float]:
    """Core Reg E opt-in calculation.

    Returns (total, opted_in, rate).
    """
    t = len(df)
    if t == 0:
        return 0, 0, 0.0
    oi = len(df[df[col].isin(opt_list)])
    return t, oi, oi / t


def _parse_reg_e_date(col_name: str) -> pd.Timestamp:
    """Extract date from a Reg E column name like 'Reg E Code Jan26'."""
    # Strip "Reg E Code" prefix, then parse remaining date part
    suffix = col_name.replace("Reg E Code", "").strip()
    # Handle "Jan26" (no space) and "Jan 26" (with space)
    suffix = suffix.replace(" ", "")
    try:
        return pd.to_datetime(suffix, format="%b%y")
    except Exception:
        return pd.NaT


def detect_reg_e_column(df: pd.DataFrame) -> str | None:
    """Auto-detect the latest 'Reg E Code ...' column from DataFrame columns.

    Sorts chronologically (not alphabetically) so Jan26 beats Dec25.
    """
    reg_e_cols = [c for c in df.columns if "Reg E Code" in c]
    if not reg_e_cols:
        return None
    # Sort chronologically; columns that fail to parse go first (NaT)
    reg_e_cols.sort(key=_parse_reg_e_date)
    logger.debug(
        "Reg E columns found: {cols}, selected: {sel}", cols=reg_e_cols, sel=reg_e_cols[-1]
    )
    return reg_e_cols[-1]


def reg_e_base(ctx: PipelineContext) -> tuple[pd.DataFrame, pd.DataFrame | None, str, list[str]]:
    """Compute Reg E eligible base from context.

    Returns (base_df, base_l12m_df, reg_e_col, opt_list).
    Raises ValueError if prerequisites are missing.
    """
    # Get opt-in codes
    opt_list = ctx.client.reg_e_opt_in
    if not opt_list:
        raise ValueError("No Reg E opt-in codes configured (client.reg_e_opt_in)")

    # Get or detect Reg E column
    reg_e_col = ctx.client.reg_e_column
    if not reg_e_col and ctx.data is not None:
        reg_e_col = detect_reg_e_column(ctx.data)
    if not reg_e_col:
        raise ValueError("No Reg E column found in data")

    # Base = eligible personal with debit
    ep = ctx.subsets.eligible_personal
    if ep is None or ep.empty:
        raise ValueError("No eligible personal accounts")
    dc_col = detect_debit_col(ep)
    if dc_col is None:
        raise ValueError("No debit card column found in eligible personal data")

    base = ep[debit_mask(ep, dc_col)].copy()
    if base.empty:
        raise ValueError("No personal accounts with debit cards")

    # Normalize the Reg E column values (strip whitespace + fix truncated codes)
    if reg_e_col in base.columns:
        base[reg_e_col] = base[reg_e_col].astype(str).str.strip()
        normalize_reg_e_codes(base, reg_e_col)
    else:
        raise ValueError(f"Reg E column '{reg_e_col}' not in data")

    # L12M base
    base_l12m = None
    if ctx.start_date and ctx.end_date and "Date Opened" in base.columns:
        base_l12m = filter_l12m(base, ctx.start_date, ctx.end_date)

    logger.debug(
        "Reg E base: {n:,} accounts, col={col}, {nl12m} L12M",
        n=len(base),
        col=reg_e_col,
        nl12m=len(base_l12m) if base_l12m is not None else 0,
    )
    return base, base_l12m, reg_e_col, opt_list


def total_row(df: pd.DataFrame, label_col: str, label: str = "TOTAL") -> pd.DataFrame:
    """Append a TOTAL row, recalculating Rate columns from Opted In / Total."""
    if df.empty:
        return df
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    totals: dict = {label_col: label}
    for c in num_cols:
        if "Rate" in c or "%" in c:
            oi = df["Opted In"].sum() if "Opted In" in df.columns else 0
            ta = df["Total Accounts"].sum() if "Total Accounts" in df.columns else 0
            totals[c] = oi / ta if ta > 0 else 0
        else:
            totals[c] = df[c].sum()
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
