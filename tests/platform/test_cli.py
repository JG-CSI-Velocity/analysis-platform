"""Tests for platform_app.cli."""

from __future__ import annotations

from pathlib import Path

from platform_app.cli import _build_input_files, _scan_data_dir


class TestBuildInputFiles:
    def test_ars_maps_to_oddd(self):
        result = _build_input_files("ars", Path("data.xlsx"), None, None)
        assert result == {"oddd": Path("data.xlsx")}

    def test_txn_maps_to_tran(self):
        result = _build_input_files("txn", Path("data.csv"), None, None)
        assert result == {"tran": Path("data.csv")}

    def test_txn_with_odd(self):
        result = _build_input_files("txn", Path("tran.csv"), Path("odd.xlsx"), None)
        assert result == {"tran": Path("tran.csv"), "odd": Path("odd.xlsx")}

    def test_txn_uses_tran_override(self):
        result = _build_input_files("txn", Path("default.csv"), None, Path("actual.csv"))
        assert result == {"tran": Path("actual.csv")}

    def test_ics_maps_to_ics(self):
        result = _build_input_files("ics", Path("data.xlsx"), None, None)
        assert result == {"ics": Path("data.xlsx")}

    def test_ics_append_maps_to_base_dir(self):
        result = _build_input_files("ics_append", Path("/data/ics"), None, None)
        assert result == {"base_dir": Path("/data/ics")}


class TestScanDataDir:
    def test_detects_files_by_name(self, tmp_path):
        (tmp_path / "12345_oddd_data.xlsx").touch()
        (tmp_path / "12345_tran_debit.csv").touch()
        (tmp_path / "12345_odd_accounts.xlsx").touch()
        (tmp_path / "12345_ics_report.xlsx").touch()
        (tmp_path / "readme.txt").touch()  # should be ignored

        result = _scan_data_dir(tmp_path)
        assert "oddd" in result
        assert "tran" in result
        assert "odd" in result
        assert "ics" in result

    def test_empty_dir_returns_empty(self, tmp_path):
        assert _scan_data_dir(tmp_path) == {}

    def test_ignores_non_data_files(self, tmp_path):
        (tmp_path / "report.pdf").touch()
        (tmp_path / "notes.txt").touch()
        assert _scan_data_dir(tmp_path) == {}
