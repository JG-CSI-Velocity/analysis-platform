"""Tests for txn_analysis.segment_runner -- segmented analysis execution."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.segment_runner import (
    SegmentedResult,
    _tag_result,
    run_segmented_analyses,
)
from txn_analysis.segments import SegmentFilter
from txn_analysis.settings import Settings


def _make_txn_df(accts: list[str], n_per_acct: int = 3) -> pd.DataFrame:
    """Build a synthetic transaction DataFrame."""
    rows = []
    for acct in accts:
        for i in range(n_per_acct):
            rows.append(
                {
                    "primary_account_num": acct,
                    "merchant_name": f"Merchant_{i}",
                    "amount": 100.0 * (i + 1),
                    "year_month": "2025-01",
                    "business_flag": "No",
                }
            )
    return pd.DataFrame(rows)


def _fake_run_all(df, settings, odd_df=None, on_progress=None):
    """Fake run_all_analyses that returns one result per unique account."""
    n_accts = df["primary_account_num"].nunique()
    return [
        AnalysisResult.from_df(
            "test_analysis",
            "Test Analysis",
            pd.DataFrame({"count": [n_accts]}),
        )
    ]


class TestSegmentedResult:
    def test_frozen_dataclass(self):
        sr = SegmentedResult(
            segment="test",
            label="Test",
            analyses=[],
            account_count=10,
            transaction_count=30,
        )
        assert sr.segment == "test"
        assert sr.account_count == 10


class TestTagResult:
    def test_tags_name_and_title(self):
        result = AnalysisResult.from_df("top_by_spend", "Top by Spend", pd.DataFrame())
        tagged = _tag_result(result, "ARS Responders")
        assert tagged.name == "top_by_spend__ars_responders"
        assert tagged.title == "[ARS Responders] Top by Spend"

    def test_preserves_data(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = AnalysisResult.from_df("test", "Test", df)
        tagged = _tag_result(result, "ICS Account Holders")
        assert len(tagged.df) == 3

    def test_adds_segment_metadata(self):
        result = AnalysisResult.from_df("test", "Test", pd.DataFrame())
        tagged = _tag_result(result, "ARS Responders")
        assert tagged.metadata["segment"] == "ARS Responders"

    def test_empty_title_unchanged(self):
        result = AnalysisResult(name="test", title="")
        tagged = _tag_result(result, "Seg")
        assert tagged.title == ""


class TestRunSegmentedAnalyses:
    @patch("txn_analysis.segment_runner.run_all_analyses", side_effect=_fake_run_all)
    def test_full_population_always_first(self, mock_run):
        df = _make_txn_df(["1001", "1002", "1003"])
        settings = Settings(data_file=None, output_dir="/tmp/test")
        results = run_segmented_analyses(df, settings, odd_df=None, segments=[])
        assert len(results) == 1
        assert results[0].segment == "full_population"
        assert results[0].transaction_count == 9

    @patch("txn_analysis.segment_runner.run_all_analyses", side_effect=_fake_run_all)
    def test_with_one_segment(self, mock_run):
        df = _make_txn_df(["1001", "1002", "1003"])
        seg = SegmentFilter(
            name="ars_responders",
            label="ARS Responders",
            account_numbers=frozenset({"1001", "1003"}),
        )
        settings = Settings(data_file=None, output_dir="/tmp/test")
        results = run_segmented_analyses(df, settings, odd_df=None, segments=[seg])
        assert len(results) == 2
        assert results[0].segment == "full_population"
        assert results[1].segment == "ars_responders"
        assert results[1].transaction_count == 6
        assert results[1].account_count == 2
        # Verify segment analyses are tagged
        assert results[1].analyses[0].name == "test_analysis__ars_responders"

    @patch("txn_analysis.segment_runner.run_all_analyses", side_effect=_fake_run_all)
    def test_with_two_segments(self, mock_run):
        df = _make_txn_df(["1001", "1002", "1003"])
        segs = [
            SegmentFilter("ars_responders", "ARS Responders", frozenset({"1001"})),
            SegmentFilter("ics_accounts", "ICS Account Holders", frozenset({"1002", "1003"})),
        ]
        settings = Settings(data_file=None, output_dir="/tmp/test")
        results = run_segmented_analyses(df, settings, odd_df=None, segments=segs)
        assert len(results) == 3
        labels = [r.label for r in results]
        assert labels == ["Full Population", "ARS Responders", "ICS Account Holders"]

    @patch("txn_analysis.segment_runner.run_all_analyses", side_effect=_fake_run_all)
    def test_empty_segment_skipped(self, mock_run):
        df = _make_txn_df(["1001", "1002"])
        seg = SegmentFilter(
            name="empty",
            label="Empty Segment",
            account_numbers=frozenset({"9999"}),
        )
        settings = Settings(data_file=None, output_dir="/tmp/test")
        results = run_segmented_analyses(df, settings, odd_df=None, segments=[seg])
        # Only full population -- empty segment skipped
        assert len(results) == 1
        assert results[0].segment == "full_population"

    @patch("txn_analysis.segment_runner.run_all_analyses", side_effect=_fake_run_all)
    def test_account_count_from_segment(self, mock_run):
        df = _make_txn_df(["1001", "1002", "1003"])
        seg = SegmentFilter(
            name="test",
            label="Test",
            account_numbers=frozenset({"1001", "1002"}),
        )
        settings = Settings(data_file=None, output_dir="/tmp/test")
        results = run_segmented_analyses(df, settings, odd_df=None, segments=[seg])
        full = results[0]
        segment = results[1]
        assert full.account_count == 3
        assert segment.account_count == 2
