"""Unified data loading for ODDD, ODD, and transaction files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_oddd(path: Path, format_data: bool = True) -> pd.DataFrame:
    """Load an ODDD file, optionally running the formatting pipeline.

    Args:
        path: Path to the ODDD Excel or CSV file.
        format_data: If True, apply the 7-step formatting pipeline.

    Returns:
        DataFrame with account-level data.
    """
    df = _read_file(path)
    if format_data:
        from shared.format_odd import format_odd

        df = format_odd(df)
    return df


def load_tran(path: Path) -> pd.DataFrame:
    """Load a transaction file (tab-delimited CSV).

    Args:
        path: Path to the transaction CSV/TXT file.

    Returns:
        DataFrame with transaction records.
    """
    df = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    df.columns = df.columns.str.strip()

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    return df


def load_odd(path: Path) -> pd.DataFrame:
    """Load an ODD file for transaction analysis pairing.

    Args:
        path: Path to the ODD Excel file.

    Returns:
        DataFrame with account-level demographics.
    """
    return _read_file(path)


def _read_file(path: Path) -> pd.DataFrame:
    """Read a file, auto-detecting format from extension."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    elif suffix == ".csv":
        return pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
