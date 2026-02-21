"""Tests for M6B-7 discover unmatched financial merchants."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.discover_unmatched_financial import analyze_unmatched_financial
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(output_dir="/tmp/test")


def _make_df(
    merchants: list[str],
    mcc_codes: list[str] | None = None,
    amounts: list[float] | None = None,
) -> pd.DataFrame:
    n = len(merchants)
    return pd.DataFrame(
        {
            "merchant_name": merchants,
            "mcc_code": mcc_codes or ["9999"] * n,
            "amount": amounts or [100.0] * n,
            "primary_account_num": [f"ACCT{i}" for i in range(n)],
            "business_flag": ["No"] * n,
        }
    )


class TestDiscoverUnmatchedFinancial:
    def test_no_mcc_column_returns_empty(self):
        df = pd.DataFrame({"merchant_name": ["SOME MERCHANT"], "amount": [100.0]})
        result = analyze_unmatched_financial(df, df, df, _settings())
        assert result.df.empty

    def test_financial_mcc_not_in_competitors_found(self):
        df = _make_df(["UNKNOWN FI CORP"], mcc_codes=["6011"])
        result = analyze_unmatched_financial(df, df, df, _settings())
        assert not result.df.empty
        assert "UNKNOWN FI CORP" in result.df["merchant_name"].str.upper().values

    def test_already_classified_excluded(self):
        df = _make_df(["CHASE BANK NA"], mcc_codes=["6011"])
        ctx = {
            "competitor_data": {"CHASE BANK": pd.DataFrame({"merchant_name": ["CHASE BANK NA"]})}
        }
        result = analyze_unmatched_financial(df, df, df, _settings(), ctx)
        assert result.df.empty

    def test_non_financial_mcc_excluded(self):
        df = _make_df(["RANDOM MERCHANT"], mcc_codes=["5411"])
        result = analyze_unmatched_financial(df, df, df, _settings())
        assert result.df.empty

    def test_summary_columns(self):
        df = _make_df(["NEW FI SERVICE"], mcc_codes=["6012"])
        result = analyze_unmatched_financial(df, df, df, _settings())
        expected = {
            "merchant_name",
            "mcc_code",
            "total_transactions",
            "unique_accounts",
            "total_amount",
        }
        assert expected.issubset(set(result.df.columns))

    def test_sorted_by_amount_descending(self):
        df = _make_df(
            ["FI ALPHA", "FI BETA", "FI GAMMA"],
            mcc_codes=["6011", "6012", "6050"],
            amounts=[100.0, 500.0, 200.0],
        )
        result = analyze_unmatched_financial(df, df, df, _settings())
        amounts = result.df["total_amount"].tolist()
        assert amounts == sorted(amounts, reverse=True)
