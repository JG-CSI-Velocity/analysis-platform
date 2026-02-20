"""Tests for txn_analysis.runner -- PipelineContext bridge."""

from pathlib import Path

import pandas as pd
import pytest

from shared.context import PipelineContext
from shared.types import AnalysisResult as SharedResult
from txn_analysis.runner import _convert_results


class TestConvertResults:
    def test_converts_successful(self):
        from txn_analysis.analyses.base import AnalysisResult

        ar = AnalysisResult(
            name="top_merchants_by_spend",
            title="Top Merchants by Spend",
            df=pd.DataFrame({"merchant": ["A"], "spend": [1000]}),
            sheet_name="TopSpend",
            metadata={"top_n": 50},
        )
        results = _convert_results([ar])
        assert "top_merchants_by_spend" in results
        r = results["top_merchants_by_spend"]
        assert isinstance(r, SharedResult)
        assert r.name == "top_merchants_by_spend"
        assert "main" in r.data
        assert r.summary == "Top Merchants by Spend"
        assert r.metadata["title"] == "Top Merchants by Spend"
        assert r.metadata["sheet_name"] == "TopSpend"
        assert r.metadata["top_n"] == 50

    def test_skips_failed(self):
        from txn_analysis.analyses.base import AnalysisResult

        ar = AnalysisResult(
            name="failed_one",
            title="Failed Analysis",
            df=pd.DataFrame(),
            error="Something broke",
        )
        results = _convert_results([ar])
        assert "failed_one" not in results

    def test_empty_list(self):
        results = _convert_results([])
        assert results == {}


class TestRunTxnMissingFile:
    def test_raises_without_input_file(self):
        ctx = PipelineContext(output_dir=Path("/tmp/test"))
        with pytest.raises(FileNotFoundError, match="No 'tran' or 'txn_dir'"):
            from txn_analysis.runner import run_txn

            run_txn(ctx)
