"""Tests for ars.pipeline.utils -- ODD filename parsing and month resolution."""

import pytest

from ars_analysis.pipeline.utils import (
    current_month,
    parse_month_folder,
    parse_odd_filename,
    parse_oddd_zip,
    resolve_target_month,
)


class TestParseOddFilename:
    def test_standard_filename(self):
        result = parse_odd_filename("1453-2026-01-Connex CU-ODD.xlsx")
        assert result is not None
        assert result["client_id"] == "1453"
        assert result["year"] == "2026"
        assert result["month"] == "01"
        assert result["client_name"] == "Connex CU"
        assert result["filename"] == "1453-2026-01-Connex CU-ODD.xlsx"

    def test_hyphenated_client_name(self):
        result = parse_odd_filename("1776-2026-02-First-National CU-ODD.xlsx")
        assert result is not None
        assert result["client_name"] == "First-National CU"

    def test_non_xlsx(self):
        assert parse_odd_filename("1453-2026-01-Connex CU-ODD.csv") is None

    def test_missing_odd_suffix(self):
        assert parse_odd_filename("1453-2026-01-Connex CU.xlsx") is None

    def test_too_few_parts(self):
        assert parse_odd_filename("1453-2026-01.xlsx") is None

    def test_non_numeric_year(self):
        assert parse_odd_filename("1453-XXXX-01-Client-ODD.xlsx") is None

    def test_zero_pads_month(self):
        result = parse_odd_filename("1453-2026-1-Connex CU-ODD.xlsx")
        assert result is not None
        assert result["month"] == "01"


class TestParseMonthFolder:
    def test_numeric_format(self):
        assert parse_month_folder("2026.02") == ("2026", "02")

    def test_name_format(self):
        assert parse_month_folder("February, 2026") == ("2026", "02")

    def test_name_no_comma(self):
        assert parse_month_folder("January 2026") == ("2026", "01")

    def test_invalid_string(self):
        assert parse_month_folder("not a month") is None

    def test_empty_string(self):
        assert parse_month_folder("") is None


class TestParseOdddZip:
    def test_underscore(self):
        assert parse_oddd_zip("1453_ODDD.zip") == "1453"

    def test_hyphen(self):
        assert parse_oddd_zip("1776-ODD.zip") == "1776"

    def test_no_match(self):
        assert parse_oddd_zip("random_file.zip") is None


class TestCurrentMonth:
    def test_format(self):
        m = current_month()
        assert len(m) == 7
        assert m[4] == "."


class TestResolveTargetMonth:
    def test_explicit_month(self):
        full, year, mm = resolve_target_month("2026.02")
        assert full == "2026.02"
        assert year == "2026"
        assert mm == "02"

    def test_default_is_current(self):
        full, year, mm = resolve_target_month(None)
        assert len(full) == 7
        assert year.isdigit()
        assert mm.isdigit()

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="YYYY.MM"):
            resolve_target_month("2026-02")
