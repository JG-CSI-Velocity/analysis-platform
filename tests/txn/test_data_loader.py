"""Tests for txn_analysis.data_loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from txn_analysis.data_loader import load_data, load_odd
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
        csv.write_text("merchant,txn_amount,acct_num,date\nSTARBUCKS,5.50,ACCT001,2025-07-01\n")
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

    def test_malformed_rows_skipped(self, tmp_path: Path):
        """CSV with inconsistent field counts should skip bad lines, not crash."""
        csv = tmp_path / "bad_lines.csv"
        csv.write_text(
            "merchant_name,amount,primary_account_num,transaction_date\n"
            "WALMART,10.0,ACCT001,2025-07-01\n"
            "STARBUCKS,5.50,ACCT002,2025-07-02\n"
            "BAD LINE WITH,EXTRA,FIELDS,HERE,UNEXPECTED\n"
            "TARGET,20.0,ACCT003,2025-07-03\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 3  # bad line skipped, 3 good rows kept

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


    def test_pipe_delimited_headerless(self, tmp_path: Path):
        """Pipe-delimited file with metadata first row (e.g. FNB Alaska format)."""
        csv = tmp_path / "txn_pipe.csv"
        csv.write_text(
            "1441|2/3/2026 3:30:45 PM|January 2026|16286|Monthly Transaction File|6.0.11.0\n"
            "1/15/2026|1234567890|PURCHASE|25.99|5411|WALMART|ANCHORAGE|AK|T001|M001|FNB|Y|00\n"
            "1/16/2026|1234567890|PURCHASE|12.50|5812|STARBUCKS|ANCHORAGE|AK|T002|M002|FNB|Y|00\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 2
        assert "merchant_name" in df.columns
        assert "amount" in df.columns
        assert "transaction_date" in df.columns

    def test_pipe_delimited_two_metadata_rows(self, tmp_path: Path):
        """Pipe-delimited with 2 metadata rows before data."""
        csv = tmp_path / "txn_pipe2.csv"
        csv.write_text(
            "1441|2/3/2026 3:30:45 PM|January 2026|16286|Monthly Transaction File|6.0.11.0\n"
            "Report generated for|FNB Alaska|Period|January 2026\n"
            "1/15/2026|1234567890|PURCHASE|25.99|5411|WALMART|ANCHORAGE|AK|T001|M001|FNB|Y|00\n"
            "1/16/2026|9876543210|PURCHASE|8.75|5812|CAFE|FAIRBANKS|AK|T003|M003|FNB|N|00\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 2
        assert "merchant_name" in df.columns

    def test_pipe_delimited_with_blank_line(self, tmp_path: Path):
        """Pipe-delimited with blank line between metadata and data."""
        csv = tmp_path / "txn_pipe_blank.csv"
        csv.write_text(
            "1441|2/3/2026|January 2026|16286|Monthly File|6.0\n"
            "\n"
            "1/15/2026|1234567890|PURCHASE|25.99|5411|WALMART|ANC|AK|T1|M1|FNB|Y|00\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 1
        assert "merchant_name" in df.columns

    def test_bom_prefixed_csv(self, tmp_path: Path):
        """CSV with UTF-8 BOM should parse correctly."""
        csv = tmp_path / "bom.csv"
        csv.write_bytes(
            b"\xef\xbb\xbfmerchant_name,amount,primary_account_num,transaction_date\n"
            b"WALMART,10.0,ACCT001,2025-07-01\n"
        )
        settings = Settings(data_file=csv, output_dir=tmp_path)
        df = load_data(settings)
        assert len(df) == 1
        assert "merchant_name" in df.columns


class TestLoadOdd:
    def test_load_odd_csv(self, sample_csv_path: Path, tmp_path: Path):
        odd_csv = tmp_path / "odd_data.csv"
        odd_csv.write_text(
            "Account Number,Balance,Account Holder Age,DOB\n"
            "123,500,35,1990-01-15\n"
            "456,1200,55,1970-06-20\n"
        )
        settings = Settings(data_file=sample_csv_path, output_dir=tmp_path, odd_file=odd_csv)
        df = load_odd(settings)
        assert df is not None
        assert len(df) == 2
        assert "generation" in df.columns

    def test_load_odd_none(self, sample_csv_path: Path, tmp_path: Path):
        settings = Settings(data_file=sample_csv_path, output_dir=tmp_path)
        assert load_odd(settings) is None
