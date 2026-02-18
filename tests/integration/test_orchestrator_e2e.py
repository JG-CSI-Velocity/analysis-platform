"""End-to-end integration test: Orchestrator multi-pipeline."""

from __future__ import annotations

from pathlib import Path

from platform_app.orchestrator import run_all


class TestAutoDetection:
    """Test that run_all correctly auto-detects and runs applicable pipelines."""

    def test_txn_auto_detection(self, sample_txn_csv: Path, integration_output_dir: Path):
        all_results = run_all(
            input_files={"tran": sample_txn_csv},
            output_dir=integration_output_dir,
            client_id="9999",
        )

        assert "txn" in all_results
        assert len(all_results["txn"]) > 0

    def test_ics_auto_detection(self, sample_ics_xlsx: Path, integration_output_dir: Path):
        all_results = run_all(
            input_files={"ics": sample_ics_xlsx},
            output_dir=integration_output_dir,
            client_id="9999",
        )

        assert "ics" in all_results
        assert len(all_results["ics"]) > 0

    def test_multi_pipeline(
        self, sample_txn_csv: Path, sample_ics_xlsx: Path, integration_output_dir: Path,
    ):
        all_results = run_all(
            input_files={"tran": sample_txn_csv, "ics": sample_ics_xlsx},
            output_dir=integration_output_dir,
            client_id="9999",
            client_name="Multi CU",
        )

        assert "txn" in all_results
        assert "ics" in all_results

    def test_explicit_pipeline_selection(
        self, sample_txn_csv: Path, integration_output_dir: Path,
    ):
        all_results = run_all(
            input_files={"tran": sample_txn_csv},
            output_dir=integration_output_dir,
            pipelines=["txn"],
        )

        assert "txn" in all_results
        assert len(all_results) == 1

    def test_progress_callback_multi(
        self, sample_txn_csv: Path, sample_ics_xlsx: Path, integration_output_dir: Path,
    ):
        messages = []
        run_all(
            input_files={"tran": sample_txn_csv, "ics": sample_ics_xlsx},
            output_dir=integration_output_dir,
            progress_callback=lambda msg: messages.append(msg),
        )

        assert any("Running" in m for m in messages)
