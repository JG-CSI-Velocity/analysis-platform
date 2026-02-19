"""Shared utilities for ODD file parsing and month resolution."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# Month folder patterns:
#   "February, 2026" (GMiller/JBerkowitz style)
#   "2026.02" (YYYY.MM style)
_MONTH_NAME_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|"
    r"October|November|December),?\s*(\d{4})$",
    re.IGNORECASE,
)
_MONTH_NUMERIC_RE = re.compile(r"^(\d{4})\.(\d{2})$")

# ODDD zip pattern: ####_ODDD.zip, ####-ODDD.zip, #### ODDD.zip, ####_ODD.zip
_ODDD_ZIP_RE = re.compile(r"^(\d+)[_\-\s]+OD{2,3}\.zip$", re.IGNORECASE)


def parse_odd_filename(filename: str) -> dict[str, str] | None:
    """Parse an ODD filename into its components.

    Expected: ClientID-year-month-ClientName-ODD.xlsx
    Example:  1453-2026-01-Connex CU-ODD.xlsx

    Returns dict with keys: client_id, year, month, client_name, filename.
    """
    if not filename.lower().endswith(".xlsx"):
        return None

    stem = Path(filename).stem
    parts = stem.split("-")

    if len(parts) < 5:
        return None
    if parts[-1].upper() != "ODD":
        return None

    client_id = parts[0].strip()
    year = parts[1].strip()
    month = parts[2].strip()
    client_name = "-".join(parts[3:-1]).strip()

    if not year.isdigit() or not month.isdigit():
        return None

    return {
        "client_id": client_id,
        "year": year,
        "month": month.zfill(2),
        "client_name": client_name,
        "filename": filename,
    }


def parse_month_folder(folder_name: str) -> tuple[str, str] | None:
    """Parse 'February, 2026' or '2026.02' -> ('2026', '02').

    Returns (year, month_zero_padded) or None if not a recognized format.
    """
    name = folder_name.strip()

    m = _MONTH_NUMERIC_RE.match(name)
    if m:
        return m.group(1), m.group(2)

    m = _MONTH_NAME_RE.match(name)
    if not m:
        return None
    month_name, year = m.group(1), m.group(2)
    try:
        month_num = datetime.strptime(month_name, "%B").month
        return year, f"{month_num:02d}"
    except ValueError:
        return None


def parse_oddd_zip(zip_name: str) -> str | None:
    """Parse '1453_ODDD.zip' -> '1453' (client_id)."""
    m = _ODDD_ZIP_RE.match(zip_name)
    return m.group(1) if m else None


def current_month() -> str:
    """Return current month as 'YYYY.MM' (e.g., '2026.02')."""
    return datetime.now().strftime("%Y.%m")


def resolve_target_month(month: str | None = None) -> tuple[str, str, str]:
    """Resolve a target month string into components.

    Parameters
    ----------
    month : str or None
        'YYYY.MM' format. Defaults to current month.

    Returns
    -------
    tuple of (full, year, mm)
        full='2026.02', year='2026', mm='02'

    Raises
    ------
    ValueError
        If month string is not in 'YYYY.MM' format.
    """
    if month is None:
        month = current_month()
    if not _MONTH_NUMERIC_RE.match(month):
        msg = f"Month must be 'YYYY.MM' format, got: {month!r}"
        raise ValueError(msg)
    year, mm = month.split(".")
    return month, year, mm
