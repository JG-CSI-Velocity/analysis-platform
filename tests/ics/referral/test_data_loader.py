"""Tests for referral data loader."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.exceptions import DataError
from ics_toolkit.referral.column_map import REQUIRED_COLUMNS
from ics_toolkit.referral.data_loader import (
    _parse_dates,
    _read_file,
    _resolve_aliases,
    _validate_columns,
    _validate_primary_key,
    load_referral_data,
)
from ics_toolkit.settings import ReferralSettings


class TestLoadReferralData:
    """Integration tests for the full load pipeline."""

    def test_loads_xlsx(self, sample_referral_settings):
        df = load_referral_data(sample_referral_settings)
        assert len(df) == 50
        for col in REQUIRED_COLUMNS:
            assert col in df.columns

    def test_issue_date_is_datetime(self, sample_referral_settings):
        df = load_referral_data(sample_referral_settings)
        assert pd.api.types.is_datetime64_any_dtype(df["Issue Date"])

    def test_raises_on_no_file(self):
        settings = ReferralSettings()
        with pytest.raises(DataError, match="No referral data file"):
            load_referral_data(settings)

    def test_loads_csv(self, tmp_path, sample_referral_df):
        csv_path = tmp_path / "test.csv"
        sample_referral_df.to_csv(csv_path, index=False)
        settings = ReferralSettings(data_file=csv_path, output_dir=tmp_path / "out")
        df = load_referral_data(settings)
        assert len(df) == 50


class TestReadFile:
    """Tests for file format detection."""

    def test_reads_xlsx(self, tmp_path, sample_referral_df):
        path = tmp_path / "test.xlsx"
        sample_referral_df.to_excel(path, index=False, engine="openpyxl")
        df = _read_file(path)
        assert len(df) == 50

    def test_reads_csv(self, tmp_path, sample_referral_df):
        path = tmp_path / "test.csv"
        sample_referral_df.to_csv(path, index=False)
        df = _read_file(path)
        assert len(df) == 50

    def test_rejects_unsupported_format(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text("{}")
        with pytest.raises(DataError, match="Unsupported file type"):
            _read_file(path)

    def test_header_row_offset(self, tmp_path, sample_referral_df):
        path = tmp_path / "test_offset.xlsx"
        # Write with a blank row above by prepending a row
        df_with_header = pd.concat(
            [
                pd.DataFrame(
                    [[""] * len(sample_referral_df.columns)], columns=sample_referral_df.columns
                ),
                sample_referral_df,
            ],
            ignore_index=True,
        )
        df_with_header.to_excel(path, index=False, engine="openpyxl")
        df = _read_file(path, header_row=1)
        assert len(df) == 50


class TestResolveAliases:
    """Tests for column alias resolution."""

    def test_resolves_snake_case_aliases(self):
        df = pd.DataFrame(
            {
                "referrer_name": ["A"],
                "issue_date": ["2025-01-01"],
                "referral_code": ["X"],
                "purchase_manager": ["S"],
                "branch": ["1"],
                "account_holder": ["B"],
                "mrdb_account_hash": ["H"],
                "cert_id": ["C"],
            }
        )
        result = _resolve_aliases(df)
        for col in REQUIRED_COLUMNS:
            assert col in result.columns, f"Missing: {col}"

    def test_preserves_canonical_columns(self, sample_referral_df):
        result = _resolve_aliases(sample_referral_df)
        for col in REQUIRED_COLUMNS:
            assert col in result.columns

    def test_mixed_aliases_and_canonical(self):
        df = pd.DataFrame(
            {
                "Referrer Name": ["A"],
                "issue_date": ["2025-01-01"],
                "Referral Code": ["X"],
                "staff": ["S"],
                "Branch": ["1"],
                "Account Holder": ["B"],
                "mrdb": ["H"],
                "Cert ID": ["C"],
            }
        )
        result = _resolve_aliases(df)
        for col in REQUIRED_COLUMNS:
            assert col in result.columns, f"Missing: {col}"


class TestValidateColumns:
    """Tests for required column validation."""

    def test_passes_with_all_columns(self, tmp_path, sample_referral_df):
        _validate_columns(sample_referral_df, tmp_path / "test.xlsx")

    def test_fails_on_missing_column(self, tmp_path):
        df = pd.DataFrame({"Referrer Name": ["A"], "Issue Date": ["2025-01-01"]})
        with pytest.raises(DataError, match="Missing required columns"):
            _validate_columns(df, tmp_path / "test.xlsx")


class TestValidatePrimaryKey:
    """Tests for MRDB Account Hash validation."""

    def test_passes_with_valid_pks(self, sample_referral_df):
        result = _validate_primary_key(sample_referral_df)
        assert len(result) == 50

    def test_drops_null_pks(self, sample_referral_df):
        df = sample_referral_df.copy()
        df.loc[0, "MRDB Account Hash"] = None
        df.loc[1, "MRDB Account Hash"] = None
        result = _validate_primary_key(df)
        assert len(result) == 48

    def test_raises_on_all_null_pks(self):
        df = pd.DataFrame(
            {
                "MRDB Account Hash": [None, None, None],
                "Other": [1, 2, 3],
            }
        )
        with pytest.raises(DataError, match="All rows have null MRDB Account Hash"):
            _validate_primary_key(df)


class TestParseDates:
    """Tests for Issue Date parsing."""

    def test_parses_valid_dates(self, sample_referral_df):
        result = _parse_dates(sample_referral_df)
        assert pd.api.types.is_datetime64_any_dtype(result["Issue Date"])

    def test_coerces_bad_dates_to_nat(self):
        df = pd.DataFrame({"Issue Date": ["2025-01-01", "not-a-date", "2025-03-15"]})
        result = _parse_dates(df)
        assert result["Issue Date"].isna().sum() == 1

    def test_handles_all_nat(self):
        df = pd.DataFrame({"Issue Date": ["bad1", "bad2"]})
        result = _parse_dates(df)
        assert result["Issue Date"].isna().sum() == 2
