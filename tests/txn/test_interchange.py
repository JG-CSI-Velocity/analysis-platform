"""Tests for M8: Interchange revenue estimation."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.interchange import analyze_interchange_summary
from txn_analysis.settings import Settings


def _settings(ic_rate: float = 0.015) -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test", ic_rate=ic_rate)


def _make_df(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "primary_account_num": [f"ACCT{i % 3:03d}" for i in range(n)],
            "amount": [100.0 + i * 10 for i in range(n)],
            "merchant_consolidated": [f"Merch{i % 5}" for i in range(n)],
            "mcc_code": [f"MCC{i % 4}" for i in range(n)],
            "year_month": [f"2025-{(i % 3) + 7:02d}" for i in range(n)],
            "business_flag": ["Yes" if i % 3 == 0 else "No" for i in range(n)],
        }
    )


class TestInterchangeSummary:
    def test_basic_result(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_interchange_summary(df, biz, per, _settings())
        assert result.error is None
        assert not result.df.empty

    def test_sections_present(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_interchange_summary(df, biz, per, _settings())
        sections = set(result.df["section"])
        assert "Portfolio" in sections
        assert "Segment" in sections
        assert "Top Merchants" in sections

    def test_ic_revenue_calculation(self):
        df = _make_df(5)
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        total_spend = df["amount"].sum()
        ic_rate = 0.015
        result = analyze_interchange_summary(df, biz, per, _settings(ic_rate))
        portfolio = result.df[result.df["section"] == "Portfolio"]
        expected = round(total_spend * ic_rate, 2)
        assert portfolio.iloc[0]["estimated_ic_revenue"] == expected

    def test_context_populated(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        ctx: dict = {}
        analyze_interchange_summary(df, biz, per, _settings(), context=ctx)
        assert "interchange_summary" in ctx
        assert ctx["interchange_summary"]["total_ic_revenue"] > 0
        assert ctx["interchange_summary"]["ic_rate"] == 0.015

    def test_zero_ic_rate(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_interchange_summary(df, biz, per, _settings(ic_rate=0.0))
        assert result.df.empty

    def test_empty_df(self):
        empty = pd.DataFrame()
        result = analyze_interchange_summary(empty, empty, empty, _settings())
        assert result.df.empty

    def test_monthly_trend(self):
        df = _make_df(30)
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_interchange_summary(df, biz, per, _settings())
        monthly = result.df[result.df["section"] == "Monthly"]
        assert len(monthly) > 0

    def test_metadata(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_interchange_summary(df, biz, per, _settings())
        assert result.metadata["ic_rate"] == 0.015
        assert result.metadata["total_ic_revenue"] > 0
