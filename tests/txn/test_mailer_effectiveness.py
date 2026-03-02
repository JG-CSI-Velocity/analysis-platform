"""Tests for M23 Mailer Effectiveness (DiD, ITS, decay, lift)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from txn_analysis.analyses.mailer_effectiveness import (
    _build_monthly_spend,
    _classify_accounts,
    _compute_cumulative_incremental,
    _compute_decay,
    _compute_did,
    _compute_did_by_segment,
    _compute_its,
    _compute_lift_distribution,
    _split_pre_post,
    analyze_mailer_effectiveness,
)
from txn_analysis.settings import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def odd_df():
    """ODD with 2 mailer months, responders + non-responders."""
    return pd.DataFrame({
        "Acct Number": [f"A{i}" for i in range(20)],
        "Jan25 Mail": ["NU"] * 20,
        "Jan25 Resp": (
            ["TH-10"] * 5 + ["NU 5+"] * 3 + [None] * 12
        ),
        "Feb25 Mail": ["NU"] * 20,
        "Feb25 Resp": (
            ["TH-15"] * 3 + ["TH-10"] * 4 + [None] * 13
        ),
        "balance_tier": (
            ["High"] * 5 + ["Medium"] * 5 + ["Low"] * 10
        ),
    })


@pytest.fixture()
def txn_df():
    """Transaction data spanning Aug 2024 - Jun 2025."""
    rng = np.random.default_rng(42)
    n = 2000
    accounts = [f"A{i}" for i in rng.integers(0, 20, size=n)]
    dates = pd.date_range("2024-08-01", "2025-06-30", periods=n)
    amounts = rng.uniform(5, 500, size=n)
    return pd.DataFrame({
        "primary_account_num": accounts,
        "transaction_date": dates,
        "amount": amounts,
        "merchant_name": ["Store"] * n,
        "business_flag": ["No"] * n,
    })


@pytest.fixture()
def settings(tmp_path):
    return Settings(output_dir=tmp_path)


# ---------------------------------------------------------------------------
# classify_accounts
# ---------------------------------------------------------------------------

class TestClassifyAccounts:
    def test_splits_responders_and_non_responders(self, odd_df):
        pairs = [
            ("Jan25", "Jan25 Resp", "Jan25 Mail"),
            ("Feb25", "Feb25 Resp", "Feb25 Mail"),
        ]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        assert len(resp) > 0
        assert len(non_resp) > 0
        assert resp.isdisjoint(non_resp)

    def test_earliest_date_detected(self, odd_df):
        pairs = [
            ("Jan25", "Jan25 Resp", "Jan25 Mail"),
            ("Feb25", "Feb25 Resp", "Feb25 Mail"),
        ]
        _, _, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        assert earliest is not None
        assert earliest.month == 1
        assert earliest.year == 2025


# ---------------------------------------------------------------------------
# build_monthly_spend
# ---------------------------------------------------------------------------

class TestBuildMonthlySpend:
    def test_returns_grouped_spend(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, _ = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        assert not monthly.empty
        assert "group" in monthly.columns
        assert set(monthly["group"].unique()) <= {"Responder", "Non-Responder"}

    def test_has_required_columns(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, _ = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        for col in ("account", "year_month", "spend", "txn_count", "group"):
            assert col in monthly.columns


# ---------------------------------------------------------------------------
# DiD
# ---------------------------------------------------------------------------

class TestDiD:
    def test_did_returns_required_keys(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        pre, post = _split_pre_post(monthly, earliest, 6, 6)
        did = _compute_did(pre, post)
        assert "did_estimate" in did
        assert "did_pct" in did
        assert "resp_pre_avg" in did

    def test_did_table_has_4_rows(self, txn_df, odd_df):
        from txn_analysis.analyses.mailer_effectiveness import _build_did_table
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        pre, post = _split_pre_post(monthly, earliest, 6, 6)
        did = _compute_did(pre, post)
        table = _build_did_table(did)
        assert len(table) == 4

    def test_did_by_segment_returns_tiers(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        seg_df = _compute_did_by_segment(monthly, earliest, odd_df, "Acct Number", 6, 6)
        if not seg_df.empty:
            assert "Balance Tier" in seg_df.columns
            assert "DiD Estimate" in seg_df.columns


# ---------------------------------------------------------------------------
# ITS
# ---------------------------------------------------------------------------

class TestITS:
    def test_its_returns_columns(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        its = _compute_its(monthly, earliest)
        if not its.empty:
            for col in ("Month", "actual_spend", "counterfactual"):
                assert col in its.columns

    def test_its_counterfactual_extends(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        its = _compute_its(monthly, earliest)
        if not its.empty:
            assert its["counterfactual"].notna().all()


# ---------------------------------------------------------------------------
# Effect Decay
# ---------------------------------------------------------------------------

class TestDecay:
    def test_decay_has_lift_column(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        decay = _compute_decay(monthly, earliest, 6)
        if not decay.empty:
            assert "Lift" in decay.columns

    def test_decay_months_post_mailer(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        decay = _compute_decay(monthly, earliest, 6)
        if not decay.empty:
            assert decay["Months Post-Mailer"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# Cumulative Incremental
# ---------------------------------------------------------------------------

class TestCumulativeIncremental:
    def test_cumulative_is_monotonic_direction(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        cum = _compute_cumulative_incremental(monthly, earliest, 6)
        if not cum.empty:
            assert "Cumulative Incremental" in cum.columns
            # Last value should be sum of all incrementals
            assert abs(cum.iloc[-1]["Cumulative Incremental"] - cum["Incremental"].sum()) < 0.1


# ---------------------------------------------------------------------------
# Lift Distribution
# ---------------------------------------------------------------------------

class TestLiftDistribution:
    def test_lift_has_group_column(self, txn_df, odd_df):
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        resp, non_resp, earliest = _classify_accounts(odd_df, "Acct Number", pairs)
        monthly = _build_monthly_spend(txn_df, resp, non_resp)
        lift = _compute_lift_distribution(monthly, earliest, 6, 6, 1)
        if not lift.empty:
            assert "group" in lift.columns
            assert "lift" in lift.columns


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

class TestAnalyzeMailerEffectiveness:
    def test_without_odd_returns_note(self, txn_df, settings):
        result = analyze_mailer_effectiveness(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, None
        )
        assert result.success
        assert "ODD data required" in result.df.iloc[0, 0]

    def test_with_odd_returns_did(self, txn_df, odd_df, settings):
        context = {"odd_df": odd_df}
        result = analyze_mailer_effectiveness(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, context
        )
        assert result.success
        assert result.metadata.get("chart_id") == "M23"
        assert result.metadata.get("n_responders", 0) > 0

    def test_summary_has_content(self, txn_df, odd_df, settings):
        context = {"odd_df": odd_df}
        result = analyze_mailer_effectiveness(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, context
        )
        assert len(result.summary) > 0

    def test_data_keys(self, txn_df, odd_df, settings):
        context = {"odd_df": odd_df}
        result = analyze_mailer_effectiveness(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, context
        )
        assert "main" in result.data
        assert "did_raw" in result.data
