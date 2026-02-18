"""Required columns, aliases, and column resolution for ICS data files."""

import logging
import re

import pandas as pd

from ics_toolkit.exceptions import DataError

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "ICS Account",
    "Stat Code",
    "Debit?",
    "Business?",
    "Date Opened",
    "Prod Code",
    "Branch",
    "Source",
    "Curr Bal",
}

OPTIONAL_COLUMNS = {
    "Date Closed",
    "Avg Bal",
}

COLUMN_ALIASES: dict[str, str] = {
    "ICS Accounts": "ICS Account",
    "Ics Account": "ICS Account",
    "ICS_Account": "ICS Account",
    "IcsAccount": "ICS Account",
    "StatCode": "Stat Code",
    "Stat_Code": "Stat Code",
    "Status Code": "Stat Code",
    "ProdCode": "Prod Code",
    "Prod_Code": "Prod Code",
    "Product Code": "Prod Code",
    "DateOpened": "Date Opened",
    "Date_Opened": "Date Opened",
    "Open Date": "Date Opened",
    "DateClosed": "Date Closed",
    "Date_Closed": "Date Closed",
    "Close Date": "Date Closed",
    "CurrBal": "Curr Bal",
    "Curr_Bal": "Curr Bal",
    "Current Balance": "Curr Bal",
    "AvgBal": "Avg Bal",
    "Avg_Bal": "Avg Bal",
    "Average Balance": "Avg Bal",
    "AvgColBal": "Avg Bal",
    "Business": "Business?",
    "BusinessFlag": "Business?",
    "Business Flag": "Business?",
    "Debit": "Debit?",
    "DebitCard": "Debit?",
    "Debit Card": "Debit?",
}

# Pattern for L12M monthly columns: e.g., "Feb24 Swipes", "Mar25 Spend"
L12M_SWIPE_PATTERN = re.compile(r"^([A-Z][a-z]{2}\d{2})\s+Swipes$")
L12M_SPEND_PATTERN = re.compile(r"^([A-Z][a-z]{2}\d{2})\s+Spend$")


def resolve_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns using COLUMN_ALIASES to canonical names.

    Returns a new DataFrame with resolved column names.
    """
    rename_map = {}
    for col in df.columns:
        col_stripped = str(col).strip()
        if col_stripped in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[col_stripped]
        elif col_stripped != col:
            rename_map[col] = col_stripped

    if rename_map:
        logger.info("Resolved column aliases: %s", rename_map)
        df = df.rename(columns=rename_map)

    return df


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Check that all required columns are present.

    Returns list of missing column names. Raises DataError if critical columns missing.
    """
    present = set(df.columns)
    missing = REQUIRED_COLUMNS - present

    if missing:
        raise DataError(
            f"Missing required columns: {sorted(missing)}\n"
            f"Available columns: {sorted(present)}\n"
            "Check your data file or column_map.py aliases."
        )

    optional_missing = OPTIONAL_COLUMNS - present
    if optional_missing:
        logger.info("Optional columns not found (ok): %s", sorted(optional_missing))

    return sorted(missing)


def discover_l12m_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    """Discover L12M monthly Swipes and Spend columns from DataFrame headers.

    Returns:
        (month_tags, swipe_cols, spend_cols) where month_tags are like ['Feb24', 'Mar24', ...]
    """
    month_tags = []
    swipe_cols = []
    spend_cols = []

    swipe_map: dict[str, str] = {}
    spend_map: dict[str, str] = {}

    for col in df.columns:
        m = L12M_SWIPE_PATTERN.match(str(col))
        if m:
            swipe_map[m.group(1)] = col
        m = L12M_SPEND_PATTERN.match(str(col))
        if m:
            spend_map[m.group(1)] = col

    # Find tags present in both swipes and spend
    common_tags = sorted(set(swipe_map.keys()) & set(spend_map.keys()))

    if not common_tags:
        logger.warning("No L12M monthly columns found (expected '{MonthTag} Swipes/Spend')")
        return [], [], []

    # Sort chronologically by converting tag to date
    from datetime import datetime

    def tag_to_date(tag: str) -> datetime:
        return datetime.strptime(tag, "%b%y")

    common_tags.sort(key=tag_to_date)

    for tag in common_tags:
        month_tags.append(tag)
        swipe_cols.append(swipe_map[tag])
        spend_cols.append(spend_map[tag])

    logger.info(
        "Discovered %d L12M months: %s ... %s",
        len(month_tags),
        month_tags[0],
        month_tags[-1],
    )

    return month_tags, swipe_cols, spend_cols
