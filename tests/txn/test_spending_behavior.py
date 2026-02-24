"""Tests for M17: Spending behavior by demographics and response timing."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.spending_behavior import (
    _build_age_group_spending,
    _build_branch_spending,
    _build_response_month_velocity,
    _detect_acct_col,
    _detect_resp_pairs,
    analyze_spending_behavior,
)
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test")


def _make_odd(
    accounts: list[str],
    ages: list[int] | None = None,
    branches: list[str] | None = None,
    mail_months: list[str] | None = None,
    responders: set[str] | None = None,
) -> pd.DataFrame:
    """Build a synthetic ODD DataFrame."""
    rows = []
    for i, acct in enumerate(accounts):
        row: dict = {"Account Number": acct}
        if ages:
            row["Account Holder Age"] = ages[i % len(ages)]
        if branches:
            row["Branch"] = branches[i % len(branches)]
        if mail_months:
            for m in mail_months:
                row[f"{m} Mail"] = "TH-10"
                if responders and acct in responders:
                    row[f"{m} Resp"] = "TH-10"
                else:
                    row[f"{m} Resp"] = ""
        rows.append(row)
    return pd.DataFrame(rows)


def _make_txns(
    accounts: list[str],
    dates: list[str],
    amount: float = 25.0,
) -> pd.DataFrame:
    """Build synthetic transaction DataFrame."""
    rows = []
    for acct in accounts:
        for date in dates:
            rows.append({
                "primary_account_num": acct,
                "merchant_consolidated": "STORE",
                "merchant_name": "STORE",
                "amount": amount,
                "transaction_date": date,
                "year_month": date[:7],
                "business_flag": "No",
            })
    return pd.DataFrame(rows)


class TestDetectAcctCol:
    def test_standard_col(self):
        df = pd.DataFrame({"Account Number": [1], "Balance": [100]})
        assert _detect_acct_col(df) == "Account Number"

    def test_alt_col(self):
        df = pd.DataFrame({"Acct Number": [1]})
        assert _detect_acct_col(df) == "Acct Number"

    def test_missing(self):
        df = pd.DataFrame({"ID": [1]})
        assert _detect_acct_col(df) is None


class TestDetectRespPairs:
    def test_finds_pairs(self):
        df = pd.DataFrame({
            "Account Number": ["1001"],
            "Apr24 Mail": ["TH-10"],
            "Apr24 Resp": ["TH-10"],
            "May24 Mail": ["TH-15"],
            "May24 Resp": [""],
        })
        pairs = _detect_resp_pairs(df)
        assert len(pairs) == 2
        assert pairs[0][0] == "Apr24"
        assert pairs[1][0] == "May24"

    def test_no_pairs(self):
        df = pd.DataFrame({"Account Number": ["1001"], "Balance": [100]})
        assert _detect_resp_pairs(df) == []


class TestResponseMonthVelocity:
    def test_responders_vs_non_responders(self):
        odd = _make_odd(
            accounts=["1001", "1002"],
            mail_months=["Jan25"],
            responders={"1001"},
        )
        # 1001 (responder) swipes early; 1002 (non-responder) swipes late
        txns = pd.DataFrame([
            {"primary_account_num": "1001", "transaction_date": "2025-01-05",
             "amount": 50, "year_month": "2025-01", "business_flag": "No",
             "merchant_consolidated": "X", "merchant_name": "X"},
            {"primary_account_num": "1002", "transaction_date": "2025-01-25",
             "amount": 50, "year_month": "2025-01", "business_flag": "No",
             "merchant_consolidated": "X", "merchant_name": "X"},
        ])
        pairs = _detect_resp_pairs(odd)
        result = _build_response_month_velocity(txns, odd, "Account Number", pairs)
        assert not result.empty
        assert len(result) == 2
        resp_row = result[result["Segment"] == "Responders"].iloc[0]
        non_resp_row = result[result["Segment"] == "Non-Responders"].iloc[0]
        # Responder swiped on day 5 (early), non-responder on day 25 (late)
        assert resp_row["Avg Day of Month"] < non_resp_row["Avg Day of Month"]
        assert resp_row["% in First 10 Days"] == 100.0

    def test_no_response_cols(self):
        odd = pd.DataFrame({"Account Number": ["1001"], "Balance": [100]})
        txns = _make_txns(["1001"], ["2025-01-15"])
        result = _build_response_month_velocity(txns, odd, "Account Number", [])
        assert result.empty


class TestAgeGroupSpending:
    def test_age_buckets(self):
        odd = _make_odd(["1001", "1002", "1003"], ages=[22, 40, 60])
        txns = _make_txns(["1001", "1002", "1003"], ["2025-01-15"])
        result = _build_age_group_spending(txns, odd, "Account Number")
        assert not result.empty
        assert "18-25" in result["Age Group"].values
        assert "36-45" in result["Age Group"].values
        assert "56-65" in result["Age Group"].values

    def test_no_age_column(self):
        odd = pd.DataFrame({"Account Number": ["1001"]})
        txns = _make_txns(["1001"], ["2025-01-15"])
        result = _build_age_group_spending(txns, odd, "Account Number")
        assert result.empty

    def test_pct_of_spend_sums_to_100(self):
        odd = _make_odd(["1001", "1002"], ages=[25, 55])
        txns = _make_txns(["1001", "1002"], ["2025-01-15"])
        result = _build_age_group_spending(txns, odd, "Account Number")
        assert abs(result["% of Spend"].sum() - 100.0) < 0.2


class TestBranchSpending:
    def test_branch_breakdown(self):
        odd = _make_odd(["1001", "1002"], branches=["Main", "West"])
        txns = _make_txns(["1001", "1002"], ["2025-01-15"])
        result = _build_branch_spending(txns, odd, "Account Number")
        assert not result.empty
        assert len(result) == 2
        assert "Main" in result["Branch"].values
        assert "West" in result["Branch"].values

    def test_no_branch_column(self):
        odd = pd.DataFrame({"Account Number": ["1001"]})
        txns = _make_txns(["1001"], ["2025-01-15"])
        result = _build_branch_spending(txns, odd, "Account Number")
        assert result.empty


class TestAnalyzeSpendingBehavior:
    def test_no_odd_graceful(self):
        txns = _make_txns(["1001"], ["2025-01-15"])
        result = analyze_spending_behavior(txns, txns, txns, _settings())
        assert result.error is None
        assert "Note" in result.df.columns

    def test_with_odd(self):
        odd = _make_odd(
            ["1001", "1002"],
            ages=[30, 50],
            branches=["Main", "West"],
            mail_months=["Jan25"],
            responders={"1001"},
        )
        txns = _make_txns(["1001", "1002"], ["2025-01-15", "2025-01-20"])
        ctx: dict = {"odd_df": odd, "completed_results": {}}
        result = analyze_spending_behavior(txns, txns, txns, _settings(), context=ctx)
        assert result.error is None
        assert result.metadata["sheet_name"] == "M17 Behavior"
        # Should have multiple data sheets
        assert len(result.data) >= 2

    def test_summary_mentions_age(self):
        odd = _make_odd(["1001"], ages=[35])
        txns = _make_txns(["1001"], ["2025-01-15"])
        ctx: dict = {"odd_df": odd, "completed_results": {}}
        result = analyze_spending_behavior(txns, txns, txns, _settings(), context=ctx)
        assert "age group" in result.summary.lower() or "Age Group" in result.summary

    def test_empty_odd(self):
        txns = _make_txns(["1001"], ["2025-01-15"])
        ctx: dict = {"odd_df": pd.DataFrame(), "completed_results": {}}
        result = analyze_spending_behavior(txns, txns, txns, _settings(), context=ctx)
        assert "Note" in result.df.columns
