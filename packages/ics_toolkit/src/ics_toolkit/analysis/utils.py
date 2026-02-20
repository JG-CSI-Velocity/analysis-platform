"""ICS-specific filter functions, enrichment, and helpers."""

import logging
from datetime import datetime

import pandas as pd

from ics_toolkit.settings import AnalysisSettings as Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filter functions -- return filtered DataFrames
# ---------------------------------------------------------------------------


def get_ics_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to ICS Account == 'Yes'."""
    return df[df["ICS Account"] == "Yes"].copy()


def get_ics_stat_o(df: pd.DataFrame, open_codes: list[str] | None = None) -> pd.DataFrame:
    """Filter to ICS Account == 'Yes' and open stat codes."""
    codes = open_codes or ["O"]
    return df[(df["ICS Account"] == "Yes") & (df["Stat Code"].isin(codes))].copy()


def get_ics_stat_o_debit(df: pd.DataFrame, open_codes: list[str] | None = None) -> pd.DataFrame:
    """Filter to ICS Account == 'Yes', open stat code, Debit? == 'Yes'."""
    codes = open_codes or ["O"]
    return df[
        (df["ICS Account"] == "Yes") & (df["Stat Code"].isin(codes)) & (df["Debit?"] == "Yes")
    ].copy()


def get_open_accounts(df: pd.DataFrame, open_codes: list[str] | None = None) -> pd.DataFrame:
    """Filter to accounts with open stat codes."""
    codes = open_codes or ["O"]
    return df[df["Stat Code"].isin(codes)].copy()


# ---------------------------------------------------------------------------
# Enrichment functions -- add computed columns
# ---------------------------------------------------------------------------


def add_l12m_activity(df: pd.DataFrame, last_12_months: list[str]) -> pd.DataFrame:
    """Add Total L12M Swipes, Total L12M Spend, and Active in L12M columns."""
    swipe_cols = [f"{tag} Swipes" for tag in last_12_months if f"{tag} Swipes" in df.columns]
    spend_cols = [f"{tag} Spend" for tag in last_12_months if f"{tag} Spend" in df.columns]

    if swipe_cols:
        df["Total L12M Swipes"] = df[swipe_cols].sum(axis=1).astype(int)
    else:
        df["Total L12M Swipes"] = 0

    if spend_cols:
        df["Total L12M Spend"] = df[spend_cols].sum(axis=1)
    else:
        df["Total L12M Spend"] = 0.0

    df["Active in L12M"] = df["Total L12M Swipes"] > 0

    return df


def add_opening_month(df: pd.DataFrame) -> pd.DataFrame:
    """Add Opening Month column (YYYY-MM format) from Date Opened."""
    if "Date Opened" in df.columns:
        df["Opening Month"] = df["Date Opened"].dt.to_period("M").astype(str)
    return df


def add_account_age(df: pd.DataFrame, reference_date: datetime | None = None) -> pd.DataFrame:
    """Add Account Age Days column computed from Date Opened."""
    if "Date Opened" not in df.columns:
        return df

    if reference_date is None:
        reference_date = datetime.now()

    ref = pd.Timestamp(reference_date)
    df["Account Age Days"] = (ref - df["Date Opened"]).dt.days.fillna(0).astype(int)

    return df


def add_balance_tier(df: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Add Balance Tier column from Curr Bal using settings bins."""
    if "Curr Bal" not in df.columns:
        return df

    bins = settings.balance_tiers.bins
    labels = settings.balance_tiers.labels

    df["Balance Tier"] = pd.cut(
        df["Curr Bal"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    )

    return df


def add_age_range(df: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Add Age Range column from Account Age Days using settings bins."""
    if "Account Age Days" not in df.columns:
        return df

    bins = settings.age_ranges.bins
    labels = settings.age_ranges.labels

    df["Age Range"] = pd.cut(
        df["Account Age Days"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    )

    return df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_last_12_months(reference_date: datetime | None = None) -> list[str]:
    """Generate last 12 month tags (e.g., ['Feb24', 'Mar24', ...]) from reference date.

    The reference date's month is the most recent month. Tags go back 11 months.
    """
    if reference_date is None:
        reference_date = datetime.now()

    from dateutil.relativedelta import relativedelta

    tags = []
    for i in range(11, -1, -1):
        dt = reference_date - relativedelta(months=i)
        tags.append(dt.strftime("%b%y"))

    return tags
