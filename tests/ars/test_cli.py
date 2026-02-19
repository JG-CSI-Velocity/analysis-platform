"""Tests for the CLI commands."""


import pandas as pd
import pytest
from typer.testing import CliRunner

from ars_analysis.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _ars_base_env(tmp_path, monkeypatch):
    """Ensure ARSSettings can load without a real config file."""
    monkeypatch.setenv("ARS_PATHS__ARS_BASE", str(tmp_path))


@pytest.fixture
def odd_csv(tmp_path):
    """Create a minimal ODD CSV file for CLI testing."""
    df = pd.DataFrame({
        "Stat Code": ["O"] * 5,
        "Product Code": ["DDA"] * 5,
        "Date Opened": ["2025-06-15"] * 5,
        "Balance": [1000.0] * 5,
        "Business?": ["No"] * 5,
    })
    path = tmp_path / "1200_TestCU_2026.02.csv"
    df.to_csv(path, index=False)
    return path


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ARS Automated Reporting System" in result.output


def test_run_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Analyze a single client" in result.output


def test_validate_missing_file():
    result = runner.invoke(app, ["validate", "/nonexistent/file.csv"])
    assert result.exit_code == 1


def test_validate_valid_file(odd_csv):
    result = runner.invoke(app, ["validate", str(odd_csv)])
    assert result.exit_code == 0
    assert "Valid" in result.output
    assert "5" in result.output  # 5 rows


def test_validate_bad_columns(tmp_path):
    bad_df = pd.DataFrame({"Wrong Column Name Here": list(range(50))})
    bad_path = tmp_path / "bad.csv"
    bad_df.to_csv(bad_path, index=False)

    result = runner.invoke(app, ["validate", str(bad_path)])
    assert result.exit_code == 1
    assert "missing required columns" in result.output


def test_run_missing_file():
    result = runner.invoke(app, ["run", "/nonexistent/file.csv"])
    assert result.exit_code == 1


def test_format_help():
    result = runner.invoke(app, ["format", "--help"])
    assert result.exit_code == 0
    assert "Format retrieved ODD files" in result.output


def test_format_runs():
    result = runner.invoke(app, ["format"])
    assert result.exit_code == 0
    assert "Format Results" in result.output


def test_scan_help():
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "List clients with data ready" in result.output


def test_scan_runs():
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0


def test_retrieve_help():
    result = runner.invoke(app, ["retrieve", "--help"])
    assert result.exit_code == 0
    assert "Retrieve ODD files" in result.output


def test_batch_no_files():
    result = runner.invoke(app, ["batch"])
    assert result.exit_code == 0
    assert "No ready files" in result.output


def test_init_creates_configs_dir(tmp_path):
    result = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "configs").exists()
