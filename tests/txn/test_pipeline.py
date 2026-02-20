"""Tests for the pipeline orchestrator."""

from __future__ import annotations

import pytest

from txn_analysis.pipeline import PipelineResult, export_outputs, run_pipeline
from txn_analysis.settings import Settings


@pytest.fixture()
def pipeline_settings(sample_csv_path, tmp_path):
    return Settings.from_args(data_file=sample_csv_path, output_dir=tmp_path)


class TestRunPipeline:
    def test_returns_pipeline_result(self, pipeline_settings):
        result = run_pipeline(pipeline_settings)
        assert isinstance(result, PipelineResult)

    def test_has_analyses(self, pipeline_settings):
        result = run_pipeline(pipeline_settings)
        assert len(result.analyses) == 35

    def test_all_analyses_succeed(self, pipeline_settings):
        result = run_pipeline(pipeline_settings)
        # Storyline adapters (demographics, campaigns, payroll, lifecycle) may fail
        # gracefully without ODD data -- only check non-adapter analyses
        adapter_names = {"demographics", "campaigns", "payroll", "lifecycle"}
        non_adapter = [a for a in result.analyses if a.name not in adapter_names]
        failed = [a for a in non_adapter if a.error is not None]
        assert len(failed) == 0, f"Failed: {[a.name for a in failed]}"

    def test_has_charts(self, pipeline_settings):
        result = run_pipeline(pipeline_settings)
        assert len(result.charts) > 0

    def test_df_populated(self, pipeline_settings):
        result = run_pipeline(pipeline_settings)
        assert not result.df.empty

    def test_progress_callback(self, pipeline_settings):
        calls = []

        def on_progress(step, total, msg):
            calls.append((step, total, msg))

        run_pipeline(pipeline_settings, on_progress=on_progress)
        assert len(calls) == 3
        assert calls[0][0] == 0
        assert calls[2][0] == 2


class TestExportOutputs:
    def test_generates_excel(self, pipeline_settings, tmp_path):
        result = run_pipeline(pipeline_settings)
        files = export_outputs(result)
        xlsx_files = [f for f in files if f.suffix == ".xlsx"]
        assert len(xlsx_files) == 1
        assert xlsx_files[0].exists()

    def test_generates_chart_pngs(self, pipeline_settings, tmp_path):
        result = run_pipeline(pipeline_settings)
        files = export_outputs(result)
        png_files = [f for f in files if f.suffix == ".png"]
        assert len(png_files) > 0
        assert all(f.exists() for f in png_files)

    def test_chart_pngs_disabled(self, sample_csv_path, tmp_path):
        settings = Settings.from_args(
            data_file=sample_csv_path,
            output_dir=tmp_path,
            outputs={"excel": True, "chart_images": False},
        )
        result = run_pipeline(settings)
        files = export_outputs(result)
        png_files = [f for f in files if f.suffix == ".png"]
        assert len(png_files) == 0

    def test_excel_has_content(self, pipeline_settings, tmp_path):
        result = run_pipeline(pipeline_settings)
        files = export_outputs(result)
        xlsx_files = [f for f in files if f.suffix == ".xlsx"]
        assert xlsx_files[0].stat().st_size > 5000

    def test_no_excel_when_disabled(self, sample_csv_path, tmp_path):
        settings = Settings.from_args(
            data_file=sample_csv_path,
            output_dir=tmp_path,
            outputs={"excel": False, "chart_images": False},
        )
        result = run_pipeline(settings)
        files = export_outputs(result)
        assert len(files) == 0
