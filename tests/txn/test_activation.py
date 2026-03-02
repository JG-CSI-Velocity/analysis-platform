"""Tests for M24 Activation & Dormancy analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from txn_analysis.analyses.activation import (
    _build_activation_summary,
    _build_dormancy_summary,
    _compute_activation,
    _compute_dormancy,
    _compute_reactivation,
    analyze_activation,
)
from txn_analysis.settings import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def odd_df():
    """ODD with Date Opened for activation testing."""
    return pd.DataFrame({
        "Acct Number": [f"A{i}" for i in range(15)],
        "Date Opened": pd.to_datetime([
            "2024-01-15", "2024-02-20", "2024-03-10",
            "2024-04-05", "2024-05-01", "2024-06-15",
            "2024-07-20", "2024-08-10", "2024-09-01",
            "2024-10-15", "2024-11-01", "2024-12-10",
            "2025-01-05", "2025-02-01", "2025-03-15",
        ]),
    })


@pytest.fixture()
def txn_df():
    """Transaction data with mixed activity levels."""
    rng = np.random.default_rng(42)
    # Some accounts active, some dormant, some sporadic
    rows: list[dict] = []
    for i in range(15):
        n_txns = rng.integers(0, 30)
        if i >= 12:
            n_txns = max(n_txns, 5)  # newer accounts have some activity
        for _ in range(n_txns):
            days_offset = rng.integers(0, 365)
            rows.append({
                "primary_account_num": f"A{i}",
                "transaction_date": pd.Timestamp("2024-06-01") + pd.Timedelta(days=int(days_offset)),
                "amount": float(rng.uniform(5, 300)),
                "merchant_name": "Store",
                "business_flag": "No",
            })
    # Ensure at least some data
    if not rows:
        rows.append({
            "primary_account_num": "A0",
            "transaction_date": pd.Timestamp("2024-06-15"),
            "amount": 50.0,
            "merchant_name": "Store",
            "business_flag": "No",
        })
    return pd.DataFrame(rows)


@pytest.fixture()
def settings(tmp_path):
    return Settings(output_dir=tmp_path)


# ---------------------------------------------------------------------------
# Dormancy
# ---------------------------------------------------------------------------

class TestDormancy:
    def test_dormancy_returns_statuses(self, txn_df):
        dormancy = _compute_dormancy(txn_df)
        assert not dormancy.empty
        assert "status" in dormancy.columns
        valid_statuses = {"Active", "At-Risk", "Dormant", "Lost"}
        assert set(dormancy["status"].unique()) <= valid_statuses

    def test_dormancy_days_since_non_negative(self, txn_df):
        dormancy = _compute_dormancy(txn_df)
        assert (dormancy["days_since"] >= 0).all()

    def test_dormancy_summary_sums_to_total(self, txn_df):
        dormancy = _compute_dormancy(txn_df)
        summary = _build_dormancy_summary(dormancy)
        assert not summary.empty
        assert abs(summary["% of Total"].sum() - 100.0) < 0.5

    def test_dormancy_empty_input(self):
        empty = pd.DataFrame(columns=["primary_account_num", "transaction_date", "amount"])
        result = _compute_dormancy(empty)
        assert result.empty


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------

class TestActivation:
    def test_activation_returns_days(self, txn_df, odd_df):
        activation = _compute_activation(txn_df, odd_df, "Acct Number")
        if not activation.empty:
            assert "days_to_activation" in activation.columns
            assert (activation["days_to_activation"] >= 0).all()

    def test_activation_summary_has_buckets(self, txn_df, odd_df):
        activation = _compute_activation(txn_df, odd_df, "Acct Number")
        if not activation.empty:
            summary = _build_activation_summary(activation)
            assert not summary.empty
            assert "Activation Window" in summary.columns
            assert "Cumulative %" in summary.columns

    def test_activation_cumulative_reaches_100(self, txn_df, odd_df):
        activation = _compute_activation(txn_df, odd_df, "Acct Number")
        if not activation.empty:
            summary = _build_activation_summary(activation)
            if not summary.empty:
                last_cum = summary.iloc[-1]["Cumulative %"]
                assert abs(last_cum - 100.0) < 0.5


# ---------------------------------------------------------------------------
# Reactivation
# ---------------------------------------------------------------------------

class TestReactivation:
    def test_reactivation_has_columns(self, txn_df):
        reactivation = _compute_reactivation(txn_df)
        if not reactivation.empty:
            for col in ("Month", "Active", "New", "Reactivated", "Went Dormant"):
                assert col in reactivation.columns

    def test_reactivation_first_month_no_reactivations(self, txn_df):
        reactivation = _compute_reactivation(txn_df)
        if not reactivation.empty:
            assert reactivation.iloc[0]["Reactivated"] == 0


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

class TestAnalyzeActivation:
    def test_without_odd_still_has_dormancy(self, txn_df, settings):
        result = analyze_activation(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, None
        )
        assert result.success
        assert "dormancy" in result.data or "main" in result.data

    def test_with_odd_has_activation(self, txn_df, odd_df, settings):
        context = {"odd_df": odd_df}
        result = analyze_activation(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, context
        )
        assert result.success
        assert result.metadata.get("chart_id") == "M24"

    def test_summary_has_content(self, txn_df, odd_df, settings):
        context = {"odd_df": odd_df}
        result = analyze_activation(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, context
        )
        assert len(result.summary) > 0
