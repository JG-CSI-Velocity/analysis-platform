"""Tests for txn_analysis.formatting."""

from __future__ import annotations

import math

from txn_analysis.formatting import (
    excel_number_format,
    format_value,
    is_currency_column,
    is_grand_total_row,
    is_percentage_column,
)


class TestFormatValue:
    def test_none(self):
        assert format_value(None, "amount") == ""

    def test_nan(self):
        assert format_value(float("nan"), "amount") == ""

    def test_currency(self):
        assert format_value(1234.56, "total_amount") == "$1,235"

    def test_percentage(self):
        assert format_value(42.567, "pct_change") == "42.6%"

    def test_average(self):
        assert format_value(123.4, "avg_transaction") == "123.40"

    def test_integer(self):
        assert format_value(1000.0, "transaction_count") == "1,000"

    def test_float(self):
        assert format_value(3.14, "score") == "3.14"

    def test_string(self):
        assert format_value("hello", "name") == "hello"


class TestExcelNumberFormat:
    def test_currency(self):
        assert excel_number_format("total_spend") == "$#,##0.00"

    def test_percentage(self):
        assert excel_number_format("growth_pct") == "0.0%"

    def test_average(self):
        assert excel_number_format("avg_transaction") == "0.00"

    def test_general(self):
        assert excel_number_format("count") == "#,##0"


class TestHelpers:
    def test_is_currency_column(self):
        assert is_currency_column("total_amount") is True
        assert is_currency_column("spend") is True
        assert is_currency_column("count") is False

    def test_is_percentage_column(self):
        assert is_percentage_column("pct_change") is True
        assert is_percentage_column("penetration_rate") is True
        assert is_percentage_column("count") is False

    def test_is_grand_total_row(self):
        assert is_grand_total_row("Grand Total") is True
        assert is_grand_total_row("total") is True
        assert is_grand_total_row("  All  ") is True
        assert is_grand_total_row("Walmart") is False
