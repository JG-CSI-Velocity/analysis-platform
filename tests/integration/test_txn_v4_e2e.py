"""End-to-end integration test: V4 Transaction Storyline pipeline."""

from __future__ import annotations

from pathlib import Path

from shared.types import AnalysisResult as SharedResult


class TestTxnV4PipelineE2E:
    """Run the V4 storyline pipeline with synthetic data."""

    def test_v4_runner_direct(
        self,
        v4_config_yaml: Path,
        v4_txn_dir: Path,
        v4_odd_xlsx: Path,
        integration_output_dir: Path,
    ):
        """Run the V4 pipeline directly via txn_analysis.runner."""
        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn_v4

        ctx = PipelineContext(
            client_id="9999",
            client_name="Test CU",
            input_files={
                "tran": v4_txn_dir,
                "odd": v4_odd_xlsx,
                "v4_config": v4_config_yaml,
            },
            output_dir=integration_output_dir,
        )

        results = run_txn_v4(ctx)
        assert isinstance(results, dict)
        assert len(results) > 0, "V4 pipeline should produce storyline results"

        for name, ar in results.items():
            assert isinstance(ar, SharedResult), f"{name} is not SharedResult"

    def test_produces_excel_and_html(
        self,
        v4_config_yaml: Path,
        v4_txn_dir: Path,
        v4_odd_xlsx: Path,
        integration_output_dir: Path,
    ):
        """V4 pipeline should produce Excel and HTML reports."""
        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn_v4

        ctx = PipelineContext(
            client_id="9999",
            client_name="Test CU",
            input_files={
                "tran": v4_txn_dir,
                "odd": v4_odd_xlsx,
                "v4_config": v4_config_yaml,
            },
            output_dir=integration_output_dir,
        )

        run_txn_v4(ctx)

        xlsx_files = list(integration_output_dir.rglob("*.xlsx"))
        html_files = list(integration_output_dir.rglob("*.html"))
        assert len(xlsx_files) > 0, "Should produce Excel output"
        assert len(html_files) > 0, "Should produce HTML dashboard"

    def test_progress_callback(
        self,
        v4_config_yaml: Path,
        v4_txn_dir: Path,
        v4_odd_xlsx: Path,
        integration_output_dir: Path,
    ):
        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn_v4

        messages = []
        ctx = PipelineContext(
            client_id="9999",
            client_name="Test CU",
            input_files={
                "tran": v4_txn_dir,
                "odd": v4_odd_xlsx,
                "v4_config": v4_config_yaml,
            },
            output_dir=integration_output_dir,
            progress_callback=lambda msg: messages.append(msg),
        )

        run_txn_v4(ctx)
        assert len(messages) > 0, "Progress callback should be called"
        assert any("V4" in m for m in messages), "Messages should mention V4"
