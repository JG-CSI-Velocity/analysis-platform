"""Shared test fixtures for ICS Analysis."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from ics_toolkit.settings import AnalysisSettings as Settings

# Reference date for consistent test data
REFERENCE_DATE = datetime(2026, 1, 15)

# L12M month tags relative to January 2026
L12M_TAGS = [
    "Feb25",
    "Mar25",
    "Apr25",
    "May25",
    "Jun25",
    "Jul25",
    "Aug25",
    "Sep25",
    "Oct25",
    "Nov25",
    "Dec25",
    "Jan26",
]


def _build_sample_data(n: int = 50) -> pd.DataFrame:
    """Build a synthetic ICS dataset for testing."""
    rng = np.random.default_rng(42)

    branches = ["Main", "North", "South", "East", "West"]
    sources = ["DM", "REF", "Blank", "Web"]
    prod_codes = ["100", "200", "300", "400"]

    rows = {
        "ICS Account": rng.choice(["Yes", "No"], size=n, p=[0.3, 0.7]),
        "Stat Code": rng.choice(["O", "C"], size=n, p=[0.8, 0.2]),
        "Debit?": rng.choice(["Yes", "No"], size=n, p=[0.6, 0.4]),
        "Business?": rng.choice(["Yes", "No"], size=n, p=[0.2, 0.8]),
        "Branch": rng.choice(branches, size=n),
        "Source": rng.choice(sources, size=n),
        "Prod Code": rng.choice(prod_codes, size=n),
        "Curr Bal": rng.uniform(-100, 200000, size=n).round(2),
        "Avg Bal": rng.uniform(0, 150000, size=n).round(2),
    }

    # Date Opened: spread across 2023-2026
    start = pd.Timestamp("2023-01-01")
    end = pd.Timestamp("2026-01-01")
    date_range_days = (end - start).days
    rows["Date Opened"] = pd.to_datetime(
        start + pd.to_timedelta(rng.integers(0, date_range_days, size=n), unit="D")
    )

    # Date Closed: only for Stat Code C
    closed_mask = np.array(rows["Stat Code"]) == "C"
    date_closed = pd.Series([pd.NaT] * n)
    for i in range(n):
        if closed_mask[i]:
            opened = rows["Date Opened"][i]
            days_open = rng.integers(30, 365)
            date_closed.iloc[i] = opened + pd.Timedelta(days=days_open)
    rows["Date Closed"] = date_closed

    # L12M monthly columns
    for tag in L12M_TAGS:
        rows[f"{tag} Swipes"] = rng.integers(0, 50, size=n)
        rows[f"{tag} Spend"] = rng.uniform(0, 500, size=n).round(2)

    return pd.DataFrame(rows)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """50-row synthetic ICS dataset."""
    return _build_sample_data(50)


@pytest.fixture
def sample_settings(tmp_path, sample_df) -> Settings:
    """Settings configured with a temporary sample data file."""
    data_file = tmp_path / "sample.xlsx"
    sample_df.to_excel(data_file, index=False, engine="openpyxl")

    return Settings(
        data_file=data_file,
        client_id="9999",
        client_name="Test CU",
        output_dir=tmp_path / "output",
        cohort_start="2025-01",
        last_12_months=L12M_TAGS,
    )


@pytest.fixture
def ics_all(sample_df) -> pd.DataFrame:
    """ICS accounts only."""
    return sample_df[sample_df["ICS Account"] == "Yes"].copy()


@pytest.fixture
def ics_stat_o(sample_df) -> pd.DataFrame:
    """ICS accounts with Stat Code O."""
    return sample_df[(sample_df["ICS Account"] == "Yes") & (sample_df["Stat Code"] == "O")].copy()


@pytest.fixture
def ics_stat_o_debit(sample_df) -> pd.DataFrame:
    """ICS accounts with Stat Code O and Debit."""
    return sample_df[
        (sample_df["ICS Account"] == "Yes")
        & (sample_df["Stat Code"] == "O")
        & (sample_df["Debit?"] == "Yes")
    ].copy()
