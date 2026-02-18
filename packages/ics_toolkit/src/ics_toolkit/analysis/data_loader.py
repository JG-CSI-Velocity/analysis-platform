"""Data loading, cleaning, and validation for ICS analysis."""

import logging
from pathlib import Path

import pandas as pd

from ics_toolkit.analysis.column_map import (
    discover_l12m_columns,
    resolve_columns,
    validate_columns,
)
from ics_toolkit.exceptions import DataError
from ics_toolkit.settings import AnalysisSettings as Settings

logger = logging.getLogger(__name__)


def load_data(settings: Settings) -> pd.DataFrame:
    """Load, clean, and validate ICS data from file.

    Also discovers L12M columns and stores month tags on settings.
    """
    logger.info("Loading %s ...", settings.data_file.name)
    df = _read_file(settings.data_file)
    logger.info("Read %d rows, %d columns", len(df), len(df.columns))
    df = resolve_columns(df)
    validate_columns(df)
    df = _normalize_strings(df)
    df = _parse_dates(df)
    df = _coerce_numerics(df)

    # Discover L12M monthly columns
    month_tags, swipe_cols, spend_cols = discover_l12m_columns(df)
    settings.last_12_months = month_tags

    # Coerce L12M columns to numeric
    for col in swipe_cols + spend_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    logger.info(
        "Data loaded: %d rows, %d columns, %d L12M months",
        len(df),
        len(df.columns),
        len(month_tags),
    )

    return df


def _read_file(path: Path) -> pd.DataFrame:
    """Read CSV or Excel file into DataFrame."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(path)
        elif suffix in (".xlsx", ".xls"):
            return pd.read_excel(path, engine="openpyxl")
        else:
            raise DataError(f"Unsupported file type: {suffix}")
    except DataError:
        raise
    except Exception as e:
        raise DataError(f"Failed to read {path}: {e}") from e


def _normalize_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize string columns to consistent Yes/No/O/C values."""
    yes_map = {"YES": "Yes", "Y": "Yes", "TRUE": "Yes", "1": "Yes"}
    no_map = {"NO": "No", "N": "No", "FALSE": "No", "0": "No"}
    yn_map = {**yes_map, **no_map}

    for col in ("ICS Account", "Debit?", "Business?"):
        if col in df.columns:
            df[col] = (
                df[col].fillna("").astype(str).str.strip().str.upper().map(yn_map).fillna("No")
            )

    if "Stat Code" in df.columns:
        df["Stat Code"] = df["Stat Code"].fillna("").astype(str).str.strip().str.upper()

    if "Source" in df.columns:
        df["Source"] = df["Source"].fillna("Blank").astype(str).str.strip()
        df.loc[df["Source"] == "", "Source"] = "Blank"

    if "Prod Code" in df.columns:
        df["Prod Code"] = df["Prod Code"].fillna("Unknown").astype(str).str.strip()
        df.loc[df["Prod Code"].isin(["", "nan", "NaN", "None"]), "Prod Code"] = "Unknown"

    if "Branch" in df.columns:
        df["Branch"] = df["Branch"].fillna("Unknown").astype(str).str.strip()

    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date columns to datetime."""
    for col in ("Date Opened", "Date Closed"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def _coerce_numerics(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce balance columns to numeric."""
    for col in ("Curr Bal", "Avg Bal"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df
