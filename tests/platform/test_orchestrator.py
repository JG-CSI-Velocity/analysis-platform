"""Tests for platform_app.orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from platform_app.orchestrator import PIPELINE_NAMES, _detect_pipelines, run_pipeline


class TestPipelineNames:
    def test_all_names_known(self):
        assert set(PIPELINE_NAMES) == {"ars", "txn", "txn_v4", "ics", "ics_append"}


class TestDetectPipelines:
    def test_oddd_detects_ars(self):
        assert _detect_pipelines({"oddd": Path("x.xlsx")}) == ["ars"]

    def test_tran_detects_txn(self):
        assert _detect_pipelines({"tran": Path("x.csv")}) == ["txn"]

    def test_tran_and_odd_detects_txn_and_v4(self):
        result = _detect_pipelines({"tran": Path("x.csv"), "odd": Path("y.xlsx")})
        assert result == ["txn", "txn_v4"]

    def test_ics_detects_ics(self):
        assert _detect_pipelines({"ics": Path("x.xlsx")}) == ["ics"]

    def test_all_files_detects_all(self):
        files = {
            "oddd": Path("a.xlsx"),
            "tran": Path("b.csv"),
            "odd": Path("c.xlsx"),
            "ics": Path("d.xlsx"),
        }
        result = _detect_pipelines(files)
        assert result == ["ars", "txn", "txn_v4", "ics"]

    def test_empty_returns_empty(self):
        assert _detect_pipelines({}) == []


class TestRunPipelineErrors:
    def test_unknown_pipeline_raises(self):
        with pytest.raises(ValueError, match="Unknown pipeline"):
            run_pipeline("bogus", input_files={}, output_dir=Path("/tmp"))

    def test_ars_missing_oddd_raises(self, tmp_path):
        with pytest.raises((FileNotFoundError, KeyError)):
            run_pipeline("ars", input_files={}, output_dir=tmp_path)

    def test_txn_missing_tran_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_pipeline("txn", input_files={}, output_dir=tmp_path)

    def test_ics_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_pipeline("ics", input_files={}, output_dir=tmp_path)
