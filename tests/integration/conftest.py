"""Shared fixtures for integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


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


@pytest.fixture
def sample_oddd_xlsx(tmp_path: Path) -> Path:
    """Create a minimal ODDD Excel file for ARS pipeline testing.

    Filename follows the required pattern: {ClientID}-{year}-{month}-{name}-ODD.xlsx
    """
    rng = np.random.default_rng(42)
    n = 80

    stat_codes = rng.choice(["A", "B", "C"], size=n, p=[0.6, 0.3, 0.1])
    rows = {
        "Stat Code": stat_codes,
        "Prod Code": rng.choice(["101", "102", "200"], size=n),
        "Branch": rng.choice(["01", "02", "03"], size=n),
        "Mailable?": rng.choice(["Yes", "No"], size=n, p=[0.7, 0.3]),
        "Debit?": rng.choice(["Yes", "No"], size=n, p=[0.6, 0.4]),
        "Business?": rng.choice(["Yes", "No"], size=n, p=[0.2, 0.8]),
        "Avg Bal": rng.uniform(100, 50000, size=n).round(2),
    }

    start = pd.Timestamp("2020-01-01")
    days_range = (pd.Timestamp("2025-12-01") - start).days
    rows["Date Opened"] = pd.to_datetime(
        start + pd.to_timedelta(rng.integers(0, days_range, size=n), unit="D")
    )

    closed_mask = np.array(stat_codes) == "C"
    date_closed = pd.Series([pd.NaT] * n)
    for i in range(n):
        if closed_mask[i]:
            date_closed.iloc[i] = rows["Date Opened"][i] + pd.Timedelta(
                days=int(rng.integers(30, 365))
            )
    rows["Date Closed"] = date_closed

    # Add a Reg E Code column
    rows["Jan26 Reg E Code"] = rng.choice(["Y", "N", ""], size=n, p=[0.4, 0.4, 0.2])

    df = pd.DataFrame(rows)
    path = tmp_path / "9999-2026-01-Test CU-ODD.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    return path


@pytest.fixture
def ars_client_config(tmp_path: Path) -> Path:
    """Create a minimal ARS clients_config.json for client 9999."""
    config = {
        "9999": {
            "EligibleStatusCodes": ["A", "B"],
            "EligibleProductCodes": ["101", "102", "200"],
            "EligibleMailCode": ["Yes"],
            "RegEOptInCode": ["Y"],
            "ICRate": "0.15",
            "NSF_OD_Fee": "25.00",
            "ClientName": "Test CU",
        }
    }
    path = tmp_path / "clients_config.json"
    path.write_text(json.dumps(config, indent=2))
    return path


@pytest.fixture
def v4_txn_dir(tmp_path: Path) -> Path:
    """Create synthetic tab-delimited transaction files for V4 pipeline.

    Creates files in a year-folder with the naming pattern:
    9999-trans-{MMDDYYYY}.csv
    """
    rng = np.random.default_rng(42)
    txn_dir = tmp_path / "transactions"
    year_folder = txn_dir / "2025"
    year_folder.mkdir(parents=True)

    accounts = [f"ACCT{i:04d}" for i in range(1, 21)]
    merchants = [
        "WALMART", "AMAZON.COM", "COSTCO", "TARGET", "STARBUCKS",
        "SHELL OIL", "KROGER", "HOME DEPOT", "NETFLIX", "CHASE BANK",
    ]
    mcc_codes = [5411, 5942, 5300, 5311, 5812, 5541, 5411, 5200, 4899, 6011]

    # Create 3 monthly files
    for month_num in [6, 7, 8]:
        rows = []
        n = 80
        for _ in range(n):
            idx = rng.integers(0, len(merchants))
            day = rng.integers(1, 29)
            rows.append([
                f"2025-{month_num:02d}-{day:02d}",
                rng.choice(accounts),
                "DEBIT",
                f"{rng.uniform(1, 500):.2f}",
                mcc_codes[idx],
                merchants[idx],
                "LOCATION1",
                "LOCATION2",
                f"TERM{rng.integers(1, 99):04d}",
                f"MERCH{rng.integers(1, 999):06d}",
                "INST001",
                "Y",
                "00",
            ])

        # Write tab-delimited with a header row (which gets skipped)
        header = "HEADER ROW - SKIPPED BY LOADER"
        lines = [header] + ["\t".join(str(c) for c in row) for row in rows]
        file_path = year_folder / f"9999-trans-{month_num:02d}012025.csv"
        file_path.write_text("\n".join(lines))

    return txn_dir


@pytest.fixture
def v4_odd_xlsx(tmp_path: Path) -> Path:
    """Create a minimal ODD Excel file for V4 storyline testing."""
    rng = np.random.default_rng(42)
    n = 20  # Match the 20 accounts in v4_txn_dir
    accounts = [f"ACCT{i:04d}" for i in range(1, 21)]

    rows = {
        "Acct Number": accounts,
        "Account Holder Age": rng.integers(18, 80, size=n),
        "Avg Bal": rng.uniform(100, 20000, size=n).round(2),
        "Branch": rng.choice(["Main", "North", "South"], size=n),
        "Business?": rng.choice(["Yes", "No"], size=n, p=[0.15, 0.85]),
        "Debit?": rng.choice(["Yes", "No"], size=n, p=[0.8, 0.2]),
    }

    start = pd.Timestamp("2018-01-01")
    days_range = (pd.Timestamp("2025-01-01") - start).days
    rows["Date Opened"] = pd.to_datetime(
        start + pd.to_timedelta(rng.integers(0, days_range, size=n), unit="D")
    )
    rows["Date Closed"] = [pd.NaT] * n

    df = pd.DataFrame(rows)
    path = tmp_path / "9999_odd.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    return path


@pytest.fixture
def v4_config_yaml(tmp_path: Path, v4_txn_dir: Path, v4_odd_xlsx: Path) -> Path:
    """Create a minimal V4 config YAML file."""
    config = {
        "client_id": "9999",
        "client_name": "Test CU",
        "client_state": "CT",
        "transaction_dir": str(v4_txn_dir),
        "file_extension": "csv",
        "odd_file": str(v4_odd_xlsx),
        "output_dir": str(tmp_path / "v4_output"),
        "recent_months": 12,
        "top_n": 10,
        "growth_min_threshold": 100.0,
        "consistency_min_spend": 100.0,
        "consistency_min_months": 2,
        "interchange_rate": 0.015,
        "competitors": {
            "big_nationals": {
                "starts_with": ["CHASE BANK", "WELLS FARGO", "BANK OF AMERICA"],
                "exact": [],
                "contains": [],
            },
        },
        "finserv": {
            "auto_loans": ["AUTO LOAN"],
            "credit_cards": ["CHASE CARD"],
        },
        "payroll": {
            "processors": ["ADP", "PAYCHEX"],
            "min_spend": 500,
            "max_match_count": 5,
            "skip_terms": ["REFUND"],
        },
        "false_positives": [],
    }
    path = tmp_path / "v4_config.yaml"
    path.write_text(yaml.dump(config, default_flow_style=False))
    return path
