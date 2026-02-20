"""Generate synthetic data fixtures for end-to-end pipeline validation.

Run once to create test files:
    python tests/e2e_data/generate_fixtures.py

Creates:
    tests/e2e_data/1200_Test CU_2026.02.xlsx    (ARS ODD)
    tests/e2e_data/9999_ICS_2026.01.xlsx         (ICS)
    tests/e2e_data/8888_transactions.csv          (TXN)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RNG = np.random.default_rng(42)


def generate_ars_odd(n: int = 200) -> pd.DataFrame:
    """Synthetic ODD file with all columns needed by ARS analytics modules."""
    branches = ["Main", "North", "South", "East", "West"]
    prod_codes = ["DDA", "SAV", "CD", "MM"]
    stat_codes = ["O"] * 8 + ["C"] * 2  # 80% open

    dates_opened = pd.date_range("2019-01-01", periods=n, freq="5D")
    stat = RNG.choice(stat_codes, size=n)
    dates_closed = pd.Series([pd.NaT] * n)
    for i in range(n):
        if stat[i] == "C":
            days = RNG.integers(30, 730)
            dates_closed.iloc[i] = dates_opened[i] + pd.Timedelta(days=int(days))

    # Mailer columns (2 mail months)
    mail_seg = RNG.choice(["NU", "TH-10", "TH-15", None], size=n, p=[0.3, 0.2, 0.2, 0.3])
    apr_resp = []
    may_resp = []
    for seg in mail_seg:
        if seg == "NU":
            apr_resp.append(RNG.choice(["NU 5+", "NU 1-4", None], p=[0.3, 0.2, 0.5]))
            may_resp.append(RNG.choice(["NU 5+", "NU 1-4", None], p=[0.35, 0.2, 0.45]))
        elif seg in ("TH-10", "TH-15"):
            apr_resp.append(RNG.choice([seg, None], p=[0.4, 0.6]))
            may_resp.append(RNG.choice([seg, None], p=[0.45, 0.55]))
        else:
            apr_resp.append(None)
            may_resp.append(None)

    df = pd.DataFrame(
        {
            "Account Number": [f"ACC{i:06d}" for i in range(n)],
            "Client ID": ["1200"] * n,
            "Date Opened": dates_opened,
            "Date Closed": dates_closed,
            "Stat Code": stat,
            "Product Code": RNG.choice(prod_codes, size=n, p=[0.5, 0.25, 0.15, 0.1]),
            "Branch": RNG.choice(branches, size=n),
            "Business?": RNG.choice(["Yes", "No"], size=n, p=[0.2, 0.8]),
            "Debit?": RNG.choice(["Yes", "No"], size=n, p=[0.65, 0.35]),
            "Account Holder Age": RNG.integers(18, 85, size=n),
            "Avg Bal": RNG.uniform(100, 50000, size=n).round(2),
            "Balance": RNG.uniform(0, 60000, size=n).round(2),
            "L12M Spend": RNG.uniform(0, 5000, size=n).round(2),
            "L12M Items": RNG.integers(0, 120, size=n),
            "Reg E Code 2026.02": RNG.choice(["Y", "N"], size=n, p=[0.7, 0.3]),
            # Mailer columns
            "Feb24 Spend": RNG.uniform(100, 2000, size=n).round(2),
            "Feb24 Swipes": RNG.integers(1, 60, size=n),
            "Mar24 Spend": RNG.uniform(100, 2000, size=n).round(2),
            "Mar24 Swipes": RNG.integers(1, 60, size=n),
            "Apr24 Mail": mail_seg,
            "Apr24 Resp": apr_resp,
            "Apr24 Spend": RNG.uniform(100, 3000, size=n).round(2),
            "Apr24 Swipes": RNG.integers(1, 70, size=n),
            "May24 Mail": mail_seg,
            "May24 Resp": may_resp,
            "May24 Spend": RNG.uniform(100, 3000, size=n).round(2),
            "May24 Swipes": RNG.integers(1, 70, size=n),
        }
    )
    return df


def generate_ics_data(n: int = 100) -> pd.DataFrame:
    """Synthetic ICS data with all columns needed by ICS analysis pipeline."""
    branches = ["Main", "North", "South", "East", "West"]
    sources = ["DM", "REF", "Blank", "Web"]
    prod_codes = ["100", "200", "300", "400"]
    l12m_tags = [
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

    stat = RNG.choice(["O", "C"], size=n, p=[0.8, 0.2])
    dates_opened = pd.to_datetime(
        pd.Timestamp("2023-01-01") + pd.to_timedelta(RNG.integers(0, 1095, size=n), unit="D")
    )

    dates_closed = pd.Series([pd.NaT] * n)
    for i in range(n):
        if stat[i] == "C":
            days = RNG.integers(30, 365)
            dates_closed.iloc[i] = dates_opened[i] + pd.Timedelta(days=int(days))

    rows: dict = {
        "ICS Account": RNG.choice(["Yes", "No"], size=n, p=[0.3, 0.7]),
        "Stat Code": stat,
        "Debit?": RNG.choice(["Yes", "No"], size=n, p=[0.6, 0.4]),
        "Business?": RNG.choice(["Yes", "No"], size=n, p=[0.2, 0.8]),
        "Branch": RNG.choice(branches, size=n),
        "Source": RNG.choice(sources, size=n),
        "Prod Code": RNG.choice(prod_codes, size=n),
        "Curr Bal": RNG.uniform(-100, 200000, size=n).round(2),
        "Avg Bal": RNG.uniform(0, 150000, size=n).round(2),
        "Date Opened": dates_opened,
        "Date Closed": dates_closed,
    }

    for tag in l12m_tags:
        rows[f"{tag} Swipes"] = RNG.integers(0, 50, size=n)
        rows[f"{tag} Spend"] = RNG.uniform(0, 500, size=n).round(2)

    return pd.DataFrame(rows)


def generate_txn_data(n: int = 200) -> pd.DataFrame:
    """Synthetic transaction data with all columns needed by TXN pipeline."""
    merchants = [
        "Walmart",
        "Amazon",
        "Costco",
        "Target",
        "Kroger",
        "Shell Gas",
        "Chevron",
        "McDonald's",
        "Starbucks",
        "Subway",
        "Home Depot",
        "Lowe's",
        "CVS Pharmacy",
        "Walgreens",
        "Netflix",
        "AT&T",
        "Verizon",
        "Uber",
        "Lyft",
        "DoorDash",
    ]
    mcc_codes = [
        5411,
        5411,
        5311,
        5311,
        5411,
        5541,
        5541,
        5812,
        5814,
        5812,
        5211,
        5211,
        5912,
        5912,
        4899,
        4812,
        4812,
        4121,
        4121,
        5812,
    ]
    mcc_descriptions = [
        "Grocery Stores",
        "Grocery Stores",
        "Department Stores",
        "Department Stores",
        "Grocery Stores",
        "Service Stations",
        "Service Stations",
        "Restaurants",
        "Fast Food",
        "Restaurants",
        "Building Materials",
        "Building Materials",
        "Drug Stores",
        "Drug Stores",
        "Cable/Satellite",
        "Telecom",
        "Telecom",
        "Ride Sharing",
        "Ride Sharing",
        "Restaurants",
    ]

    merchant_idx = RNG.integers(0, len(merchants), size=n)
    dates = pd.date_range("2025-07-01", periods=180, freq="D")
    txn_dates = RNG.choice(dates, size=n)

    df = pd.DataFrame(
        {
            "primary_account_num": [f"4{RNG.integers(100000000, 999999999)}" for _ in range(n)],
            "merchant_name": [merchants[i] for i in merchant_idx],
            "merchant_consolidated": [merchants[i] for i in merchant_idx],
            "amount": RNG.uniform(1.50, 500.0, size=n).round(2),
            "transaction_date": txn_dates,
            "mcc_code": [mcc_codes[i] for i in merchant_idx],
            "mcc_description": [mcc_descriptions[i] for i in merchant_idx],
            "business_flag": RNG.choice(["Yes", "No"], size=n, p=[0.15, 0.85]),
        }
    )
    return df


def main():
    print("Generating synthetic E2E data fixtures...")

    # ARS ODD
    ars_df = generate_ars_odd(200)
    ars_path = HERE / "1200_Test CU_2026.02.xlsx"
    ars_df.to_excel(ars_path, index=False, engine="openpyxl")
    print(f"  ARS ODD: {ars_path} ({len(ars_df)} rows, {len(ars_df.columns)} cols)")

    # ICS
    ics_df = generate_ics_data(100)
    ics_path = HERE / "9999_ICS_2026.01.xlsx"
    ics_df.to_excel(ics_path, index=False, engine="openpyxl")
    print(f"  ICS:     {ics_path} ({len(ics_df)} rows, {len(ics_df.columns)} cols)")

    # TXN
    txn_df = generate_txn_data(200)
    txn_path = HERE / "8888_transactions.csv"
    txn_df.to_csv(txn_path, index=False)
    print(f"  TXN:     {txn_path} ({len(txn_df)} rows, {len(txn_df.columns)} cols)")

    print("Done.")


if __name__ == "__main__":
    main()
