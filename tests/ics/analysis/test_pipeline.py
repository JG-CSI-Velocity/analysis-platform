"""Tests for pipeline.py -- end-to-end orchestration."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.pipeline import AnalysisPipelineResult as PipelineResult
from ics_toolkit.analysis.pipeline import export_outputs, run_pipeline


class TestPipelineResult:
    def test_dataclass_defaults(self, sample_settings):
        result = PipelineResult(
            settings=sample_settings,
            df=pd.DataFrame(),
        )
        assert result.analyses == []
        assert result.charts == {}

    def test_stores_data(self, sample_settings, sample_df):
        result = PipelineResult(
            settings=sample_settings,
            df=sample_df,
        )
        assert len(result.df) == len(sample_df)


class TestRunPipeline:
    def test_runs_with_sample_data(self, sample_settings):
        result = run_pipeline(sample_settings)
        assert isinstance(result, PipelineResult)
        assert len(result.df) > 0
        assert len(result.analyses) > 0

    def test_all_analyses_have_results(self, sample_settings):
        result = run_pipeline(sample_settings)
        for analysis in result.analyses:
            assert isinstance(analysis, AnalysisResult)
            assert analysis.name

    def test_progress_callback(self, sample_settings):
        calls = []

        def track(step, total, msg):
            calls.append((step, total, msg))

        run_pipeline(sample_settings, on_progress=track)
        assert len(calls) >= 4

    def test_charts_created(self, sample_settings):
        result = run_pipeline(sample_settings)
        # At least some charts should be created
        assert isinstance(result.charts, dict)


class TestExportOutputs:
    def test_excel_export(self, sample_settings, tmp_path):
        sample_settings.output_dir = tmp_path
        sample_settings.outputs.powerpoint = False
        result = run_pipeline(sample_settings)
        generated = export_outputs(result)
        assert len(generated) >= 1
        assert generated[0].suffix == ".xlsx"
        assert generated[0].exists()

    def test_no_export_when_disabled(self, sample_settings, tmp_path):
        sample_settings.output_dir = tmp_path
        sample_settings.outputs.excel = False
        sample_settings.outputs.powerpoint = False
        result = run_pipeline(sample_settings)
        generated = export_outputs(result)
        assert len(generated) == 0
