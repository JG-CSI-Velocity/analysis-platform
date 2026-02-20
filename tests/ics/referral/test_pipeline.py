"""Tests for referral pipeline orchestrator."""

from __future__ import annotations

from ics_toolkit.referral.pipeline import (
    ReferralPipelineResult,
    export_outputs,
    run_pipeline,
)


class TestRunPipeline:
    """Tests for run_pipeline."""

    def test_returns_pipeline_result(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert isinstance(result, ReferralPipelineResult)

    def test_result_has_enriched_df(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert not result.df.empty
        assert "Referrer" in result.df.columns
        assert "Influence Score" not in result.df.columns  # scores are in metrics

    def test_result_has_referrer_metrics(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert not result.referrer_metrics.empty
        assert "Influence Score" in result.referrer_metrics.columns

    def test_result_has_staff_metrics(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert not result.staff_metrics.empty
        assert "Multiplier Score" in result.staff_metrics.columns

    def test_result_has_eight_analyses(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert len(result.analyses) == 8

    def test_no_analysis_errors(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        for a in result.analyses:
            assert a.error is None, f"{a.name} had error: {a.error}"

    def test_skip_charts_produces_no_charts(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert len(result.charts) == 0
        assert len(result.chart_pngs) == 0

    def test_progress_callback(self, sample_referral_settings):
        calls = []

        def on_progress(step, total, msg):
            calls.append((step, total, msg))

        run_pipeline(sample_referral_settings, on_progress=on_progress, skip_charts=True)
        assert len(calls) >= 7  # At least 7 progress steps

    def test_settings_preserved(self, sample_referral_settings):
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        assert result.settings is sample_referral_settings


class TestExportOutputs:
    """Tests for export_outputs."""

    def test_generates_excel_file(self, sample_referral_settings, tmp_path):
        sample_referral_settings = sample_referral_settings.model_copy(
            update={"output_dir": tmp_path / "out"}
        )
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        paths = export_outputs(result, skip_charts=True)
        assert len(paths) >= 1
        xlsx_paths = [p for p in paths if p.suffix == ".xlsx"]
        assert len(xlsx_paths) == 1
        assert xlsx_paths[0].exists()

    def test_generates_pptx_file(self, sample_referral_settings, tmp_path):
        sample_referral_settings = sample_referral_settings.model_copy(
            update={"output_dir": tmp_path / "out"}
        )
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        paths = export_outputs(result, skip_charts=True)
        pptx_paths = [p for p in paths if p.suffix == ".pptx"]
        assert len(pptx_paths) == 1
        assert pptx_paths[0].exists()

    def test_output_dir_created(self, sample_referral_settings, tmp_path):
        out_dir = tmp_path / "new_dir" / "sub"
        sample_referral_settings = sample_referral_settings.model_copy(
            update={"output_dir": out_dir}
        )
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        export_outputs(result, skip_charts=True)
        assert out_dir.exists()

    def test_filenames_contain_client_id(self, sample_referral_settings, tmp_path):
        sample_referral_settings = sample_referral_settings.model_copy(
            update={
                "output_dir": tmp_path / "out",
                "client_id": "1234",
            }
        )
        result = run_pipeline(sample_referral_settings, skip_charts=True)
        paths = export_outputs(result, skip_charts=True)
        for p in paths:
            assert "1234" in p.name
