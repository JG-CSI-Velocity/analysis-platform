"""Tests for formatting.py -- value formatting and Excel number formats."""

from ics_toolkit.analysis.formatting import excel_number_format, format_value


class TestFormatValue:
    def test_none_returns_empty(self):
        assert format_value(None) == ""

    def test_non_numeric_returns_string(self):
        assert format_value("Hello") == "Hello"

    def test_percentage_value(self):
        # Values stored as 0-100, displayed with % suffix
        assert format_value(75.0, "% of Total") == "75.0%"

    def test_percentage_pct_column(self):
        assert format_value(12.3, "Hit Pct") == "12.3%"

    def test_percentage_large_value(self):
        assert format_value(85.3, "% of Total") == "85.3%"

    def test_currency_dollar_sign(self):
        assert format_value(1234.56, "MTD $ Spend") == "$1,234.56"

    def test_currency_bal_column(self):
        assert format_value(50000, "Avg Bal") == "$50,000.00"

    def test_currency_spend_column(self):
        assert format_value(99.9, "MonthlySpend") == "$99.90"

    def test_ratio_column(self):
        assert format_value(3.14159, "Swipe Ratio") == "3.14"

    def test_integer_comma_formatting(self):
        assert format_value(1234567, "Count") == "1,234,567"

    def test_float_with_no_special_column(self):
        assert format_value(3.14159, "something") == "3.14"

    def test_zero_value(self):
        assert format_value(0, "Count") == "0"

    def test_negative_currency(self):
        assert format_value(-500.50, "Curr Bal") == "$-500.50"

    def test_value_error_returns_string(self):
        assert format_value("N/A", "Count") == "N/A"


class TestExcelNumberFormat:
    def test_percentage_column(self):
        assert excel_number_format("% of Total") == '0.0"%"'

    def test_pct_column(self):
        assert excel_number_format("Hit Pct") == '0.0"%"'

    def test_dollar_column(self):
        assert excel_number_format("MTD $ Spend") == "$#,##0.00"

    def test_balance_column(self):
        assert excel_number_format("Avg Bal") == "$#,##0.00"

    def test_spend_column(self):
        assert excel_number_format("MonthlySpend") == "$#,##0.00"

    def test_ratio_column(self):
        assert excel_number_format("Swipe Ratio") == "0.00"

    def test_count_column(self):
        assert excel_number_format("Account Count") == "#,##0"

    def test_total_column(self):
        assert excel_number_format("Grand Total") == "#,##0"

    def test_swipe_column(self):
        assert excel_number_format("MTD Swipes") == "#,##0"

    def test_general_column(self):
        assert excel_number_format("Category") == "General"
