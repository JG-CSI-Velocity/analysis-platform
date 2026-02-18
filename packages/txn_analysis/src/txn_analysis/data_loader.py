"""Data loading, validation, and preparation pipeline."""

from __future__ import annotations

import calendar
import logging
from pathlib import Path

import pandas as pd

from txn_analysis.column_map import resolve_columns
from txn_analysis.exceptions import DataLoadError
from txn_analysis.merchant_rules import standardize_merchant_name
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)


def load_data(settings: Settings) -> pd.DataFrame:
    """Load, validate, and prepare the transaction dataset.

    Steps:
      1. Read CSV/Excel from settings.data_file
      2. Resolve column aliases -> canonical names
      3. Apply merchant consolidation -> merchant_consolidated column
      4. Derive year_month from transaction_date
      5. Normalize business_flag (default "No" if missing)

    Returns the cleaned DataFrame ready for analysis.
    """
    df = _read_file(settings.data_file)
    df = resolve_columns(df)
    df = _apply_merchant_consolidation(df)
    df = _derive_year_month(df)
    df = _normalize_business_flag(df)
    df = _flag_partial_month(df)
    _warn_negative_amounts(df)
    logger.info(
        "Loaded %d rows, %d unique merchants (%d consolidated)",
        len(df),
        df["merchant_name"].nunique(),
        df["merchant_consolidated"].nunique(),
    )
    return df


def _read_file(path: Path) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(path)
        return pd.read_excel(path)
    except Exception as e:
        raise DataLoadError(f"Failed to read {path}: {e}") from e


def _apply_merchant_consolidation(df: pd.DataFrame) -> pd.DataFrame:
    """Add merchant_consolidated column via standardize_merchant_name.

    Maps unique names first to avoid redundant per-row rule matching.
    """
    df = df.copy()
    unique_names = df["merchant_name"].unique()
    mapping = {name: standardize_merchant_name(name) for name in unique_names}
    df["merchant_consolidated"] = df["merchant_name"].map(mapping)
    return df


def _derive_year_month(df: pd.DataFrame) -> pd.DataFrame:
    """Add year_month column from transaction_date if not already present."""
    if "year_month" in df.columns:
        return df
    df = df.copy()
    dt = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["year_month"] = dt.dt.to_period("M").astype(str)
    return df


_BUSINESS_TRUTHY = frozenset({"yes", "y", "true", "1", "t"})
_BUSINESS_FALSY = frozenset({"no", "n", "false", "0", "f", ""})


def _normalize_business_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize business_flag to 'Yes'/'No'.

    Handles common variants: Y/yes/TRUE/1 -> 'Yes', N/no/FALSE/0 -> 'No'.
    NaN defaults to 'No'. Unmapped values logged and default to 'No'.
    """
    df = df.copy()
    if "business_flag" not in df.columns:
        df["business_flag"] = "No"
        return df

    raw = df["business_flag"].fillna("").astype(str).str.strip().str.lower()
    mapped = raw.map(
        lambda v: "Yes" if v in _BUSINESS_TRUTHY else ("No" if v in _BUSINESS_FALSY else None)
    )
    unmapped = mapped.isna()
    unmapped_count = unmapped.sum()
    if unmapped_count > 0:
        examples = raw[unmapped].unique()[:5].tolist()
        logger.warning(
            "business_flag: %d rows with unmapped values (defaulting to 'No'): %s",
            unmapped_count,
            examples,
        )
        mapped = mapped.fillna("No")
    df["business_flag"] = mapped
    return df


def _flag_partial_month(df: pd.DataFrame) -> pd.DataFrame:
    """Flag the last month in the dataset as partial if data coverage < 90%.

    Adds an 'is_partial_month' boolean column. Anchored to the dataset's own
    max date (not the system clock) for reproducibility.
    """
    df = df.copy()
    df["is_partial_month"] = False

    if "transaction_date" not in df.columns:
        return df

    dt = pd.to_datetime(df["transaction_date"], errors="coerce")
    max_date = dt.max()
    if pd.isna(max_date):
        return df

    days_in_month = calendar.monthrange(max_date.year, max_date.month)[1]
    coverage = max_date.day / days_in_month
    if coverage < 0.90:
        last_ym = max_date.strftime("%Y-%m")
        last_period = f"{max_date.year}-{max_date.month:02d}"
        if "year_month" in df.columns:
            mask = df["year_month"].astype(str).str.startswith(last_period) | (
                df["year_month"].astype(str) == last_ym
            )
            df.loc[mask, "is_partial_month"] = True
        logger.info(
            "Partial month detected: %s (day %d of %d, %.0f%% coverage)",
            last_ym,
            max_date.day,
            days_in_month,
            coverage * 100,
        )
    return df


def _warn_negative_amounts(df: pd.DataFrame) -> None:
    """Log a warning if negative amounts (refunds/reversals) are present."""
    if "amount" not in df.columns:
        return
    neg_mask = df["amount"] < 0
    neg_count = neg_mask.sum()
    if neg_count > 0:
        neg_total = df.loc[neg_mask, "amount"].sum()
        logger.warning(
            "Negative amounts detected: %d transactions totaling $%s "
            "(included as-is; may represent refunds/reversals)",
            neg_count,
            f"{neg_total:,.2f}",
        )
