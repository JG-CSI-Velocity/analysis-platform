"""Tests for shared.types module."""

from pathlib import Path

import pandas as pd
import pytest

from shared.types import AnalysisResult


class TestAnalysisResult:
    def test_create_with_name_only(self):
        r = AnalysisResult(name="test")
        assert r.name == "test"
        assert r.title == ""
        assert r.data == {}
        assert r.charts == []
        assert r.error is None
        assert r.summary == ""
        assert r.metadata == {}

    def test_create_with_all_fields(self):
        df = pd.DataFrame({"a": [1, 2]})
        r = AnalysisResult(
            name="full",
            title="Full Test",
            data={"main": df},
            charts=[Path("chart.png")],
            error=None,
            summary="A test result",
            metadata={"count": 42},
        )
        assert r.name == "full"
        assert r.title == "Full Test"
        assert "main" in r.data
        assert len(r.charts) == 1
        assert r.error is None
        assert r.summary == "A test result"
        assert r.metadata["count"] == 42

    def test_immutable(self):
        r = AnalysisResult(name="frozen")
        with pytest.raises(AttributeError):
            r.name = "changed"

    def test_data_dict_is_independent(self):
        r1 = AnalysisResult(name="a")
        r2 = AnalysisResult(name="b")
        assert r1.data is not r2.data

    def test_charts_list_is_independent(self):
        r1 = AnalysisResult(name="a")
        r2 = AnalysisResult(name="b")
        assert r1.charts is not r2.charts


class TestAnalysisResultProperties:
    def test_success_true_when_no_error(self):
        r = AnalysisResult(name="ok")
        assert r.success is True

    def test_success_false_when_error(self):
        r = AnalysisResult(name="fail", error="something broke")
        assert r.success is False

    def test_df_returns_main_dataframe(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        r = AnalysisResult(name="t", data={"main": df})
        assert r.df.equals(df)

    def test_df_returns_empty_when_no_main(self):
        r = AnalysisResult(name="t", data={"other": pd.DataFrame({"a": [1]})})
        assert r.df.empty

    def test_df_returns_empty_when_no_data(self):
        r = AnalysisResult(name="t")
        assert r.df.empty

    def test_sheet_name_from_metadata(self):
        r = AnalysisResult(name="t", metadata={"sheet_name": "custom_sheet"})
        assert r.sheet_name == "custom_sheet"

    def test_sheet_name_derived_from_name(self):
        r = AnalysisResult(name="top merchants by spend")
        assert r.sheet_name == "top_merchants_by_spend"

    def test_sheet_name_truncated_to_31(self):
        r = AnalysisResult(name="a" * 50)
        assert len(r.sheet_name) == 31


class TestFromDf:
    def test_basic(self):
        df = pd.DataFrame({"a": [1]})
        r = AnalysisResult.from_df("test", "Test Title", df)
        assert r.name == "test"
        assert r.title == "Test Title"
        assert r.df.equals(df)
        assert r.sheet_name == "test"
        assert r.error is None

    def test_with_sheet_name(self):
        df = pd.DataFrame({"a": [1]})
        r = AnalysisResult.from_df("test", "Test", df, sheet_name="my_sheet")
        assert r.sheet_name == "my_sheet"

    def test_with_error(self):
        df = pd.DataFrame()
        r = AnalysisResult.from_df("test", "Test", df, error="bad data")
        assert r.error == "bad data"
        assert r.success is False

    def test_with_metadata(self):
        df = pd.DataFrame({"a": [1]})
        r = AnalysisResult.from_df("test", "Test", df, metadata={"extra": 42})
        assert r.metadata["extra"] == 42
        assert "sheet_name" in r.metadata

    def test_none_df(self):
        r = AnalysisResult.from_df("test", "Test", None)
        assert r.data == {}
        assert r.df.empty
