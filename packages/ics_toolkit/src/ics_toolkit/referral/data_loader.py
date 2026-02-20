"""Load and validate referral data files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ics_toolkit.exceptions import DataError
from ics_toolkit.referral.column_map import COLUMN_ALIASES, REQUIRED_COLUMNS

if TYPE_CHECKING:
    from ics_toolkit.settings import ReferralSettings

logger = logging.getLogger(__name__)


def load_referral_data(settings: ReferralSettings) -> pd.DataFrame:
    """Load and validate a referral data file.

    Steps:
    1. Read file (detect format by suffix)
    2. Resolve column aliases
    3. Validate required columns
    4. Drop rows where MRDB Account Hash is null
    5. Parse Issue Date as datetime
    6. Log warnings for data quality issues
    """
    if settings.data_file is None:
        raise DataError("No referral data file specified.")

    df = _read_file(settings.data_file, settings.header_row)
    df = _resolve_aliases(df)
    _validate_columns(df, settings.data_file)
    df = _validate_primary_key(df)
    df = _parse_dates(df)
    _warn_data_quality(df)
    logger.info("Loaded %d referral records from %s", len(df), settings.data_file.name)
    return df


def _read_file(path: Path, header_row: int = 0) -> pd.DataFrame:
    """Read file, choosing engine by suffix."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(path, header=header_row)
        elif suffix == ".xls":
            return pd.read_excel(path, header=header_row, engine="xlrd")
        elif suffix == ".xlsx":
            return pd.read_excel(path, header=header_row, engine="openpyxl")
        else:
            raise DataError(f"Unsupported file type: {suffix}")
    except ImportError as e:
        if "xlrd" in str(e):
            raise DataError(
                "The 'xlrd' package is required to read .xls files. "
                "Install it with: pip install xlrd"
            ) from e
        raise
    except Exception as e:
        raise DataError(f"Failed to read {path.name}: {e}") from e


def _resolve_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Map alternative column names to canonical names."""
    rename_map: dict[str, str] = {}
    for col in df.columns:
        lower = col.strip().lower().replace("-", "_")
        if col not in REQUIRED_COLUMNS and lower in COLUMN_ALIASES:
            canonical = COLUMN_ALIASES[lower]
            if canonical not in df.columns:
                rename_map[col] = canonical
    if rename_map:
        logger.debug("Column aliases resolved: %s", rename_map)
        df = df.rename(columns=rename_map)
    return df


def _validate_columns(df: pd.DataFrame, path: Path) -> None:
    """Ensure all required columns are present."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        available = ", ".join(sorted(df.columns))
        raise DataError(
            f"Missing required columns in {path.name}: {missing}\nAvailable columns: {available}"
        )


def _validate_primary_key(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where MRDB Account Hash is null."""
    null_pk = df["MRDB Account Hash"].isna()
    if null_pk.all():
        raise DataError("All rows have null MRDB Account Hash -- file has no usable data.")
    if null_pk.any():
        count = null_pk.sum()
        logger.warning("Dropped %d rows with null MRDB Account Hash", count)
        df = df[~null_pk].copy()
    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse Issue Date as datetime."""
    df = df.copy()
    df["Issue Date"] = pd.to_datetime(df["Issue Date"], errors="coerce")
    nat_count = df["Issue Date"].isna().sum()
    if nat_count > 0:
        logger.warning(
            "%d rows have unparseable Issue Date (will be excluded from temporal analysis)",
            nat_count,
        )
    return df


def _warn_data_quality(df: pd.DataFrame) -> None:
    """Log warnings for common data quality issues."""
    # Null Cert ID
    null_cert = df["Cert ID"].isna().sum()
    if null_cert > 0:
        logger.warning("%d rows have null Cert ID", null_cert)

    # Future dates
    now = pd.Timestamp.now()
    future = df["Issue Date"].dropna() > now
    if future.any():
        logger.warning("%d rows have future Issue Date", future.sum())

    # Duplicate MRDB + Cert ID pairs
    dups = df.duplicated(subset=["MRDB Account Hash", "Cert ID"], keep=False)
    if dups.any():
        logger.warning(
            "%d rows have duplicate MRDB Account Hash + Cert ID pairs",
            dups.sum(),
        )
