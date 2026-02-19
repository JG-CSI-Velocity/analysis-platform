"""Shared fixtures for ARS analysis tests."""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from ars_analysis.pipeline import create_context


@pytest.fixture
def chart_dir(tmp_path):
    """Temporary chart output directory."""
    d = tmp_path / "charts"
    d.mkdir()
    return d


@pytest.fixture
def odd_data():
    """Realistic ODD DataFrame with columns used across all ARS suites."""
    rng = np.random.default_rng(42)
    n = 200

    dates_opened = pd.date_range("2015-01-01", periods=n, freq="14D")
    # 15% of accounts are closed
    closed_mask = rng.random(n) < 0.15
    dates_closed = pd.Series([pd.NaT] * n)
    dates_closed[closed_mask] = pd.to_datetime(
        rng.choice(pd.date_range("2023-01-01", "2025-12-01", freq="ME"), closed_mask.sum())
    )

    stat_codes = np.where(closed_mask, "C", "O")
    business = rng.choice(["Yes", "No"], n, p=[0.25, 0.75])
    debit = rng.choice(["Yes", "No"], n, p=[0.65, 0.35])
    prod_codes = rng.choice(["001", "002", "003"], n)
    mailable = rng.choice(["Yes", "No"], n, p=[0.8, 0.2])
    avg_bal = rng.uniform(-500, 50000, n).round(2)
    branches = rng.choice(["Main", "North", "South", "East"], n)
    holder_age = rng.integers(18, 85, n)
    reg_e = rng.choice(["Opted In", "Opted Out", "N/A", None], n, p=[0.3, 0.3, 0.2, 0.2])

    # Spend/Items columns (L12M)
    spend = rng.uniform(0, 5000, n).round(2)
    items = rng.integers(0, 200, n)

    df = pd.DataFrame({
        "Stat Code": stat_codes,
        "Date Opened": dates_opened,
        "Date Closed": dates_closed,
        "Business?": business,
        "Debit?": debit,
        "Prod Code": prod_codes,
        "Mailable?": mailable,
        "Avg Bal": avg_bal,
        "Branch": branches,
        "Holder Age": holder_age,
        "Dec24 Reg E": reg_e,
        "L12M Spend": spend,
        "L12M Items": items,
    })

    # Mailer columns (for mailer suite tests)
    df["Jan25 Mail"] = rng.choice(["NU", "TH-10", "TH-15", None], n, p=[0.2, 0.1, 0.1, 0.6])
    df["Jan25 Resp"] = rng.choice(
        ["NU 5+", "NU 1-4", "TH-10", None], n, p=[0.05, 0.05, 0.05, 0.85]
    )
    df["Jan25 Spend"] = rng.uniform(0, 1000, n).round(2)
    df["Jan25 Swipes"] = rng.integers(0, 50, n)

    return df


@pytest.fixture
def ars_ctx(odd_data, chart_dir):
    """Full ARS pipeline context with realistic data subsets.

    This ctx mirrors what pipeline.py builds by step_create_subsets().
    """
    ctx = create_context()
    ctx["data"] = odd_data.copy()
    ctx["data_original"] = odd_data.copy()
    ctx["chart_dir"] = chart_dir  # Path object -- some modules wrap with Path(), others use directly
    ctx["results"] = {}
    ctx["all_slides"] = []
    ctx["export_log"] = []

    # Identity
    ctx["client_id"] = "9999"
    ctx["client_name"] = "Test Credit Union"
    ctx["year"] = "2025"
    ctx["month"] = "01"

    # Config
    ctx["eligible_stat_code"] = ["O"]
    ctx["eligible_prod_code"] = ["001", "002", "003"]
    ctx["eligible_mailable"] = ["Yes"]
    ctx["reg_e_opt_in"] = ["Opted In"]
    ctx["nsf_od_fee"] = 25.0
    ctx["ic_rate"] = 0.005

    # Date ranges
    ctx["start_date"] = pd.Timestamp("2024-01-01")
    ctx["end_date"] = pd.Timestamp("2025-01-01")
    ctx["last_12_months"] = pd.date_range("2024-01-01", periods=12, freq="MS").strftime("%b%y").tolist()

    # Subsets (mirror step_create_subsets logic)
    data = odd_data
    open_accts = data[data["Stat Code"] == "O"].copy()
    closed_accts = data[data["Stat Code"] == "C"].copy()
    eligible = open_accts[
        open_accts["Prod Code"].isin(ctx["eligible_prod_code"])
    ].copy()

    ctx["open_accounts"] = open_accts
    ctx["closed_accounts"] = closed_accts
    ctx["eligible_data"] = eligible
    ctx["eligible_personal"] = eligible[eligible["Business?"] == "No"].copy()
    ctx["eligible_business"] = eligible[eligible["Business?"] == "Yes"].copy()
    ctx["eligible_with_debit"] = eligible[eligible["Debit?"] == "Yes"].copy()
    ctx["eligible_without_debit"] = eligible[eligible["Debit?"] == "No"].copy()
    ctx["eligible_personal_with_debit"] = ctx["eligible_personal"][
        ctx["eligible_personal"]["Debit?"] == "Yes"
    ].copy()
    ctx["eligible_business_with_debit"] = ctx["eligible_business"][
        ctx["eligible_business"]["Debit?"] == "Yes"
    ].copy()
    ctx["open_personal"] = open_accts[open_accts["Business?"] == "No"].copy()
    ctx["open_business"] = open_accts[open_accts["Business?"] == "Yes"].copy()

    # Reg E columns
    ctx["latest_reg_e_column"] = "Dec24 Reg E"
    reg_col = ctx["latest_reg_e_column"]
    reg_base = eligible[eligible[reg_col].isin(["Opted In", "Opted Out"])].copy()
    ctx["reg_e_eligible_base"] = reg_base
    ctx["reg_e_eligible_base_l12m"] = reg_base  # simplified for tests
    ctx["reg_e_opted_in"] = reg_base[reg_base[reg_col] == "Opted In"].copy()
    ctx["reg_e_opted_out"] = reg_base[reg_base[reg_col] == "Opted Out"].copy()

    # L12M subsets
    ctx["eligible_last_12m"] = eligible
    ctx["eligible_personal_last_12m"] = ctx["eligible_personal"]
    ctx["eligible_business_last_12m"] = ctx["eligible_business"]
    ctx["open_last_12m"] = open_accts

    # Stub out Excel save to avoid real file I/O
    ctx["_save_to_excel"] = MagicMock()

    # Config dict (some analyses access ctx["config"]["BranchMapping"] etc.)
    ctx["config"] = {}
    ctx["client_config"] = {}

    # Source folder for chart paths
    ctx["source_folder"] = str(chart_dir.parent)

    return ctx
