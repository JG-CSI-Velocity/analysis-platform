"""Layer 1: Entity normalization for referral data."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ics_toolkit.settings import ReferralSettings

SUFFIXES = frozenset({"JR", "SR", "II", "III", "IV", "V"})


def normalize_entities(df: pd.DataFrame, settings: ReferralSettings) -> pd.DataFrame:
    """Standardize entity names. Adds canonical columns without overwriting originals.

    Added columns: Referrer, New Account, Staff, Branch Code, Branch Label,
    Referrer Surname, Account Surname
    """
    df = df.copy()
    df["Referrer"] = _normalize_name(df["Referrer Name"], settings.name_aliases, "UNKNOWN")
    df["New Account"] = _normalize_name(df["Account Holder"], settings.name_aliases, "UNKNOWN")
    df["Staff"] = _normalize_name(df["Purchase Manager"], settings.name_aliases, "UNASSIGNED")
    df["Branch Code"] = df["Branch"].fillna("UNKNOWN").astype(str).str.strip()

    if settings.branch_mapping:
        mapped = df["Branch Code"].map(settings.branch_mapping)
        df["Branch Label"] = mapped.fillna(df["Branch Code"])
    else:
        df["Branch Label"] = df["Branch Code"]

    df["Referrer Surname"] = _extract_surname(df["Referrer"])
    df["Account Surname"] = _extract_surname(df["New Account"])
    return df


def _normalize_name(
    series: pd.Series,
    aliases: dict[str, str],
    null_sentinel: str,
) -> pd.Series:
    """Strip, uppercase, collapse whitespace, apply alias table."""
    normalized = series.fillna(null_sentinel).astype(str).str.strip().str.upper()
    normalized = normalized.apply(lambda n: re.sub(r"\s+", " ", n))
    normalized = normalized.replace("", null_sentinel)
    if aliases:
        upper_aliases = {k.upper(): v.upper() for k, v in aliases.items()}
        normalized = normalized.map(lambda n: upper_aliases.get(n, n))
    return normalized


def _extract_surname(series: pd.Series) -> pd.Series:
    """Extract surname from full name, skipping common suffixes."""

    def _surname(name: str) -> str:
        parts = name.split()
        if len(parts) <= 1:
            return name
        if parts[-1] in SUFFIXES and len(parts) > 2:
            return parts[-2]
        return parts[-1]

    return series.apply(_surname)
