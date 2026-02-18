"""Tests for txn_analysis.data_loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from txn_analysis.data_loader import load_data
from txn_analysis.exceptions import ColumnMismatchError, DataLoadError
from txn_analysis.settings import Settings


class TestLoadData:
    def test_loads_sample_csv(self, sample_settings: Settings):
        df = load_data(sample_settings)
        assert len(df) > 0
        assert "merchant_consolidated" in df.columns
        assert "year_month" in df.columns
        assert "business_flag" in df.columns

    def test_merchant_consolidation_applied(self, sample_settings: Settings):
        df = load_data(sample_settings)
        consolidated = set(df["merchant_consolidated"])
        # WAL-MART #3893 should consolidate to WALMART (ALL LOCATIONS)
        assert "WALMART (ALL LOCATIONS)" in consolidated
        # NETFLIX.COM -> NETFLIX
        assert "NETFLIX" in consolidated

    def test_year_month_derived(self, sample_settings: Settings):
        df = load_data(sample_settings)
        assert df["year_month"].notna().all()
        # Sample data spans Jul-Dec 2025
        months = set(df["year_month"])
        assert "2025-07" in months
        assert "2025-12" in months

    def test_business_flag_present(self, sample_settings: Settings):
        df = load_data(sample_settings)
        flags = set(df["business_flag"])
        assert "Yes" in flags
        assert "No" in flags

    def test_business_flag_default_no(self, tmp_path: Path):
        csv = tmp_path / "no_biz.csv"
        csv.write_text(
            "merchant_name,amount,primary_account_num,transaction_date\n"
            "WALMART,10.0,ACCT001,2025-07-01\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert (df["business_flag"] == "No").all()

    def test_missing_columns_raises(self, tmp_path: Path):
        csv = tmp_path / "bad.csv"
        csv.write_text("col_a,col_b\n1,2\n")
        settings = Settings(data_file=csv, output_dir=tmp_path)
        with pytest.raises(ColumnMismatchError):
            load_data(settings)

    def test_bad_file_raises_data_load_error(self, tmp_path: Path):
        csv = tmp_path / "corrupt.csv"
        csv.write_bytes(b"\x00\x01\x02")
        settings = Settings(data_file=csv, output_dir=tmp_path)
        with pytest.raises((DataLoadError, ColumnMismatchError)):
            load_data(settings)

    def test_alias_columns_resolved(self, tmp_path: Path):
        csv = tmp_path / "aliased.csv"
        csv.write_text(
            "merchant,txn_amount,acct_num,date\n"
            "STARBUCKS,5.50,ACCT001,2025-07-01\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert "merchant_name" in df.columns
        assert "amount" in df.columns
        assert "merchant_consolidated" in df.columns

    def test_excel_file(self, tmp_path: Path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text(
            "merchant_name,amount,primary_account_num,transaction_date\n"
            "WALMART,10.0,ACCT001,2025-07-01\n"
        )
        xlsx_path = tmp_path / "data.xlsx"
        pd.read_csv(csv_path).to_excel(xlsx_path, index=False)
        settings = Settings(data_file=xlsx_path, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 1
        assert "merchant_consolidated" in df.columns

    def test_original_row_count_preserved(self, sample_settings: Settings):
        df = load_data(sample_settings)
        raw = pd.read_csv(sample_settings.data_file)
        assert len(df) == len(raw)

    def test_is_partial_month_column_added(self, sample_settings: Settings):
        df = load_data(sample_settings)
        assert "is_partial_month" in df.columns
        assert df["is_partial_month"].dtype == bool

    def test_business_flag_yes_variants(self, tmp_path: Path):
        csv = tmp_path / "biz_yes.csv"
        csv.write_text(
            "merchant_name,amount,primary_account_num,transaction_date,business_flag\n"
            "STORE,10.0,ACCT001,2025-07-01,Yes\n"
            "STORE,10.0,ACCT002,2025-07-01,y\n"
            "STORE,10.0,ACCT003,2025-07-01,TRUE\n"
            "STORE,10.0,ACCT004,2025-07-01,1\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert (df["business_flag"] == "Yes").all()

    def test_business_flag_no_variants(self, tmp_path: Path):
        csv = tmp_path / "biz_no.csv"
        csv.write_text(
            "merchant_name,amount,primary_account_num,transaction_date,business_flag\n"
            "STORE,10.0,ACCT001,2025-07-01,No\n"
            "STORE,10.0,ACCT002,2025-07-01,n\n"
            "STORE,10.0,ACCT003,2025-07-01,FALSE\n"
            "STORE,10.0,ACCT004,2025-07-01,0\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert (df["business_flag"] == "No").all()

    def test_business_flag_unmapped_defaults_no(self, tmp_path: Path):
        csv = tmp_path / "biz_unknown.csv"
        csv.write_text(
            "merchant_name,amount,primary_account_num,transaction_date,business_flag\n"
            "STORE,10.0,ACCT001,2025-07-01,UNKNOWN\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert (df["business_flag"] == "No").all()

    def test_negative_amounts_not_removed(self, tmp_path: Path):
        csv = tmp_path / "neg.csv"
        csv.write_text(
            "merchant_name,amount,primary_account_num,transaction_date\n"
            "STORE,10.0,ACCT001,2025-07-01\n"
            "STORE,-5.0,ACCT001,2025-07-02\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 2
        assert (df["amount"] < 0).any()
