"""End-to-end CLI tests: exercise each pipeline's Typer CLI with synthetic data.

These tests invoke the actual CLI commands via typer.testing.CliRunner to
validate argument parsing, pipeline execution, and output generation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()

E2E_DATA = Path(__file__).parent.parent / "e2e_data"
TXN_CSV = E2E_DATA / "8888_transactions.csv"
ICS_XLSX = E2E_DATA / "9999_ICS_2026.01.xlsx"
ARS_XLSX = E2E_DATA / "1200_Test CU_2026.02.xlsx"


@pytest.fixture(autouse=True)
def _matplotlib_agg():
    """Force non-interactive backend for chart generation."""
    import matplotlib

    matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# TXN CLI
# ---------------------------------------------------------------------------


class TestTxnCli:
    """Test the txn_analysis Typer CLI end-to-end."""

    def test_help(self):
        from txn_analysis.cli import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "data_file" in result.output.lower() or "DATA_FILE" in result.output

    def test_full_pipeline(self, tmp_path: Path):
        from txn_analysis.cli import app

        out = tmp_path / "txn_output"
        out.mkdir()
        result = runner.invoke(
            app,
            [
                str(TXN_CSV),
                "--output-dir",
                str(out),
                "--client-id",
                "8888",
                "--client-name",
                "CLI Test CU",
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Done" in result.output

        # Verify outputs
        xlsx_files = list(out.rglob("*.xlsx"))
        assert len(xlsx_files) >= 1, "Should produce Excel report"

        chart_dir = out / "charts"
        if chart_dir.exists():
            png_files = list(chart_dir.glob("*.png"))
            assert len(png_files) >= 5, f"Expected 5+ charts, got {len(png_files)}"

    def test_analysis_count(self, tmp_path: Path):
        from txn_analysis.cli import app

        out = tmp_path / "txn_output"
        out.mkdir()
        result = runner.invoke(app, [str(TXN_CSV), "--output-dir", str(out)])
        assert result.exit_code == 0
        assert "36/36" in result.output or "analyses completed" in result.output


# ---------------------------------------------------------------------------
# ICS CLI
# ---------------------------------------------------------------------------


class TestIcsCli:
    """Test the ics_toolkit Typer CLI end-to-end."""

    def test_help(self):
        from ics_toolkit.cli import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "analyze" in result.output

    def test_analyze_pipeline(self, tmp_path: Path):
        from ics_toolkit.cli import app

        out = tmp_path / "ics_output"
        out.mkdir()
        result = runner.invoke(
            app,
            [
                "analyze",
                str(ICS_XLSX),
                "--output",
                str(out),
                "--client-id",
                "9999",
                "--client-name",
                "CLI Test CU",
                "--cohort-start",
                "2025-01",
                "--no-charts",
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify Excel output
        xlsx_files = list(out.rglob("*.xlsx"))
        assert len(xlsx_files) >= 1, "Should produce Excel report"

    def test_analyze_with_charts(self, tmp_path: Path):
        from ics_toolkit.cli import app

        out = tmp_path / "ics_output"
        out.mkdir()
        result = runner.invoke(
            app,
            [
                "analyze",
                str(ICS_XLSX),
                "--output",
                str(out),
                "--client-id",
                "9999",
                "--cohort-start",
                "2025-01",
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify PPTX output
        pptx_files = list(out.rglob("*.pptx"))
        assert len(pptx_files) >= 1, "Should produce PPTX presentation"


# ---------------------------------------------------------------------------
# ARS CLI
# ---------------------------------------------------------------------------


class TestArsCli:
    """Test the ars_analysis Typer CLI end-to-end."""

    def test_help(self):
        from ars_analysis.cli import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output

    def test_run_help(self):
        from ars_analysis.cli import app

        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "file" in result.output.lower()

    def test_run_pipeline(self, tmp_path: Path):
        from ars_analysis.cli import app

        out = tmp_path / "ars_output"
        out.mkdir()
        result = runner.invoke(
            app,
            [
                "run",
                str(ARS_XLSX),
                "--output-dir",
                str(out),
                "--skip-pptx",
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "OK" in result.output or "complete" in result.output.lower()

    def test_run_produces_excel(self, tmp_path: Path):
        from ars_analysis.cli import app

        out = tmp_path / "ars_output"
        out.mkdir()
        result = runner.invoke(
            app,
            [
                "run",
                str(ARS_XLSX),
                "--output-dir",
                str(out),
                "--skip-pptx",
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        xlsx_files = list(out.rglob("*.xlsx"))
        assert len(xlsx_files) >= 1, "Should produce Excel report"

    def test_run_with_pptx(self, tmp_path: Path):
        from ars_analysis.cli import app

        out = tmp_path / "ars_output"
        out.mkdir()
        result = runner.invoke(
            app,
            ["run", str(ARS_XLSX), "--output-dir", str(out)],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        pptx_files = list(out.rglob("*.pptx"))
        assert len(pptx_files) >= 1, "Should produce PPTX deck"

    def test_run_selected_modules(self, tmp_path: Path):
        from ars_analysis.cli import app

        out = tmp_path / "ars_output"
        out.mkdir()
        result = runner.invoke(
            app,
            [
                "run",
                str(ARS_XLSX),
                "--output-dir",
                str(out),
                "--modules",
                "overview.stat_codes,overview.product_codes",
                "--skip-pptx",
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}"

    def test_validate_command(self):
        from ars_analysis.cli import app

        result = runner.invoke(app, ["validate", str(ARS_XLSX)])
        assert result.exit_code == 0
        assert "200" in result.output  # 200 rows

    def test_validate_nonexistent_file(self):
        from ars_analysis.cli import app

        result = runner.invoke(app, ["validate", "/tmp/nonexistent.xlsx"])
        assert result.exit_code == 1
