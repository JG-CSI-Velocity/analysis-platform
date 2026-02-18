"""Shared fixtures for integration tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def integration_output_dir(tmp_path: Path) -> Path:
    """Temporary output directory for integration tests."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def sample_txn_csv(tmp_path: Path) -> Path:
    """Create a minimal transaction CSV for end-to-end txn pipeline testing."""
    rng = np.random.default_rng(42)
    n = 200
    accounts = [f"ACCT{i:04d}" for i in range(1, 21)]
    merchants = [
        "WALMART", "AMAZON.COM", "COSTCO", "TARGET", "STARBUCKS",
        "SHELL OIL", "KROGER", "HOME DEPOT", "NETFLIX", "SPOTIFY",
        "CHASE BANK", "WELLS FARGO", "APPLE.COM", "UBER", "MCDONALDS",
    ]
    mcc_codes = [5411, 5942, 5300, 5311, 5812, 5541, 5411, 5200, 4899, 5815, 6011, 6011, 5735, 4121, 5814]

    dates = pd.date_range("2025-06-01", periods=90, freq="D")
    rows = []
    for _ in range(n):
        idx = rng.integers(0, len(merchants))
        rows.append({
            "merchant_name": merchants[idx],
            "amount": round(float(rng.uniform(1, 500)), 2),
            "primary_account_num": rng.choice(accounts),
            "transaction_date": str(pd.Timestamp(rng.choice(dates)).date()),
            "mcc_code": mcc_codes[idx],
            "business_flag": rng.choice(["Yes", "No"], p=[0.15, 0.85]),
        })

    df = pd.DataFrame(rows)
    path = tmp_path / "sample_transactions.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_ics_xlsx(tmp_path: Path) -> Path:
    """Create a minimal ICS Excel file for end-to-end ICS pipeline testing."""
    rng = np.random.default_rng(42)
    n = 60

    l12m_tags = ["Feb25", "Mar25", "Apr25", "May25", "Jun25", "Jul25",
                 "Aug25", "Sep25", "Oct25", "Nov25", "Dec25", "Jan26"]

    rows = {
        "ICS Account": rng.choice(["Yes", "No"], size=n, p=[0.3, 0.7]),
        "Stat Code": rng.choice(["O", "C"], size=n, p=[0.8, 0.2]),
        "Debit?": rng.choice(["Yes", "No"], size=n, p=[0.6, 0.4]),
        "Business?": rng.choice(["Yes", "No"], size=n, p=[0.2, 0.8]),
        "Branch": rng.choice(["Main", "North", "South"], size=n),
        "Source": rng.choice(["DM", "REF", "Blank"], size=n),
        "Prod Code": rng.choice(["100", "200", "300"], size=n),
        "Curr Bal": rng.uniform(-100, 200000, size=n).round(2),
        "Avg Bal": rng.uniform(0, 150000, size=n).round(2),
    }

    start = pd.Timestamp("2023-01-01")
    days = (pd.Timestamp("2026-01-01") - start).days
    rows["Date Opened"] = pd.to_datetime(
        start + pd.to_timedelta(rng.integers(0, days, size=n), unit="D")
    )

    closed_mask = np.array(rows["Stat Code"]) == "C"
    date_closed = pd.Series([pd.NaT] * n)
    for i in range(n):
        if closed_mask[i]:
            date_closed.iloc[i] = rows["Date Opened"][i] + pd.Timedelta(days=int(rng.integers(30, 365)))
    rows["Date Closed"] = date_closed

    for tag in l12m_tags:
        rows[f"{tag} Swipes"] = rng.integers(0, 50, size=n)
        rows[f"{tag} Spend"] = rng.uniform(0, 500, size=n).round(2)

    df = pd.DataFrame(rows)
    path = tmp_path / "sample_ics.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    return path
