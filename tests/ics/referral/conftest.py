"""Shared fixtures for referral pipeline tests."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from ics_toolkit.referral.column_map import REQUIRED_COLUMNS
from ics_toolkit.settings import ReferralSettings

REFERENCE_DATE = datetime(2026, 1, 15)

REFERRERS = [
    "JOHN SMITH",
    "JANE DOE",
    "BOB WILSON",
    "ALICE BROWN",
    "TOM JONES",
    "MARY CLARK",
    "DAVID HALL",
    "SARAH KING",
]
STAFF = ["SARAH MANAGER", "MIKE HANDLER", "LISA PROCESSOR"]
BRANCHES = ["001", "002", "003"]
CODES = [
    "150A001",
    "120A002",
    "PC100",
    None,
    "EMAIL_Q1",
    "080A003",
    None,
    "UNKNOWN_XYZ",
]


@pytest.fixture(scope="session")
def rng():
    """Deterministic random number generator."""
    return np.random.default_rng(42)


@pytest.fixture
def sample_referral_df(rng):
    """50-row deterministic referral dataset with known patterns.

    Guarantees:
    - At least some referrers have multiple referrals (JOHN SMITH, JANE DOE)
    - Mix of null and non-null referral codes
    - All branches represented
    - Sequential dates covering ~1 year
    """
    n = 50
    # Bias toward repeat referrers for testable patterns
    referrer_weights = [0.25, 0.20, 0.15, 0.10, 0.10, 0.08, 0.07, 0.05]
    referrers = rng.choice(REFERRERS, n, p=referrer_weights)

    return pd.DataFrame(
        {
            "Referrer Name": referrers,
            "Issue Date": pd.date_range("2025-01-01", periods=n, freq="7D"),
            "Referral Code": rng.choice(CODES, n),
            "Purchase Manager": rng.choice(STAFF, n),
            "Branch": rng.choice(BRANCHES, n),
            "Account Holder": [f"NEW_ACCOUNT_{i:03d}" for i in range(n)],
            "MRDB Account Hash": [f"HASH_{i:04d}" for i in range(n)],
            "Cert ID": [f"CERT_{i:04d}" for i in range(n)],
        }
    )


@pytest.fixture
def sample_referral_settings(tmp_path, sample_referral_df):
    """Write sample data to tmp xlsx and create ReferralSettings."""
    data_path = tmp_path / "test_referral.xlsx"
    sample_referral_df.to_excel(data_path, index=False, engine="openpyxl")
    return ReferralSettings(
        data_file=data_path,
        output_dir=tmp_path / "output",
    )


@pytest.fixture
def empty_referral_df():
    """Empty DataFrame with correct columns."""
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


@pytest.fixture
def single_row_referral_df():
    """Single-row DataFrame for edge-case testing."""
    return pd.DataFrame(
        {
            "Referrer Name": ["JOHN SMITH"],
            "Issue Date": [pd.Timestamp("2025-06-15")],
            "Referral Code": ["150A001"],
            "Purchase Manager": ["SARAH MANAGER"],
            "Branch": ["001"],
            "Account Holder": ["NEW_PERSON"],
            "MRDB Account Hash": ["HASH_SINGLE"],
            "Cert ID": ["CERT_SINGLE"],
        }
    )
