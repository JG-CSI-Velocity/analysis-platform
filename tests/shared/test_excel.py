"""Tests for shared.excel module."""

import pandas as pd

from shared.excel import (
    _sanitize_sheet_title,
    create_workbook,
    save_to_excel,
    save_workbook,
)


class TestSanitizeSheetTitle:
    def test_truncates_to_31(self):
        long = "A" * 50
        assert len(_sanitize_sheet_title(long)) == 31

    def test_removes_special_chars(self):
        assert _sanitize_sheet_title("Test[1]:2") == "Test12"

    def test_short_title_unchanged(self):
        assert _sanitize_sheet_title("Valid Name") == "Valid Name"


class TestCreateWorkbook:
    def test_has_summary_sheet(self):
        wb = create_workbook("Test Report")
        assert wb.active.title == "Summary"
        assert wb.active.cell(row=1, column=1).value == "Test Report"


class TestSaveToExcel:
    def test_single_dataframe(self):
        wb = create_workbook()
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        save_to_excel(wb, df, "Test Sheet", "Test Analysis")
        assert "Test Sheet" in wb.sheetnames

    def test_dict_of_dataframes(self):
        wb = create_workbook()
        dfs = {
            "part1": pd.DataFrame({"x": [1]}),
            "part2": pd.DataFrame({"y": [2]}),
        }
        save_to_excel(wb, dfs, "Multi", "Multi Analysis")
        assert "Multi-part1" in wb.sheetnames
        assert "Multi-part2" in wb.sheetnames

    def test_with_key_metrics(self):
        wb = create_workbook()
        df = pd.DataFrame({"A": [1]})
        save_to_excel(wb, df, "KPI", "KPI Test", key_metrics={"Total": "$1M"})
        ws = wb["KPI"]
        found = False
        for row in ws.iter_rows(max_row=5, max_col=5, values_only=True):
            for val in row:
                if val and "Total" in str(val):
                    found = True
        assert found


class TestSaveWorkbook:
    def test_creates_file(self, tmp_path):
        wb = create_workbook("Test")
        out = tmp_path / "output.xlsx"
        save_workbook(wb, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_creates_parent_dirs(self, tmp_path):
        wb = create_workbook("Test")
        out = tmp_path / "sub" / "dir" / "output.xlsx"
        save_workbook(wb, out)
        assert out.exists()
