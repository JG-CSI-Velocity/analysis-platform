"""Tests for M9: Portfolio health scorecard."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.scorecard import PULSE_2024_BENCHMARKS, analyze_portfolio_scorecard
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test", ic_rate=0.015)


def _make_df(n: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "primary_account_num": [f"ACCT{i % 5:03d}" for i in range(n)],
            "amount": [50.0 + i * 5 for i in range(n)],
            "merchant_consolidated": [f"Merch{i % 8}" for i in range(n)],
            "year_month": [f"2025-{(i % 3) + 7:02d}" for i in range(n)],
            "business_flag": ["Yes" if i % 4 == 0 else "No" for i in range(n)],
            "transaction_date": [f"2025-{(i % 3) + 7:02d}-{(i % 28) + 1:02d}" for i in range(n)],
        }
    )


class TestPortfolioScorecard:
    def test_basic_result(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_portfolio_scorecard(df, biz, per, _settings())
        assert result.error is None
        assert not result.df.empty

    def test_kpi_count(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_portfolio_scorecard(df, biz, per, _settings())
        assert len(result.df) >= 10  # 10+ KPIs

    def test_kpi_metrics_present(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_portfolio_scorecard(df, biz, per, _settings())
        metrics = set(result.df["metric"])
        assert "Active Accounts" in metrics
        assert "Average Ticket" in metrics
        assert "Business Spend %" in metrics

    def test_benchmark_status(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_portfolio_scorecard(df, biz, per, _settings())
        benchmarked = result.df[result.df["benchmark"] != ""]
        assert len(benchmarked) > 0
        assert set(benchmarked["status"]) <= {"Above", "At", "Below", ""}

    def test_reads_interchange_context(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        ctx: dict = {
            "interchange_summary": {
                "total_ic_revenue": 5000.0,
                "ic_rate": 0.015,
            },
            "completed_results": {},
        }
        result = analyze_portfolio_scorecard(df, biz, per, _settings(), context=ctx)
        ic_row = result.df[result.df["metric"] == "Est. Annual Interchange Revenue"]
        assert len(ic_row) == 1
        assert ic_row.iloc[0]["value"] > 0

    def test_reads_member_segments_context(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        ctx: dict = {
            "interchange_summary": {},
            "member_segments": {
                "total_accounts": 5,
                "segment_counts": {"High Value": 2, "Active": 2, "Dormant": 1},
                "dormant_count": 1,
            },
            "completed_results": {},
        }
        result = analyze_portfolio_scorecard(df, biz, per, _settings(), context=ctx)
        dormant_row = result.df[result.df["metric"] == "Dormant Accounts (90+ days)"]
        assert len(dormant_row) == 1
        assert dormant_row.iloc[0]["value"] == 1

    def test_empty_df(self):
        empty = pd.DataFrame()
        result = analyze_portfolio_scorecard(empty, empty, empty, _settings())
        assert result.df.empty

    def test_pulse_benchmarks_exist(self):
        assert "annual_spend_per_card" in PULSE_2024_BENCHMARKS
        assert "txn_per_card_month" in PULSE_2024_BENCHMARKS
        assert "avg_ticket" in PULSE_2024_BENCHMARKS

    def test_metadata(self):
        df = _make_df()
        biz = df[df["business_flag"] == "Yes"]
        per = df[df["business_flag"] == "No"]
        result = analyze_portfolio_scorecard(df, biz, per, _settings())
        assert result.metadata["benchmark_source"] == "PULSE 2024 Debit Issuer Study"
        assert result.metadata["months_in_data"] > 0
