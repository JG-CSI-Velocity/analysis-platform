"""End-to-end integration test: Transaction analysis pipeline."""

from __future__ import annotations

from pathlib import Path

from shared.context import PipelineContext
from shared.types import AnalysisResult as SharedResult


class TestTxnPipelineE2E:
    """Run the full txn pipeline with sample data through the orchestrator."""

    def test_orchestrator_txn(self, sample_txn_csv: Path, integration_output_dir: Path):
        from platform_app.orchestrator import run_pipeline

        results = run_pipeline(
            "txn",
            input_files={"tran": sample_txn_csv},
            output_dir=integration_output_dir,
            client_id="9999",
            client_name="Test CU",
        )

        assert isinstance(results, dict)
        assert len(results) > 0, "Pipeline should produce at least one analysis"

        for name, ar in results.items():
            assert isinstance(ar, SharedResult), f"{name} is not SharedResult"
            assert ar.name == name
            assert ar.summary, f"{name} has no summary"

    def test_runner_direct(self, sample_txn_csv: Path, integration_output_dir: Path):
        from txn_analysis.runner import run_txn

        ctx = PipelineContext(
            client_id="9999",
            client_name="Test CU",
            input_files={"tran": sample_txn_csv},
            output_dir=integration_output_dir,
        )

        results = run_txn(ctx)
        assert isinstance(results, dict)
        assert len(results) > 0

    def test_produces_excel_output(self, sample_txn_csv: Path, integration_output_dir: Path):
        from platform_app.orchestrator import run_pipeline

        run_pipeline(
            "txn",
            input_files={"tran": sample_txn_csv},
            output_dir=integration_output_dir,
            client_id="9999",
            client_name="Test CU",
        )

        xlsx_files = list(integration_output_dir.rglob("*.xlsx"))
        assert len(xlsx_files) > 0, "Should produce at least one Excel file"

    def test_progress_callback(self, sample_txn_csv: Path, integration_output_dir: Path):
        from platform_app.orchestrator import run_pipeline

        messages = []
        run_pipeline(
            "txn",
            input_files={"tran": sample_txn_csv},
            output_dir=integration_output_dir,
            progress_callback=lambda msg: messages.append(msg),
        )

        assert len(messages) > 0, "Progress callback should be called"
