"""End-to-end integration test: Transaction pipeline with ODD enrichment.

After V4 consolidation, the main txn pipeline handles both single-file
and transaction-dir+ODD workflows via run_txn().
"""

from __future__ import annotations

from pathlib import Path

from shared.types import AnalysisResult as SharedResult


class TestTxnWithOddE2E:
    """Run the unified transaction pipeline with ODD data."""

    def test_run_txn_with_txn_dir(
        self,
        v4_txn_dir: Path,
        v4_odd_xlsx: Path,
        integration_output_dir: Path,
    ):
        """Run via run_txn() with txn_dir + odd inputs."""
        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn

        ctx = PipelineContext(
            client_id="9999",
            client_name="Test CU",
            input_files={
                "txn_dir": v4_txn_dir,
                "odd": v4_odd_xlsx,
            },
            output_dir=integration_output_dir,
        )

        results = run_txn(ctx)
        assert isinstance(results, dict)
        assert len(results) > 0, "Pipeline should produce analysis results"

        for name, ar in results.items():
            assert isinstance(ar, SharedResult), f"{name} is not SharedResult"

    def test_run_txn_missing_both_inputs(
        self,
        integration_output_dir: Path,
    ):
        """Should raise when neither tran nor txn_dir provided."""
        import pytest

        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn

        ctx = PipelineContext(
            output_dir=integration_output_dir,
        )
        with pytest.raises(FileNotFoundError, match="No 'tran' or 'txn_dir'"):
            run_txn(ctx)
