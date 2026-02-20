"""Tests for ics_toolkit.runner -- PipelineContext bridge."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from shared.context import PipelineContext
from shared.types import AnalysisResult as SharedResult


class TestConvertResults:
    """Test ICS AnalysisResult -> SharedResult conversion."""

    def test_converts_successful(self):
        from ics_toolkit.analysis.analyses.base import AnalysisResult
        from ics_toolkit.runner import _convert_results

        ar = AnalysisResult.from_df(
            "portfolio_overview",
            "Portfolio Overview",
            pd.DataFrame({"metric": ["Total"], "value": [1000]}),
            sheet_name="Portfolio",
            metadata={"count": 50},
        )
        results = _convert_results([ar])
        assert "portfolio_overview" in results
        r = results["portfolio_overview"]
        assert isinstance(r, SharedResult)
        assert r.name == "portfolio_overview"
        assert "main" in r.data
        assert r.metadata["title"] == "Portfolio Overview"

    def test_skips_failed(self):
        from ics_toolkit.analysis.analyses.base import AnalysisResult
        from ics_toolkit.runner import _convert_results

        ar = AnalysisResult.from_df("failed_one", "Failed", pd.DataFrame(), error="broke")
        results = _convert_results([ar])
        assert "failed_one" not in results

    def test_empty_list(self):
        from ics_toolkit.runner import _convert_results

        assert _convert_results([]) == {}


class TestRunIcsMissingFile:
    def test_raises_without_ics_input(self):
        ctx = PipelineContext(output_dir=Path("/tmp/test"))
        with pytest.raises(FileNotFoundError, match="No 'ics' input file"):
            from ics_toolkit.runner import run_ics

            run_ics(ctx)

    def test_raises_without_base_dir(self):
        ctx = PipelineContext(output_dir=Path("/tmp/test"))
        with pytest.raises(FileNotFoundError, match="No 'base_dir' input file"):
            from ics_toolkit.runner import run_ics_append

            run_ics_append(ctx)
