"""Shared fixtures for txn_analysis tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from txn_analysis.data_loader import load_data
from txn_analysis.settings import Settings

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CSV = DATA_DIR / "sample_transactions.csv"


@pytest.fixture()
def sample_csv_path() -> Path:
    """Path to the synthetic 90-row CSV."""
    return SAMPLE_CSV


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Load the full sample dataset as a raw DataFrame."""
    return pd.read_csv(SAMPLE_CSV)


@pytest.fixture()
def sample_settings(sample_csv_path: Path, tmp_path: Path) -> Settings:
    """Minimal Settings object pointing at the sample CSV."""
    return Settings(data_file=sample_csv_path, output_dir=tmp_path)


@pytest.fixture()
def business_df(sample_df: pd.DataFrame) -> pd.DataFrame:
    """Business-only rows from the sample dataset."""
    return sample_df[sample_df["business_flag"] == "Yes"]


@pytest.fixture()
def personal_df(sample_df: pd.DataFrame) -> pd.DataFrame:
    """Personal-only rows from the sample dataset."""
    return sample_df[sample_df["business_flag"] == "No"]


@pytest.fixture()
def loaded_df(sample_settings: Settings) -> pd.DataFrame:
    """Fully loaded + prepared DataFrame (merchant_consolidated, year_month, etc.)."""
    return load_data(sample_settings)


@pytest.fixture()
def loaded_business_df(loaded_df: pd.DataFrame) -> pd.DataFrame:
    return loaded_df[loaded_df["business_flag"] == "Yes"]


@pytest.fixture()
def loaded_personal_df(loaded_df: pd.DataFrame) -> pd.DataFrame:
    return loaded_df[loaded_df["business_flag"] == "No"]
