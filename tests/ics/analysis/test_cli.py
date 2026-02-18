"""Tests for analyze CLI command."""

from typer.testing import CliRunner

from ics_toolkit.cli import app

runner = CliRunner()


class TestAnalyzeCLI:
    def test_help_flag(self):
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "analysis" in result.stdout.lower() or "report" in result.stdout.lower()

    def test_missing_data_file(self):
        result = runner.invoke(app, ["analyze", "nonexistent.csv"])
        assert result.exit_code == 1

    def test_runs_with_sample_data(self, sample_settings, tmp_path):
        result = runner.invoke(
            app,
            [
                "analyze",
                str(sample_settings.data_file),
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

    def test_verbose_flag(self, sample_settings, tmp_path):
        result = runner.invoke(
            app,
            [
                "analyze",
                str(sample_settings.data_file),
                "--output",
                str(tmp_path),
                "--verbose",
            ],
        )
        assert result.exit_code == 0

    def test_client_id_override(self, sample_settings, tmp_path):
        result = runner.invoke(
            app,
            [
                "analyze",
                str(sample_settings.data_file),
                "--output",
                str(tmp_path),
                "--client-id",
                "9999",
                "--client-name",
                "Test Client",
            ],
        )
        assert result.exit_code == 0
