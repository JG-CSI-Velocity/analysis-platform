"""Tests for txn_analysis.v4_data_loader -- helper functions and constants."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from txn_analysis.v4_data_loader import (
    BALANCE_TIERS,
    GENERATION_BINS,
    ODD_TIMESERIES_PATTERNS,
    TRANSACTION_COLUMNS,
    _assign_balance_tier,
    _assign_generation,
    _detect_timeseries_columns,
    _is_year_folder,
    _parse_file_date,
    load_config,
    merge_data,
)


class TestConstants:
    def test_transaction_columns_count(self):
        assert len(TRANSACTION_COLUMNS) == 13

    def test_transaction_columns_first(self):
        assert TRANSACTION_COLUMNS[0] == "transaction_date"

    def test_generation_bins(self):
        assert len(GENERATION_BINS) == 5
        assert GENERATION_BINS[0][2] == "Gen Z"
        assert GENERATION_BINS[-1][2] == "Silent"

    def test_balance_tiers(self):
        assert len(BALANCE_TIERS) == 4
        assert BALANCE_TIERS[0][2] == "Low"
        assert BALANCE_TIERS[-1][2] == "Very High"

    def test_timeseries_patterns(self):
        assert "spend" in ODD_TIMESERIES_PATTERNS
        assert "pin_dollar" in ODD_TIMESERIES_PATTERNS
        assert "sig_count" in ODD_TIMESERIES_PATTERNS


class TestIsYearFolder:
    def test_valid_year_folder(self, tmp_path):
        year_dir = tmp_path / "2025"
        year_dir.mkdir()
        assert _is_year_folder(year_dir) is True

    def test_non_year_name(self, tmp_path):
        other = tmp_path / "data"
        other.mkdir()
        assert _is_year_folder(other) is False

    def test_file_not_dir(self, tmp_path):
        f = tmp_path / "2025"
        f.write_text("file")
        assert _is_year_folder(f) is False

    def test_short_number(self, tmp_path):
        d = tmp_path / "25"
        d.mkdir()
        assert _is_year_folder(d) is False


class TestParseFileDate:
    def test_valid_date(self, tmp_path):
        f = tmp_path / "1453-trans-01012025.csv"
        f.touch()
        result = _parse_file_date(f)
        assert result == datetime(2025, 1, 1)

    def test_another_date(self, tmp_path):
        f = tmp_path / "1759-trans-12152024.csv"
        f.touch()
        result = _parse_file_date(f)
        assert result == datetime(2024, 12, 15)

    def test_no_date_pattern(self, tmp_path):
        f = tmp_path / "transactions.csv"
        f.touch()
        assert _parse_file_date(f) is None

    def test_wrong_format(self, tmp_path):
        f = tmp_path / "1453-data-2025.csv"
        f.touch()
        assert _parse_file_date(f) is None


class TestAssignGeneration:
    @pytest.mark.parametrize(
        "age, expected",
        [
            (20, "Gen Z"),
            (12, "Gen Z"),
            (27, "Gen Z"),
            (28, "Millennial"),
            (35, "Millennial"),
            (43, "Millennial"),
            (44, "Gen X"),
            (55, "Gen X"),
            (60, "Boomer"),
            (75, "Boomer"),
            (80, "Silent"),
            (100, "Silent"),
        ],
    )
    def test_valid_ages(self, age, expected):
        assert _assign_generation(age) == expected

    def test_invalid_age(self):
        assert _assign_generation("N/A") is None

    def test_none(self):
        assert _assign_generation(None) is None

    def test_out_of_range(self):
        assert _assign_generation(5) is None


class TestAssignBalanceTier:
    @pytest.mark.parametrize(
        "balance, expected",
        [
            (-100, "Low"),
            (0, "Low"),
            (499, "Low"),
            (500, "Medium"),
            (1500, "Medium"),
            (2000, "High"),
            (9999, "High"),
            (10000, "Very High"),
            (100000, "Very High"),
        ],
    )
    def test_valid_balances(self, balance, expected):
        assert _assign_balance_tier(balance) == expected

    def test_invalid_input(self):
        assert _assign_balance_tier("N/A") is None

    def test_none_input(self):
        assert _assign_balance_tier(None) is None


class TestDetectTimeseriesColumns:
    def test_finds_spend_columns(self):
        cols = pd.Index(["Jan25 Spend", "Feb25 Spend", "Name", "Age"])
        result = _detect_timeseries_columns(cols)
        assert "spend" in result
        assert len(result["spend"]) == 2

    def test_finds_pin_dollar(self):
        cols = pd.Index(["Jan25 PIN $", "Feb25 PIN $", "Other"])
        result = _detect_timeseries_columns(cols)
        assert "pin_dollar" in result

    def test_no_timeseries(self):
        cols = pd.Index(["Name", "Age", "Balance"])
        result = _detect_timeseries_columns(cols)
        assert result == {}

    def test_multiple_series(self):
        cols = pd.Index(["Jan25 Spend", "Jan25 PIN $", "Jan25 Sig $"])
        result = _detect_timeseries_columns(cols)
        assert "spend" in result
        assert "pin_dollar" in result
        assert "sig_dollar" in result


class TestLoadConfig:
    def test_valid_yaml(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("client_id: '1234'\nclient_name: 'Test CU'\n")
        result = load_config(str(cfg))
        assert result["client_id"] == "1234"
        assert result["client_name"] == "Test CU"

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nope.yaml"))


class TestMergeData:
    def test_basic_merge(self):
        txn = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A001", "A002"],
                "amount": [100.0, 200.0, 50.0],
                "transaction_date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-01"]),
            }
        )
        odd = pd.DataFrame(
            {
                "Acct Number": ["A001", "A002"],
                "Business?": ["Yes", "No"],
                "Avg Bal": [5000, 200],
            }
        )
        combined, biz, personal = merge_data(txn, odd)
        assert len(combined) == 3
        assert len(biz) == 2
        assert len(personal) == 1

    def test_no_business_column(self):
        txn = pd.DataFrame(
            {
                "primary_account_num": ["A001"],
                "amount": [100.0],
            }
        )
        odd = pd.DataFrame({"Acct Number": ["A001"]})
        combined, biz, personal = merge_data(txn, odd)
        assert len(biz) == 0
        assert len(personal) == 1
