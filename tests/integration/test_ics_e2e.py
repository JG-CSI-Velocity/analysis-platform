"""End-to-end integration test: ICS analysis pipeline."""

from __future__ import annotations

from pathlib import Path

from shared.types import AnalysisResult as SharedResult


class TestIcsPipelineE2E:
    """Run the full ICS pipeline with sample data through the orchestrator."""

    def test_orchestrator_ics(self, sample_ics_xlsx: Path, integration_output_dir: Path):
        from platform_app.orchestrator import run_pipeline

        results = run_pipeline(
            "ics",
            input_files={"ics": sample_ics_xlsx},
            output_dir=integration_output_dir,
            client_id="9999",
            client_name="Test CU",
        )

        assert isinstance(results, dict)
        assert len(results) > 0, "Pipeline should produce at least one analysis"

        for name, ar in results.items():
            assert isinstance(ar, SharedResult), f"{name} is not SharedResult"

    def test_produces_outputs(self, sample_ics_xlsx: Path, integration_output_dir: Path):
        from platform_app.orchestrator import run_pipeline

        run_pipeline(
            "ics",
            input_files={"ics": sample_ics_xlsx},
            output_dir=integration_output_dir,
            client_id="9999",
            client_name="Test CU",
        )

        xlsx_files = list(integration_output_dir.rglob("*.xlsx"))
        assert len(xlsx_files) > 0, "Should produce Excel output"

    def test_progress_callback(self, sample_ics_xlsx: Path, integration_output_dir: Path):
        from platform_app.orchestrator import run_pipeline

        messages = []
        run_pipeline(
            "ics",
            input_files={"ics": sample_ics_xlsx},
            output_dir=integration_output_dir,
            progress_callback=lambda msg: messages.append(msg),
        )

        assert len(messages) > 0
