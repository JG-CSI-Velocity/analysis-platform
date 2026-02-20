"""Data loading, validation, and preparation pipeline.

Handles three data sources:
1. Single CSV/Excel file (data_file) -- M1-M10 analyses
2. Transaction directory with year-folder layout (transaction_dir) -- V4 pipeline
3. ODD (account-level) Excel file (odd_file) -- demographics, balance tiers
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from txn_analysis.column_map import resolve_columns
from txn_analysis.exceptions import DataLoadError
from txn_analysis.merchant_rules import standardize_merchant_name
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transaction directory constants (tab-delimited files with no header)
# ---------------------------------------------------------------------------

TRANSACTION_COLUMNS = [
    "transaction_date",
    "primary_account_num",
    "transaction_type",
    "amount",
    "mcc_code",
    "merchant_name",
    "terminal_location_1",
    "terminal_location_2",
    "terminal_id",
    "merchant_id",
    "institution",
    "card_present",
    "transaction_code",
]

# ---------------------------------------------------------------------------
# ODD time-series regex patterns (MmmYY prefix, e.g. "Jan25 Spend")
# ---------------------------------------------------------------------------

_MONTH_PREFIX = r"[A-Z][a-z]{2}\d{2}"
ODD_TIMESERIES_PATTERNS: dict[str, re.Pattern[str]] = {
    "reg_e_code": re.compile(rf"^{_MONTH_PREFIX} Reg E Code$"),
    "reg_e_desc": re.compile(rf"^{_MONTH_PREFIX} Reg E Desc$"),
    "od_limit": re.compile(rf"^{_MONTH_PREFIX} OD Limit$"),
    "pin_dollar": re.compile(rf"^{_MONTH_PREFIX} PIN \$$"),
    "sig_dollar": re.compile(rf"^{_MONTH_PREFIX} Sig \$$"),
    "pin_count": re.compile(rf"^{_MONTH_PREFIX} PIN #$"),
    "sig_count": re.compile(rf"^{_MONTH_PREFIX} Sig #$"),
    "mtd": re.compile(rf"^{_MONTH_PREFIX} MTD$"),
    "spend": re.compile(rf"^{_MONTH_PREFIX} Spend$"),
    "swipes": re.compile(rf"^{_MONTH_PREFIX} Swipes$"),
    "mail": re.compile(rf"^{_MONTH_PREFIX} Mail$"),
    "resp": re.compile(rf"^{_MONTH_PREFIX} Resp$"),
    "segmentation": re.compile(rf"^{_MONTH_PREFIX} Segmentation$"),
}

# Generation boundaries based on Account Holder Age
GENERATION_BINS = [
    (12, 27, "Gen Z"),
    (28, 43, "Millennial"),
    (44, 59, "Gen X"),
    (60, 78, "Boomer"),
    (79, 200, "Silent"),
]

# Balance tier thresholds
BALANCE_TIERS = [
    (float("-inf"), 500, "Low"),
    (500, 2_000, "Medium"),
    (2_000, 10_000, "High"),
    (10_000, float("inf"), "Very High"),
]


def load_data(settings: Settings) -> pd.DataFrame:
    """Load, validate, and prepare the transaction dataset.

    Supports two input modes:
      - settings.data_file: single CSV/Excel file (M1-M10 path)
      - settings.transaction_dir: directory of tab-delimited files (V4 path)

    Steps:
      1. Read data from file or transaction directory
      2. Resolve column aliases -> canonical names
      3. Apply merchant consolidation -> merchant_consolidated column
      4. Derive year_month from transaction_date
      5. Normalize business_flag (default "No" if missing)
      6. Flag partial month

    Returns the cleaned DataFrame ready for analysis.
    """
    if settings.data_file:
        df = _read_file(settings.data_file)
        df = resolve_columns(df)
    elif settings.transaction_dir:
        df = _load_transaction_dir(settings)
    else:
        raise DataLoadError("No data_file or transaction_dir configured")
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


# ---------------------------------------------------------------------------
# Transaction directory loading (V4 tab-delimited files)
# ---------------------------------------------------------------------------


def _is_year_folder(path: Path) -> bool:
    """Return True if *path* is a directory whose name is a 4-digit year."""
    return path.is_dir() and path.name.isdigit() and len(path.name) == 4


def _parse_file_date(filepath: Path) -> datetime | None:
    """Extract the MMDDYYYY date embedded in filenames like ``1453-trans-01012025``."""
    match = re.search(r"trans-(\d{8})$", filepath.stem)
    if match:
        return datetime.strptime(match.group(1), "%m%d%Y")
    return None


def _load_single_transaction_file(filepath: Path) -> pd.DataFrame:
    """Read one tab-delimited transaction file, skip metadata row."""
    df = pd.read_csv(filepath, sep="\t", skiprows=1, header=None, low_memory=False)
    df.columns = TRANSACTION_COLUMNS[: len(df.columns)]
    df["source_file"] = filepath.name
    return df


def _load_transaction_dir(settings: Settings) -> pd.DataFrame:
    """Load all transaction files from a directory, keep most recent 12 months.

    Walks year-folders, parses embedded dates from filenames, selects the
    most recent files, and combines into a single DataFrame.
    """
    txn_dir = settings.transaction_dir
    ext = "csv"
    recent_months = 12

    year_folders = [p for p in txn_dir.iterdir() if _is_year_folder(p)]
    all_files: list[Path] = []
    for yf in year_folders:
        all_files.extend(yf.glob(f"*.{ext}"))
    all_files.extend(txn_dir.glob(f"*.{ext}"))

    # Deduplicate by resolved path
    seen: set[Path] = set()
    unique_files: list[Path] = []
    for f in all_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)
    all_files = unique_files

    logger.info("Transaction dir: %s (%d files found)", txn_dir, len(all_files))

    # Parse dates and select most recent N months
    dated: list[tuple[Path, datetime]] = []
    for f in all_files:
        fd = _parse_file_date(f)
        if fd is not None:
            dated.append((f, fd))

    dated.sort(key=lambda x: x[1], reverse=True)
    selected = dated[:recent_months]

    if not selected:
        raise DataLoadError(f"No transaction files matched in {txn_dir}")

    logger.info(
        "Selected %d files (%s to %s)",
        len(selected),
        selected[-1][1].strftime("%Y-%m-%d"),
        selected[0][1].strftime("%Y-%m-%d"),
    )

    frames: list[pd.DataFrame] = []
    for filepath, _file_date in selected:
        frames.append(_load_single_transaction_file(filepath))

    combined = pd.concat(frames, ignore_index=True)

    # Type conversions
    combined["amount"] = pd.to_numeric(combined["amount"], errors="coerce").fillna(0.0)
    if combined["amount"].median() < 0:
        combined["amount"] = combined["amount"].abs()
    combined["transaction_date"] = pd.to_datetime(combined["transaction_date"], errors="coerce")

    logger.info("Loaded %d rows from transaction directory", len(combined))
    return combined


# ---------------------------------------------------------------------------
# ODD (account-level demographics) loading
# ---------------------------------------------------------------------------


def _assign_generation(age) -> str | None:
    """Map numeric age to a generational cohort label."""
    try:
        age_val = float(age)
    except (TypeError, ValueError):
        return None
    for lo, hi, label in GENERATION_BINS:
        if lo <= age_val <= hi:
            return label
    return None


def _assign_balance_tier(avg_bal) -> str | None:
    """Map average balance to a tier label."""
    try:
        bal = float(avg_bal)
    except (TypeError, ValueError):
        return None
    for lo, hi, label in BALANCE_TIERS:
        if lo <= bal < hi:
            return label
    if bal >= BALANCE_TIERS[-1][1]:
        return BALANCE_TIERS[-1][2]
    return None


def _detect_timeseries_columns(columns: pd.Index) -> dict[str, list[str]]:
    """Auto-detect monthly time series columns in the ODD file.

    Returns a dict keyed by series name (e.g. ``"spend"``, ``"swipes"``)
    with values being lists of matching column names sorted chronologically.
    """
    result: dict[str, list[str]] = {}
    for series_name, pattern in ODD_TIMESERIES_PATTERNS.items():
        matches = [c for c in columns if pattern.match(c)]
        if matches:
            result[series_name] = sorted(matches)
    return result


def load_odd(settings: Settings) -> pd.DataFrame | None:
    """Load the ODD (account-level) Excel file and derive analytical columns.

    Returns None if settings.odd_file is not configured.

    Derived columns: generation, tenure_years, balance_tier.
    """
    if settings.odd_file is None:
        return None

    odd_path = settings.odd_file
    logger.info("Loading ODD file: %s", odd_path.name)
    odd_df = pd.read_excel(odd_path, engine="openpyxl")
    odd_df.columns = odd_df.columns.str.strip()

    # Parse date columns
    for col in ("DOB", "Date Opened", "Date Closed"):
        if col in odd_df.columns:
            odd_df[col] = pd.to_datetime(odd_df[col], errors="coerce")

    # Derived: generation
    if "Account Holder Age" in odd_df.columns:
        odd_df["generation"] = odd_df["Account Holder Age"].apply(_assign_generation)
    else:
        odd_df["generation"] = None

    # Derived: tenure_years
    if "Account Age" in odd_df.columns:
        numeric_age = pd.to_numeric(odd_df["Account Age"], errors="coerce")
        if numeric_age.notna().any():
            odd_df["tenure_years"] = numeric_age
        elif "Date Opened" in odd_df.columns:
            today = pd.Timestamp.now()
            odd_df["tenure_years"] = ((today - odd_df["Date Opened"]).dt.days / 365.25).round(1)
        else:
            odd_df["tenure_years"] = None
    elif "Date Opened" in odd_df.columns:
        today = pd.Timestamp.now()
        odd_df["tenure_years"] = ((today - odd_df["Date Opened"]).dt.days / 365.25).round(1)
    else:
        odd_df["tenure_years"] = None

    # Derived: balance_tier
    if "Avg Bal" in odd_df.columns:
        odd_df["balance_tier"] = odd_df["Avg Bal"].apply(_assign_balance_tier)
    else:
        odd_df["balance_tier"] = None

    ts_cols = _detect_timeseries_columns(odd_df.columns)
    logger.info(
        "ODD loaded: %d rows, %d time series detected",
        len(odd_df),
        len(ts_cols),
    )
    return odd_df


# ODD columns to merge into transaction data (keep slim for memory)
_ODD_MERGE_COLS = [
    "Acct Number",
    "generation",
    "balance_tier",
    "tenure_years",
    "Branch",
    "Business?",
    "Debit?",
    "Avg Bal",
    "Account Holder Age",
    "Date Opened",
    "Date Closed",
]


def merge_odd(
    df: pd.DataFrame, odd_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Left-join transaction data with a slim subset of ODD columns.

    Returns (combined_df, business_df, personal_df).
    """
    merge_cols = [c for c in _ODD_MERGE_COLS if c in odd_df.columns]
    odd_slim = odd_df[merge_cols].copy()

    combined = df.merge(
        odd_slim,
        left_on="primary_account_num",
        right_on="Acct Number",
        how="left",
    )

    matched = combined["Acct Number"].notna().sum()
    match_rate = (matched / len(combined) * 100) if len(combined) else 0.0
    logger.info("ODD merge: %d/%d rows matched (%.1f%%)", matched, len(combined), match_rate)

    if "Business?" in combined.columns:
        business_df = combined[combined["Business?"] == "Yes"].copy()
        personal_df = combined[combined["Business?"] == "No"].copy()
    else:
        business_df = pd.DataFrame(columns=combined.columns)
        personal_df = combined.copy()

    return combined, business_df, personal_df
