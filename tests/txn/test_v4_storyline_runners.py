"""Tests for V4 storyline run() functions with realistic test data.

Each storyline module's run(ctx) is called with a synthetic context dict
containing the same shape of data the real pipeline produces. Tests verify
the return structure (title, sections, sheets) without checking exact values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def v4_ctx():
    """Build a synthetic context dict matching the real pipeline's output shape.

    Provides: combined_df, business_df, personal_df, odd_df, config.
    All DataFrames have realistic column names and a small but varied dataset.
    """
    np.random.seed(42)
    n_txn = 200
    n_accts = 20

    acct_nums = [f"A{i:04d}" for i in range(n_accts)]
    dates = pd.date_range("2024-07-01", "2025-06-30", freq="D")

    # Transaction data
    txn_dates = np.random.choice(dates, size=n_txn)
    txn_accts = np.random.choice(acct_nums, size=n_txn)
    txn_amounts = np.random.lognormal(mean=3, sigma=1.5, size=n_txn).round(2)
    mcc_codes = np.random.choice([5411, 5541, 5812, 6010, 6011, 5311, 5912], size=n_txn)
    merchants = np.random.choice(
        [
            "WALMART #1234",
            "AMAZON MARKETPLACE",
            "SHELL OIL",
            "MCDONALDS",
            "CHASE BANK",
            "WELLS FARGO",
            "VENMO PAYMENT",
            "LOCAL GROCERY",
            "NETFLIX",
            "TARGET STORE",
        ],
        size=n_txn,
    )
    txn_types = np.random.choice(["PIN", "SIG", "ECOM"], size=n_txn)

    combined_df = pd.DataFrame(
        {
            "primary_account_num": txn_accts,
            "transaction_date": pd.to_datetime(txn_dates),
            "amount": txn_amounts,
            "mcc_code": mcc_codes,
            "merchant_name": merchants,
            "merchant_consolidated": merchants,  # simplified for tests
            "transaction_type": txn_types,
            "card_present": np.random.choice(["Y", "N"], size=n_txn),
            "transaction_code": np.random.choice(["00", "01", "02"], size=n_txn),
            "terminal_id": [f"T{i}" for i in range(n_txn)],
        }
    )
    combined_df["year_month"] = combined_df["transaction_date"].dt.to_period("M")

    # ODD (account-level) data
    odd_df = pd.DataFrame(
        {
            "Acct Number": acct_nums,
            "Business?": np.random.choice(["Yes", "No"], size=n_accts, p=[0.2, 0.8]),
            "Debit?": np.random.choice(["Yes", "No"], size=n_accts, p=[0.7, 0.3]),
            "Account Holder Age": np.random.randint(18, 80, size=n_accts),
            "Date Opened": pd.date_range("2015-01-01", periods=n_accts, freq="90D"),
            "Date Closed": [pd.NaT] * n_accts,
            "Avg Bal": np.random.uniform(100, 15000, size=n_accts).round(2),
            "Branch": np.random.choice(["HQ", "Downtown", "West", "East"], size=n_accts),
            "Stat Code": np.random.choice(["A", "C", "O"], size=n_accts, p=[0.7, 0.1, 0.2]),
        }
    )
    odd_df["generation"] = odd_df["Account Holder Age"].apply(_gen_from_age)
    odd_df["balance_tier"] = odd_df["Avg Bal"].apply(_tier_from_bal)
    odd_df["tenure_years"] = np.random.uniform(1, 15, size=n_accts).round(1)

    # Add monthly time series columns to ODD (needed by s7 campaigns, s8 payroll)
    for month in ["Jan25", "Feb25", "Mar25"]:
        odd_df[f"{month} Spend"] = np.random.uniform(0, 2000, size=n_accts).round(2)
        odd_df[f"{month} PIN $"] = np.random.uniform(0, 1000, size=n_accts).round(2)
        odd_df[f"{month} Sig $"] = np.random.uniform(0, 1000, size=n_accts).round(2)
        odd_df[f"{month} PIN #"] = np.random.randint(0, 30, size=n_accts)
        odd_df[f"{month} Sig #"] = np.random.randint(0, 30, size=n_accts)

    # Merge ODD into combined for enriched columns.
    # Exclude Date Opened / Date Closed / Acct Number -- storylines that need
    # these do their own merges from odd_df and would get suffixed duplicates.
    merge_cols = [
        c
        for c in [
            "Acct Number",
            "generation",
            "balance_tier",
            "tenure_years",
            "Branch",
            "Business?",
            "Debit?",
            "Avg Bal",
            "Account Holder Age",
        ]
        if c in odd_df.columns
    ]
    combined_df = combined_df.merge(
        odd_df[merge_cols], left_on="primary_account_num", right_on="Acct Number", how="left"
    )
    combined_df.drop(columns=["Acct Number"], inplace=True, errors="ignore")

    # Split by business flag
    business_df = combined_df[combined_df["Business?"] == "Yes"].copy()
    personal_df = combined_df[combined_df["Business?"] == "No"].copy()

    config = {
        "client_name": "Test Credit Union",
        "client_id": "9999",
        "competitors": {
            "big_nationals": {"contains": ["CHASE", "WELLS FARGO", "BANK OF AMERICA"]},
            "wallets_p2p": {"contains": ["VENMO", "ZELLE", "CASH APP"]},
        },
        "false_positives": [],
        "financial_services": {
            "categories": {
                "insurance": {"contains": ["GEICO", "STATE FARM"]},
                "lending": {"contains": ["SOFI", "LENDING"]},
            }
        },
    }

    return {
        "combined_df": combined_df,
        "business_df": business_df,
        "personal_df": personal_df,
        "odd_df": odd_df,
        "config": config,
    }


def _gen_from_age(age):
    if 12 <= age <= 27:
        return "Gen Z"
    if 28 <= age <= 43:
        return "Millennial"
    if 44 <= age <= 59:
        return "Gen X"
    if 60 <= age <= 78:
        return "Boomer"
    return "Silent"


def _tier_from_bal(bal):
    if bal < 500:
        return "Low"
    if bal < 2000:
        return "Medium"
    if bal < 10000:
        return "High"
    return "Very High"


def _assert_storyline_result(result: dict) -> None:
    """Common assertions for all storyline results."""
    assert isinstance(result, dict)
    assert "title" in result
    assert "sections" in result
    assert "sheets" in result
    assert isinstance(result["sections"], list)
    assert isinstance(result["sheets"], list)


# ---------------------------------------------------------------------------
# S1: Portfolio Health
# ---------------------------------------------------------------------------


class TestS1PortfolioHealth:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s1_portfolio_health import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Portfolio" in result["title"]

    def test_has_sections(self, v4_ctx):
        from txn_analysis.storylines.v4_s1_portfolio_health import run

        result = run(v4_ctx)
        assert len(result["sections"]) > 0

    def test_has_sheets(self, v4_ctx):
        from txn_analysis.storylines.v4_s1_portfolio_health import run

        result = run(v4_ctx)
        assert len(result["sheets"]) > 0


# ---------------------------------------------------------------------------
# S2: Merchant Intelligence
# ---------------------------------------------------------------------------


class TestS2MerchantIntel:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s2_merchant_intel import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Merchant" in result["title"]

    def test_has_sections(self, v4_ctx):
        from txn_analysis.storylines.v4_s2_merchant_intel import run

        result = run(v4_ctx)
        assert len(result["sections"]) > 0


# ---------------------------------------------------------------------------
# S3: Competitive Landscape
# ---------------------------------------------------------------------------


class TestS3Competition:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s3_competition import run

        result = run(v4_ctx)
        _assert_storyline_result(result)

    def test_populates_ctx_for_sub_modules(self, v4_ctx):
        from txn_analysis.storylines.v4_s3_competition import run

        run(v4_ctx)
        assert "s3_tagged_df" in v4_ctx
        assert "s3_competitor_df" in v4_ctx


# ---------------------------------------------------------------------------
# S3B: Threat Intelligence
# ---------------------------------------------------------------------------


class TestS3BThreatAnalysis:
    def test_run_with_competitor_data(self, v4_ctx):
        from txn_analysis.storylines.v4_s3_competition import run as run_s3
        from txn_analysis.storylines.v4_s3_threat_analysis import run

        run_s3(v4_ctx)  # populate s3_competitor_df / s3_tagged_df
        result = run(v4_ctx)
        _assert_storyline_result(result)

    def test_run_without_competitor_data(self, v4_ctx):
        from txn_analysis.storylines.v4_s3_threat_analysis import run

        result = run(v4_ctx)  # s3_competitor_df not set
        _assert_storyline_result(result)


# ---------------------------------------------------------------------------
# S3C: Account Segmentation
# ---------------------------------------------------------------------------


class TestS3CSegmentation:
    def test_run_with_competitor_data(self, v4_ctx):
        from txn_analysis.storylines.v4_s3_competition import run as run_s3
        from txn_analysis.storylines.v4_s3_segmentation import run

        run_s3(v4_ctx)
        result = run(v4_ctx)
        _assert_storyline_result(result)

    def test_run_without_competitor_data(self, v4_ctx):
        from txn_analysis.storylines.v4_s3_segmentation import run

        result = run(v4_ctx)
        _assert_storyline_result(result)


# ---------------------------------------------------------------------------
# S4: Financial Services Intelligence
# ---------------------------------------------------------------------------


class TestS4FinServ:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s4_finserv import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Financial" in result["title"]


# ---------------------------------------------------------------------------
# S5: Demographics & Branch Performance
# ---------------------------------------------------------------------------


class TestS5Demographics:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s5_demographics import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Demographic" in result["title"]

    def test_has_sections(self, v4_ctx):
        from txn_analysis.storylines.v4_s5_demographics import run

        result = run(v4_ctx)
        assert len(result["sections"]) > 0


# ---------------------------------------------------------------------------
# S6: Risk & Balance Correlation
# ---------------------------------------------------------------------------


class TestS6Risk:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s6_risk import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Risk" in result["title"]

    def test_has_sections(self, v4_ctx):
        from txn_analysis.storylines.v4_s6_risk import run

        result = run(v4_ctx)
        assert len(result["sections"]) > 0


# ---------------------------------------------------------------------------
# S7: Campaign Effectiveness
# ---------------------------------------------------------------------------


class TestS7Campaigns:
    def test_run_without_campaign_data(self, v4_ctx):
        """S7 should return gracefully when no campaign columns exist."""
        from txn_analysis.storylines.v4_s7_campaigns import run

        result = run(v4_ctx)
        _assert_storyline_result(result)

    def test_run_with_campaign_columns(self, v4_ctx):
        """Add campaign-related columns to ODD and verify deeper execution."""
        from txn_analysis.storylines.v4_s7_campaigns import run

        # Add campaign response columns that s7 looks for
        odd = v4_ctx["odd_df"]
        n = len(odd)
        odd["Campaign Response"] = np.random.choice(["Yes", "No"], size=n)
        odd["Campaign Type"] = np.random.choice(["Email", "Mail", "Phone"], size=n)
        odd["Response Date"] = pd.date_range("2025-01-01", periods=n, freq="D")

        result = run(v4_ctx)
        _assert_storyline_result(result)


# ---------------------------------------------------------------------------
# S8: Payroll & Circular Economy
# ---------------------------------------------------------------------------


class TestS8Payroll:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s8_payroll import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Payroll" in result["title"]


# ---------------------------------------------------------------------------
# S9: Lifecycle Management
# ---------------------------------------------------------------------------


class TestS9Lifecycle:
    def test_run_returns_valid_structure(self, v4_ctx):
        from txn_analysis.storylines.v4_s9_lifecycle import run

        result = run(v4_ctx)
        _assert_storyline_result(result)
        assert "Lifecycle" in result["title"]

    def test_has_sections(self, v4_ctx):
        from txn_analysis.storylines.v4_s9_lifecycle import run

        result = run(v4_ctx)
        assert len(result["sections"]) > 0


# ---------------------------------------------------------------------------
# V4 Run Pipeline (integration-level test)
# ---------------------------------------------------------------------------


class TestV4RunPipeline:
    def test_run_constants(self):
        from txn_analysis.v4_run import ALL_STORYLINES, STORYLINE_LABELS

        assert len(ALL_STORYLINES) == 11
        assert len(STORYLINE_LABELS) == 11
        for key, label in STORYLINE_LABELS.items():
            assert key.startswith("s")
            assert isinstance(label, str)

    def test_storyline_labels_match_all(self):
        from txn_analysis.v4_run import ALL_STORYLINES, STORYLINE_LABELS

        keys = [k for k, _ in ALL_STORYLINES]
        for k in keys:
            assert k in STORYLINE_LABELS, f"Missing label for {k}"
