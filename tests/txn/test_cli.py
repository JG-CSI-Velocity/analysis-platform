"""Tests for the Typer CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from txn_analysis.cli import app

runner = CliRunner()


class TestCLI:
    def test_analyze_runs(self, sample_csv_path, tmp_path):
        result = runner.invoke(app, [str(sample_csv_path), "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Done" in result.output

    def test_analyze_with_client_id(self, sample_csv_path, tmp_path):
        result = runner.invoke(
            app,
            [str(sample_csv_path), "--output-dir", str(tmp_path), "--client-id", "99999"],
        )
        assert result.exit_code == 0

    def test_analyze_with_verbose(self, sample_csv_path, tmp_path):
        result = runner.invoke(
            app, [str(sample_csv_path), "--output-dir", str(tmp_path), "--verbose"]
        )
        assert result.exit_code == 0

    def test_bad_file_exits_nonzero(self, tmp_path):
        result = runner.invoke(app, [str(tmp_path / "nonexistent.csv")])
        assert result.exit_code != 0

    def test_produces_excel_output(self, sample_csv_path, tmp_path):
        runner.invoke(app, [str(sample_csv_path), "--output-dir", str(tmp_path)])
        xlsx_files = list(tmp_path.glob("*.xlsx"))
        assert len(xlsx_files) == 1

    def test_analyses_count_in_output(self, sample_csv_path, tmp_path):
        result = runner.invoke(app, [str(sample_csv_path), "--output-dir", str(tmp_path)])
        assert "36" in result.output
