"""Tests for ars_analysis.runner."""

from ars_analysis.runner import _build_base_paths, _extract_dataframes, _is_dataframe
from shared.context import PipelineContext


class TestBuildBasePaths:
    def test_with_output_dir(self):
        from pathlib import Path

        ctx = PipelineContext(output_dir=Path("/tmp/test"))
        result = _build_base_paths(ctx)
        assert result is not None
        assert "presentations" in result
        assert "archive" in result


class TestExtractDataframes:
    def test_extracts_dfs(self):
        import pandas as pd

        d = {
            "df1": pd.DataFrame({"a": [1]}),
            "metric": 42,
            "text": "hello",
        }
        result = _extract_dataframes(d)
        assert "df1" in result
        assert "metric" not in result
        assert "text" not in result

    def test_empty_dict(self):
        result = _extract_dataframes({})
        assert result == {}


class TestIsDataframe:
    def test_dataframe(self):
        import pandas as pd

        assert _is_dataframe(pd.DataFrame()) is True

    def test_not_dataframe(self):
        assert _is_dataframe("hello") is False
        assert _is_dataframe(42) is False
        assert _is_dataframe(None) is False
