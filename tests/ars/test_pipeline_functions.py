"""Tests for key pipeline functions from ars_analysis.pipeline."""

import pandas as pd

from ars_analysis.pipeline import (
    ARSFieldFormatter,
    clean_code_column,
    create_context,
    safe_clean_column,
    sanitize_filename_component,
    sanitize_sheet_title,
    step_create_subsets,
    step_date_range,
)


class TestCreateContext:
    def test_returns_dict(self):
        ctx = create_context()
        assert isinstance(ctx, dict)

    def test_has_required_keys(self):
        ctx = create_context()
        assert "data" in ctx
        assert "results" in ctx
        assert "all_slides" in ctx
        assert "export_log" in ctx

    def test_results_empty(self):
        ctx = create_context()
        assert ctx["results"] == {}
        assert ctx["all_slides"] == []


class TestCleanCodeColumn:
    def test_float_to_int(self):
        assert clean_code_column(100.0) == "100"

    def test_string_passthrough(self):
        assert clean_code_column("ABC") == "ABC"

    def test_none(self):
        result = clean_code_column(None)
        assert result is None or result == ""


class TestSafeCleanColumn:
    def test_cleans_column(self):
        df = pd.DataFrame({"code": ["  A  ", " B", "C "]})
        result = safe_clean_column(df, "code")
        assert result["code"].tolist() == ["A", "B", "C"]

    def test_missing_column(self):
        df = pd.DataFrame({"other": [1, 2]})
        result = safe_clean_column(df, "missing")
        assert "missing" not in result.columns


class TestSanitize:
    def test_filename_removes_special(self):
        assert "<test>" not in sanitize_filename_component("<test>")

    def test_sheet_title_max_length(self):
        long_title = "A" * 50
        result = sanitize_sheet_title(long_title)
        assert len(result) <= 31


class TestARSFieldFormatter:
    def test_currency_format(self):
        fmt = ARSFieldFormatter()
        assert "currency" in fmt.identify_column_format("Total Spend")

    def test_integer_format(self):
        fmt = ARSFieldFormatter()
        result = fmt.identify_column_format("Total Swipes")
        assert result in ("integer", "text")

    def test_percentage_format(self):
        fmt = ARSFieldFormatter()
        result = fmt.identify_column_format("DCTR Rate %")
        assert "percent" in result.lower() or result == "percentage"


class TestStepDateRange:
    def test_sets_dates(self):
        ctx = create_context()
        ctx["data"] = pd.DataFrame({"Acct": [1]})
        step_date_range(ctx)
        assert ctx["start_date"] is not None
        assert ctx["end_date"] is not None
        assert len(ctx["last_12_months"]) == 12


class TestStepCreateSubsets:
    def test_creates_open_closed(self):
        ctx = create_context()
        ctx["data"] = pd.DataFrame(
            {
                "Stat Code": ["O", "O", "C"],
                "Business?": ["No", "Yes", "No"],
                "Debit?": ["Yes", "No", "Yes"],
                "Prod Code": ["001", "001", "001"],
                "Mailable?": ["Yes", "Yes", "No"],
                "Date Closed": [None, None, "2024-06-01"],
                "Date Opened": ["2020-01-01", "2021-06-01", "2019-03-01"],
                "Avg Bal": [1000.0, 2500.0, 500.0],
            }
        )
        ctx["eligible_stat_code"] = ["O"]
        ctx["eligible_prod_code"] = ["001"]
        ctx["eligible_mailable"] = ["Yes"]
        ctx["start_date"] = pd.Timestamp("2024-01-01")
        ctx["end_date"] = pd.Timestamp("2025-01-01")
        ctx["latest_reg_e_column"] = None
        ctx["reg_e_opt_in"] = []

        step_create_subsets(ctx)

        assert "open_accounts" in ctx
        assert "closed_accounts" in ctx
        assert len(ctx["open_accounts"]) == 2
        assert len(ctx["closed_accounts"]) == 1
