"""Tests for shared.types module."""

from pathlib import Path

import pandas as pd
import pytest

from shared.types import AnalysisResult


class TestAnalysisResult:
    def test_create_with_name_only(self):
        r = AnalysisResult(name="test")
        assert r.name == "test"
        assert r.data == {}
        assert r.charts == []
        assert r.summary == ""
        assert r.metadata == {}

    def test_create_with_all_fields(self):
        df = pd.DataFrame({"a": [1, 2]})
        r = AnalysisResult(
            name="full",
            data={"main": df},
            charts=[Path("chart.png")],
            summary="A test result",
            metadata={"count": 42},
        )
        assert r.name == "full"
        assert "main" in r.data
        assert len(r.charts) == 1
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
