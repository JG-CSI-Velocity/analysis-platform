"""End-to-end integration test: ARS analysis pipeline."""

from __future__ import annotations

from pathlib import Path

from shared.types import AnalysisResult as SharedResult


class TestArsPipelineE2E:
    """Run the full ARS pipeline with sample ODDD data through the orchestrator."""

    def test_orchestrator_ars(
        self,
        sample_oddd_xlsx: Path,
        ars_client_config: Path,
        integration_output_dir: Path,
    ):
        from platform_app.orchestrator import run_pipeline

        results = run_pipeline(
            "ars",
            input_files={"oddd": sample_oddd_xlsx},
            output_dir=integration_output_dir,
            client_id="9999",
            client_name="Test CU",
            client_config={"config_path": str(ars_client_config)},
        )

        assert isinstance(results, dict)
        assert len(results) > 0, "ARS pipeline should produce at least one analysis"

        for name, ar in results.items():
            assert isinstance(ar, SharedResult), f"{name} is not SharedResult"

    def test_produces_outputs(
        self,
        sample_oddd_xlsx: Path,
        ars_client_config: Path,
        integration_output_dir: Path,
    ):
        from platform_app.orchestrator import run_pipeline

        run_pipeline(
            "ars",
            input_files={"oddd": sample_oddd_xlsx},
            output_dir=integration_output_dir,
            client_config={"config_path": str(ars_client_config)},
        )

        xlsx_files = list(integration_output_dir.rglob("*.xlsx"))
        assert len(xlsx_files) > 0, "Should produce Excel output"

    def test_progress_callback(
        self,
        sample_oddd_xlsx: Path,
        ars_client_config: Path,
        integration_output_dir: Path,
    ):
        from platform_app.orchestrator import run_pipeline

        messages = []
        run_pipeline(
            "ars",
            input_files={"oddd": sample_oddd_xlsx},
            output_dir=integration_output_dir,
            client_config={"config_path": str(ars_client_config)},
            progress_callback=lambda msg: messages.append(msg),
        )

        assert len(messages) > 0, "Progress callback should be called"
