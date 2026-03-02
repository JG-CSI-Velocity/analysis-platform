"""Tests for M25 RFM Segmentation analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from txn_analysis.analyses.rfm import (
    _build_rfm_heatmap,
    _build_rfm_migration,
    _build_segment_distribution,
    _safe_qcut,
    _segment_rank,
    analyze_rfm,
    compute_rfm,
)
from txn_analysis.settings import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def txn_df():
    """Transaction data with enough accounts for RFM scoring."""
    rng = np.random.default_rng(42)
    n = 3000
    accounts = [f"A{i}" for i in rng.integers(0, 50, size=n)]
    dates = pd.date_range("2024-06-01", "2025-06-01", periods=n)
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
# safe_qcut
# ---------------------------------------------------------------------------

class TestSafeQcut:
    def test_produces_expected_bins(self):
        s = pd.Series(range(100))
        result = _safe_qcut(s, 4)
        assert set(result.unique()) == {1, 2, 3, 4}

    def test_handles_duplicates(self):
        s = pd.Series([1, 1, 1, 2, 2, 3, 3, 4])
        result = _safe_qcut(s, 4)
        assert len(result) == len(s)
        assert result.between(1, 4).all()


# ---------------------------------------------------------------------------
# compute_rfm
# ---------------------------------------------------------------------------

class TestComputeRFM:
    def test_returns_rfm_scores(self, txn_df):
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(txn_df, snapshot)
        assert not rfm.empty
        for col in ("r_score", "f_score", "m_score", "rfm_segment"):
            assert col in rfm.columns

    def test_scores_in_range(self, txn_df):
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(txn_df, snapshot)
        for col in ("r_score", "f_score", "m_score"):
            assert rfm[col].between(1, 4).all()

    def test_segments_are_named(self, txn_df):
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(txn_df, snapshot)
        assert rfm["rfm_segment"].notna().all()
        assert len(rfm["rfm_segment"].unique()) > 1

    def test_insufficient_data_returns_empty(self):
        small = pd.DataFrame({
            "primary_account_num": ["A1", "A2"],
            "transaction_date": ["2025-01-01", "2025-01-02"],
            "amount": [10, 20],
        })
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(small, snapshot)
        assert rfm.empty


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

class TestRFMHeatmap:
    def test_heatmap_has_scores(self, txn_df):
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(txn_df, snapshot)
        heatmap = _build_rfm_heatmap(rfm)
        assert not heatmap.empty
        assert "Recency Score" in heatmap.columns
        assert "Avg Monetary" in heatmap.columns


# ---------------------------------------------------------------------------
# Segment Distribution
# ---------------------------------------------------------------------------

class TestSegmentDistribution:
    def test_distribution_sums_to_100(self, txn_df):
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(txn_df, snapshot)
        dist = _build_segment_distribution(rfm)
        assert not dist.empty
        assert abs(dist["% of Total"].sum() - 100.0) < 0.5

    def test_has_expected_segments(self, txn_df):
        snapshot = pd.Timestamp("2025-06-01")
        rfm = compute_rfm(txn_df, snapshot)
        dist = _build_segment_distribution(rfm)
        segments = set(dist["Segment"])
        # Should have at least some common segments
        assert len(segments) >= 3


# ---------------------------------------------------------------------------
# RFM Migration
# ---------------------------------------------------------------------------

class TestRFMMigration:
    def test_migration_returns_matrix(self, txn_df):
        cutoff = pd.Timestamp("2025-01-01")
        migration = _build_rfm_migration(txn_df, cutoff)
        if migration is not None:
            assert "Pre-Mailer Segment" in migration.columns
            assert "Post-Mailer Segment" in migration.columns
            assert "Accounts" in migration.columns


# ---------------------------------------------------------------------------
# Segment ranking
# ---------------------------------------------------------------------------

class TestSegmentRank:
    def test_champions_highest(self):
        assert _segment_rank("Champions") > _segment_rank("At-Risk")

    def test_lost_lowest(self):
        assert _segment_rank("Lost") == 0

    def test_unknown_defaults_to_zero(self):
        assert _segment_rank("Nonexistent") == 0


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

class TestAnalyzeRFM:
    def test_returns_success(self, txn_df, settings):
        result = analyze_rfm(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, None
        )
        assert result.success
        assert result.metadata.get("chart_id") == "M25"

    def test_has_main_data(self, txn_df, settings):
        result = analyze_rfm(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, None
        )
        assert "main" in result.data
        assert not result.data["main"].empty

    def test_summary_populated(self, txn_df, settings):
        result = analyze_rfm(
            txn_df, pd.DataFrame(), pd.DataFrame(), settings, None
        )
        assert len(result.summary) > 0

    def test_empty_data_returns_error(self, settings):
        empty = pd.DataFrame(columns=["primary_account_num", "transaction_date", "amount"])
        result = analyze_rfm(
            empty, pd.DataFrame(), pd.DataFrame(), settings, None
        )
        assert result.error is not None
