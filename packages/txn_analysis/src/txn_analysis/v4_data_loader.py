"""Data loading module for V4 Transaction Analysis.

Loads transaction CSVs and ODD Excel files, merges them, and returns
a context dict ready for downstream storyline analyses.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from dateutil.relativedelta import relativedelta

from txn_analysis.v4_merchant_rules import standardize_merchant_name

# ---------------------------------------------------------------------------
# Column names assigned to raw transaction files (tab-delimited, no header)
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


# =========================================================================
# Config
# =========================================================================

def load_config(config_path: str) -> dict:
    """Load YAML config file and return as a plain dict."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    print(f"[config] Loaded config from {path.name}")
    print(f"         Client: {config.get('client_id', '?')} - {config.get('client_name', '?')}")
    return config


# =========================================================================
# Transaction loading
# =========================================================================

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


def load_transactions(config: dict) -> pd.DataFrame:
    """Load all transaction files, keep only the most recent N months.

    Steps
    -----
    1. Walk year-folders under ``config['transaction_dir']`` and collect files
       matching ``config['file_extension']``.
    2. Parse embedded dates from filenames; keep the most recent
       ``config['recent_months']`` files.
    3. Concatenate into a single DataFrame.
    4. Convert *amount* to float, flip sign if median is negative.
    5. Parse *transaction_date* as datetime, derive *year_month* Period.
    """
    txn_dir = Path(config["transaction_dir"])
    ext = config.get("file_extension", "csv")
    recent_months = config.get("recent_months", 12)

    if not txn_dir.exists():
        raise FileNotFoundError(f"Transaction directory not found: {txn_dir}")

    # -- discover files across year-folders -----------------------------------
    year_folders = [p for p in txn_dir.iterdir() if _is_year_folder(p)]
    all_files: list[Path] = []
    for yf in year_folders:
        all_files.extend(yf.glob(f"*.{ext}"))

    # also pick up files sitting directly in the transaction dir
    all_files.extend(txn_dir.glob(f"*.{ext}"))
    # deduplicate (resolve to absolute) while preserving order
    seen: set[Path] = set()
    unique_files: list[Path] = []
    for f in all_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)
    all_files = unique_files

    print(f"\n[transactions] Directory : {txn_dir}")
    print(f"[transactions] Year folders found: "
          f"{sorted(p.name for p in year_folders) if year_folders else 'none'}")
    print(f"[transactions] Total files discovered: {len(all_files)}")

    # -- parse dates and select most recent N months --------------------------
    dated: list[tuple[Path, datetime]] = []
    unparsed: list[Path] = []
    for f in all_files:
        fd = _parse_file_date(f)
        if fd is None:
            unparsed.append(f)
        else:
            dated.append((f, fd))

    dated.sort(key=lambda x: x[1], reverse=True)
    selected = dated[:recent_months]

    if unparsed:
        print(f"[transactions] WARNING: {len(unparsed)} file(s) with unparseable dates:")
        for u in unparsed:
            print(f"               {u.name}")

    if not selected:
        raise RuntimeError("No transaction files matched after date parsing.")

    earliest = selected[-1][1]
    latest = selected[0][1]
    print(f"[transactions] Selected {len(selected)} most recent files "
          f"({earliest:%Y-%m-%d} to {latest:%Y-%m-%d})")

    # -- load and combine -----------------------------------------------------
    frames: list[pd.DataFrame] = []
    for filepath, file_date in selected:
        df = _load_single_transaction_file(filepath)
        frames.append(df)
        print(f"  Loaded: {filepath.name} ({len(df):,} rows)")

    combined = pd.concat(frames, ignore_index=True)

    # -- type conversions -----------------------------------------------------
    combined["amount"] = pd.to_numeric(combined["amount"], errors="coerce").fillna(0.0)
    if combined["amount"].median() < 0:
        combined["amount"] = combined["amount"].abs()

    combined["transaction_date"] = pd.to_datetime(
        combined["transaction_date"], errors="coerce"
    )
    combined["year_month"] = combined["transaction_date"].dt.to_period("M")

    # -- merchant consolidation -----------------------------------------------
    print("[transactions] Applying merchant name consolidation...")
    combined["merchant_consolidated"] = combined["merchant_name"].apply(
        standardize_merchant_name
    )
    original_unique = combined["merchant_name"].nunique()
    consolidated_unique = combined["merchant_consolidated"].nunique()
    reduction = original_unique - consolidated_unique
    reduction_pct = (reduction / original_unique * 100) if original_unique else 0.0
    print(f"  Original merchants : {original_unique:,}")
    print(f"  After consolidation: {consolidated_unique:,} "
          f"(-{reduction:,}, {reduction_pct:.1f}% reduction)")

    # -- summary --------------------------------------------------------------
    print(f"\n[transactions] Combined dataset:")
    print(f"  Rows        : {len(combined):,}")
    print(f"  Columns     : {combined.shape[1]}")
    print(f"  Date range  : {combined['transaction_date'].min()} "
          f"to {combined['transaction_date'].max()}")
    print(f"  Accounts    : {combined['primary_account_num'].nunique():,}")
    print(f"  Total spend : ${combined['amount'].sum():,.2f}")
    print(f"  Memory      : {combined.memory_usage(deep=True).sum() / 1024 ** 2:.1f} MB")

    return combined


# =========================================================================
# ODD loading
# =========================================================================

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
    # catch exactly the upper boundary of the last tier
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


def load_odd(config: dict) -> pd.DataFrame:
    """Load the ODD (account-level) Excel file and derive analytical columns.

    Derived columns
    ---------------
    * ``generation`` -- generational cohort from Account Holder Age
    * ``tenure_years`` -- account tenure from Account Age or Date Opened
    * ``balance_tier`` -- tier based on Avg Bal
    """
    odd_path = Path(config["odd_file"])
    if not odd_path.exists():
        raise FileNotFoundError(f"ODD file not found: {odd_path}")

    print(f"\n[odd] Loading ODD file: {odd_path.name}")
    odd_df = pd.read_excel(odd_path, engine="openpyxl")
    print(f"[odd] Loaded: {len(odd_df):,} rows, {len(odd_df.columns)} columns")

    # strip whitespace from column names
    odd_df.columns = odd_df.columns.str.strip()

    # -- parse date columns ---------------------------------------------------
    if "DOB" in odd_df.columns:
        odd_df["DOB"] = pd.to_datetime(odd_df["DOB"], errors="coerce")

    if "Date Opened" in odd_df.columns:
        odd_df["Date Opened"] = pd.to_datetime(odd_df["Date Opened"], errors="coerce")

    if "Date Closed" in odd_df.columns:
        odd_df["Date Closed"] = pd.to_datetime(odd_df["Date Closed"], errors="coerce")

    # -- derived: generation --------------------------------------------------
    if "Account Holder Age" in odd_df.columns:
        odd_df["generation"] = odd_df["Account Holder Age"].apply(_assign_generation)
        gen_dist = odd_df["generation"].value_counts()
        print(f"[odd] Generation distribution:")
        for gen, count in gen_dist.items():
            print(f"       {gen}: {count:,}")
    else:
        odd_df["generation"] = None

    # -- derived: tenure_years ------------------------------------------------
    if "Account Age" in odd_df.columns:
        numeric_age = pd.to_numeric(odd_df["Account Age"], errors="coerce")
        if numeric_age.notna().any():
            odd_df["tenure_years"] = numeric_age
        elif "Date Opened" in odd_df.columns:
            today = pd.Timestamp.now()
            odd_df["tenure_years"] = (
                (today - odd_df["Date Opened"]).dt.days / 365.25
            ).round(1)
        else:
            odd_df["tenure_years"] = None
    elif "Date Opened" in odd_df.columns:
        today = pd.Timestamp.now()
        odd_df["tenure_years"] = (
            (today - odd_df["Date Opened"]).dt.days / 365.25
        ).round(1)
    else:
        odd_df["tenure_years"] = None

    # -- derived: balance_tier ------------------------------------------------
    if "Avg Bal" in odd_df.columns:
        odd_df["balance_tier"] = odd_df["Avg Bal"].apply(_assign_balance_tier)
        tier_dist = odd_df["balance_tier"].value_counts()
        print(f"[odd] Balance tier distribution:")
        for tier, count in tier_dist.items():
            print(f"       {tier}: {count:,}")
    else:
        odd_df["balance_tier"] = None

    # -- auto-detect time series columns --------------------------------------
    ts_cols = _detect_timeseries_columns(odd_df.columns)
    print(f"[odd] Time series detected:")
    for series, cols in ts_cols.items():
        print(f"       {series}: {len(cols)} months")

    # -- summary --------------------------------------------------------------
    print(f"\n[odd] Summary:")
    print(f"  Total accounts  : {len(odd_df):,}")
    if "Business?" in odd_df.columns:
        biz_counts = odd_df["Business?"].value_counts()
        for flag, count in biz_counts.items():
            print(f"  Business={flag}  : {count:,}")
    if "Debit?" in odd_df.columns:
        debit_counts = odd_df["Debit?"].value_counts()
        for flag, count in debit_counts.items():
            print(f"  Debit={flag}    : {count:,}")
    print(f"  Memory          : {odd_df.memory_usage(deep=True).sum() / 1024 ** 2:.1f} MB")

    return odd_df


# =========================================================================
# Merge
# =========================================================================

# ODD columns to merge into combined_df (keep it slim to avoid memory blow-up).
# Storylines that need the full ODD (S6 Risk, S7 Campaigns) read ctx["odd_df"].
_MERGE_COLS = [
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


def merge_data(
    txn_df: pd.DataFrame, odd_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Left-join transaction data with a slim subset of ODD columns.

    Only essential ODD columns are merged to keep memory manageable.
    Storylines needing full ODD data should read ``ctx["odd_df"]`` directly.

    Returns
    -------
    combined_df : merged DataFrame (transactions + slim ODD columns)
    business_df : subset where Business? == 'Yes'
    personal_df : subset where Business? == 'No'
    """
    print("\n[merge] Merging transaction data with ODD...")

    # Select only the columns that exist in this ODD file
    merge_cols = [c for c in _MERGE_COLS if c in odd_df.columns]
    odd_slim = odd_df[merge_cols].copy()
    print(f"[merge] Merging {len(merge_cols)} ODD columns "
          f"(of {len(odd_df.columns)} total) to keep memory low")

    combined_df = txn_df.merge(
        odd_slim,
        left_on="primary_account_num",
        right_on="Acct Number",
        how="left",
    )

    matched = combined_df["Acct Number"].notna().sum()
    unmatched = combined_df["Acct Number"].isna().sum()
    match_rate = (matched / len(combined_df) * 100) if len(combined_df) else 0.0
    print(f"[merge] Results:")
    print(f"  Total transactions : {len(combined_df):,}")
    print(f"  Matched to ODD     : {matched:,} ({match_rate:.1f}%)")
    print(f"  Unmatched          : {unmatched:,}")

    # split by business flag (guard for missing column)
    if "Business?" in combined_df.columns:
        business_df = combined_df[combined_df["Business?"] == "Yes"].copy()
        personal_df = combined_df[combined_df["Business?"] == "No"].copy()
    else:
        business_df = pd.DataFrame(columns=combined_df.columns)
        personal_df = combined_df.copy()

    print(f"\n[merge] Account type split:")
    print(f"  Business transactions : {len(business_df):,} "
          f"(${business_df['amount'].sum():,.2f})")
    print(f"  Personal transactions : {len(personal_df):,} "
          f"(${personal_df['amount'].sum():,.2f})")

    return combined_df, business_df, personal_df


# =========================================================================
# Main entry point
# =========================================================================

def load_all(config: dict) -> dict:
    """Load all data sources and return a context dict for downstream analyses.

    Keys in returned dict
    ---------------------
    config       : the raw config dict
    txn_df       : raw transaction DataFrame (before merge)
    odd_df       : raw ODD DataFrame (account-level, for standalone analyses)
    combined_df  : merged transaction + ODD data
    business_df  : business-account transactions only
    personal_df  : personal-account transactions only
    """
    print("=" * 80)
    print("  V4 TRANSACTION ANALYSIS - DATA LOADING")
    print("=" * 80)

    txn_df = load_transactions(config)
    odd_df = load_odd(config)
    combined_df, business_df, personal_df = merge_data(txn_df, odd_df)

    print("\n" + "=" * 80)
    print("  DATA LOADING COMPLETE")
    print("=" * 80)
    print(f"  Transaction rows  : {len(txn_df):,}")
    print(f"  ODD accounts      : {len(odd_df):,}")
    print(f"  Combined rows     : {len(combined_df):,}")
    print(f"  Business rows     : {len(business_df):,}")
    print(f"  Personal rows     : {len(personal_df):,}")
    print(f"  Date range        : {combined_df['transaction_date'].min()} "
          f"to {combined_df['transaction_date'].max()}")
    print(f"  Unique accounts   : {combined_df['primary_account_num'].nunique():,}")
    print(f"  Unique merchants  : {combined_df['merchant_consolidated'].nunique():,}")
    print("=" * 80)

    return {
        "config": config,
        "txn_df": txn_df,
        "odd_df": odd_df,
        "combined_df": combined_df,
        "business_df": business_df,
        "personal_df": personal_df,
    }
