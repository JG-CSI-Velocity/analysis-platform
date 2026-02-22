"""Tests for ODD format validation and ICS readiness checks."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from shared.format_odd import (
    ARS_SIGNATURE_COLUMNS,
    ARS_SIGNATURE_THRESHOLD,
    ICS_REQUIRED_COLUMNS,
    ICS_REQUIRED_THRESHOLD,
    FormatStatus,
    check_ics_ready,
    check_odd_formatted,
    format_odd,
)


@pytest.fixture()
def raw_odd_xlsx(tmp_path: Path) -> Path:
    """Minimal raw (unformatted) ODD Excel file."""
    df = pd.DataFrame(
        {
            "Acct Number": ["001", "002"],
            "Stat Code": ["O", "O"],
            "Date Opened": ["2020-01-15", "2019-06-01"],
            "DOB": ["1990-05-20", "1985-11-03"],
            "Jan25 PIN $": [100.0, 200.0],
            "Jan25 Sig $": [50.0, 100.0],
            "Jan25 PIN #": [5, 10],
            "Jan25 Sig #": [3, 7],
            "Jan25 Mail": ["NU", "TH-10"],
            "Jan25 Resp": ["NU 5+", "NU 1-4"],
        }
    )
    path = tmp_path / "9999-ODD.xlsx"
    df.to_excel(path, index=False)
    return path


@pytest.fixture()
def formatted_odd_xlsx(raw_odd_xlsx: Path) -> Path:
    """Formatted ODD Excel file (ran through format_odd)."""
    df = pd.read_excel(raw_odd_xlsx)
    df = format_odd(df)
    path = raw_odd_xlsx.parent / "9999-ODD-fmt.xlsx"
    df.to_excel(path, index=False)
    return path


@pytest.fixture()
def ics_ready_xlsx(formatted_odd_xlsx: Path) -> Path:
    """Formatted ODD with ICS columns appended."""
    df = pd.read_excel(formatted_odd_xlsx)
    df["ICS Account"] = ["Yes", "No"]
    df["ICS Source"] = ["REF", ""]
    path = formatted_odd_xlsx.parent / "9999-ODD-ics.xlsx"
    df.to_excel(path, index=False)
    return path


class TestCheckOddFormatted:
    def test_raw_file_is_unformatted(self, raw_odd_xlsx: Path) -> None:
        result = check_odd_formatted(raw_odd_xlsx)
        assert result.is_formatted is False
        assert len(result.missing_columns) >= ARS_SIGNATURE_THRESHOLD

    def test_formatted_file_is_formatted(self, formatted_odd_xlsx: Path) -> None:
        result = check_odd_formatted(formatted_odd_xlsx)
        assert result.is_formatted is True
        assert len(result.found_columns) >= ARS_SIGNATURE_THRESHOLD

    def test_returns_frozen_dataclass(self, raw_odd_xlsx: Path) -> None:
        result = check_odd_formatted(raw_odd_xlsx)
        assert isinstance(result, FormatStatus)
        with pytest.raises(AttributeError):
            result.is_formatted = True  # type: ignore[misc]

    def test_found_columns_are_signature_subset(self, formatted_odd_xlsx: Path) -> None:
        result = check_odd_formatted(formatted_odd_xlsx)
        for col in result.found_columns:
            assert col in ARS_SIGNATURE_COLUMNS

    def test_found_plus_missing_equals_all(self, raw_odd_xlsx: Path) -> None:
        result = check_odd_formatted(raw_odd_xlsx)
        assert set(result.found_columns) | set(result.missing_columns) == set(
            ARS_SIGNATURE_COLUMNS
        )

    def test_checked_path_recorded(self, raw_odd_xlsx: Path) -> None:
        result = check_odd_formatted(raw_odd_xlsx)
        assert result.checked_path == str(raw_odd_xlsx)


class TestCheckIcsReady:
    def test_no_ics_columns_not_ready(self, formatted_odd_xlsx: Path) -> None:
        result = check_ics_ready(formatted_odd_xlsx)
        assert result.is_formatted is False
        assert "ICS Account" in result.missing_columns
        assert "ICS Source" in result.missing_columns

    def test_both_columns_present_is_ready(self, ics_ready_xlsx: Path) -> None:
        result = check_ics_ready(ics_ready_xlsx)
        assert result.is_formatted is True
        assert len(result.found_columns) == 2

    def test_only_one_column_not_ready(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"Acct Number": ["001"], "ICS Account": ["Yes"]})
        path = tmp_path / "partial.xlsx"
        df.to_excel(path, index=False)
        result = check_ics_ready(path)
        assert result.is_formatted is False
        assert "ICS Source" in result.missing_columns

    def test_found_plus_missing_equals_all(self, formatted_odd_xlsx: Path) -> None:
        result = check_ics_ready(formatted_odd_xlsx)
        assert set(result.found_columns) | set(result.missing_columns) == set(
            ICS_REQUIRED_COLUMNS
        )


class TestCheckOddFormattedCSV:
    def test_raw_csv_is_unformatted(self, tmp_path: Path) -> None:
        path = tmp_path / "raw.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Acct Number", "Stat Code", "Jan25 PIN $"])
            writer.writerow(["001", "O", "100"])
        result = check_odd_formatted(path)
        assert result.is_formatted is False

    def test_formatted_csv_is_detected(self, tmp_path: Path) -> None:
        path = tmp_path / "formatted.csv"
        cols = list(ARS_SIGNATURE_COLUMNS) + ["Acct Number"]
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerow(["100", "50", "1-5", "35", "SO-SR", "001"])
        result = check_odd_formatted(path)
        assert result.is_formatted is True


class TestCheckErrors:
    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            check_odd_formatted("/nonexistent/file.xlsx")

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported"):
            check_odd_formatted(path)


class TestConstants:
    def test_ars_threshold_is_sensible(self) -> None:
        assert 2 <= ARS_SIGNATURE_THRESHOLD <= len(ARS_SIGNATURE_COLUMNS)

    def test_ics_threshold_is_sensible(self) -> None:
        assert ICS_REQUIRED_THRESHOLD == len(ICS_REQUIRED_COLUMNS)

    def test_all_column_names_are_strings(self) -> None:
        for col in ARS_SIGNATURE_COLUMNS:
            assert isinstance(col, str) and len(col) > 0
        for col in ICS_REQUIRED_COLUMNS:
            assert isinstance(col, str) and len(col) > 0
