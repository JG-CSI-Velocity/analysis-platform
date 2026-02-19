"""Tests for the generate step (Excel output)."""

import pandas as pd
import pytest

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
from ars_analysis.pipeline.steps.generate import step_generate


@pytest.fixture
def ctx_with_results(tmp_path):
    """PipelineContext with analysis results ready for output."""
    paths = OutputPaths(
        base_dir=tmp_path,
        charts_dir=tmp_path / "charts",
        excel_dir=tmp_path,
        pptx_dir=tmp_path,
    )
    ctx = PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=paths,
    )
    ctx.all_slides = [
        AnalysisResult(
            slide_id="A1",
            title="Stat Codes",
            excel_data={
                "Summary": pd.DataFrame({"Code": ["O", "C"], "Count": [6, 3]}),
            },
        ),
        AnalysisResult(
            slide_id="A2",
            title="Products",
            excel_data={
                "Products": pd.DataFrame({"Product": ["DDA"], "Count": [5]}),
            },
        ),
    ]
    return ctx


def test_generate_writes_excel(ctx_with_results):
    step_generate(ctx_with_results)
    excel_files = list(ctx_with_results.paths.excel_dir.glob("*.xlsx"))
    assert len(excel_files) == 1
    assert "1200" in excel_files[0].name


def test_generate_excel_has_correct_sheets(ctx_with_results):
    step_generate(ctx_with_results)
    import openpyxl

    excel_path = list(ctx_with_results.paths.excel_dir.glob("*.xlsx"))[0]
    wb = openpyxl.load_workbook(excel_path)
    assert len(wb.sheetnames) == 3  # Summary, A1_Summary, A2_Products
    assert wb.sheetnames[0] == "Summary"


def test_generate_no_results_is_noop(tmp_path):
    ctx = PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(base_dir=tmp_path, excel_dir=tmp_path),
    )
    step_generate(ctx)
    excel_files = list(tmp_path.glob("*.xlsx"))
    assert len(excel_files) == 0


def test_generate_logs_to_export_log(ctx_with_results):
    step_generate(ctx_with_results)
    assert len(ctx_with_results.export_log) >= 1  # Excel + possibly PPTX
    assert any("1200" in entry for entry in ctx_with_results.export_log)


def test_generate_result_without_excel_data(tmp_path):
    """Results with no excel_data should be skipped without error."""
    ctx = PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(base_dir=tmp_path, excel_dir=tmp_path),
    )
    ctx.all_slides = [
        AnalysisResult(slide_id="A1", title="Chart Only", chart_path=None),
    ]
    step_generate(ctx)
    # No excel data means no file written
    excel_files = list(tmp_path.glob("*.xlsx"))
    assert len(excel_files) == 0
