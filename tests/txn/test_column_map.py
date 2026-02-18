"""Tests for txn_analysis.column_map."""

from __future__ import annotations

import pandas as pd
import pytest

from txn_analysis.column_map import (
    COLUMN_ALIASES,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    resolve_columns,
)
from txn_analysis.exceptions import ColumnMismatchError


class TestConstants:
    def test_required_columns(self):
        assert REQUIRED_COLUMNS == {
            "merchant_name",
            "amount",
            "primary_account_num",
            "transaction_date",
        }

    def test_optional_columns(self):
        assert "mcc_code" in OPTIONAL_COLUMNS
        assert "business_flag" in OPTIONAL_COLUMNS
        assert "year_month" in OPTIONAL_COLUMNS

    def test_aliases_cover_all_required(self):
        canonical = set(COLUMN_ALIASES.values())
        assert REQUIRED_COLUMNS.issubset(canonical)

    def test_aliases_cover_all_optional(self):
        canonical = set(COLUMN_ALIASES.values())
        assert OPTIONAL_COLUMNS.issubset(canonical)


class TestResolveColumns:
    def test_already_canonical(self):
        df = pd.DataFrame(
            {
                "merchant_name": ["A"],
                "amount": [1.0],
                "primary_account_num": ["X"],
                "transaction_date": ["2025-01-01"],
            }
        )
        result = resolve_columns(df)
        assert list(result.columns) == [
            "merchant_name",
            "amount",
            "primary_account_num",
            "transaction_date",
        ]

    def test_alias_renaming(self):
        df = pd.DataFrame(
            {
                "merchant": ["A"],
                "txn_amount": [1.0],
                "acct_num": ["X"],
                "date": ["2025-01-01"],
            }
        )
        result = resolve_columns(df)
        assert "merchant_name" in result.columns
        assert "amount" in result.columns
        assert "primary_account_num" in result.columns
        assert "transaction_date" in result.columns

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Merchant_Name": ["A"],
                "Amount": [1.0],
                "Primary_Account_Num": ["X"],
                "Transaction_Date": ["2025-01-01"],
            }
        )
        result = resolve_columns(df)
        assert "merchant_name" in result.columns

    def test_missing_column_raises(self):
        df = pd.DataFrame(
            {
                "merchant_name": ["A"],
                "amount": [1.0],
                # missing primary_account_num and transaction_date
            }
        )
        with pytest.raises(ColumnMismatchError) as exc_info:
            resolve_columns(df)
        assert "primary_account_num" in exc_info.value.missing
        assert "transaction_date" in exc_info.value.missing

    def test_extra_columns_preserved(self):
        df = pd.DataFrame(
            {
                "merchant_name": ["A"],
                "amount": [1.0],
                "primary_account_num": ["X"],
                "transaction_date": ["2025-01-01"],
                "custom_col": ["Z"],
            }
        )
        result = resolve_columns(df)
        assert "custom_col" in result.columns

    def test_optional_columns_resolved(self):
        df = pd.DataFrame(
            {
                "merchant_name": ["A"],
                "amount": [1.0],
                "primary_account_num": ["X"],
                "transaction_date": ["2025-01-01"],
                "mcc": [5411],
                "is_business": ["Yes"],
            }
        )
        result = resolve_columns(df)
        assert "mcc_code" in result.columns
        assert "business_flag" in result.columns

    def test_hyphenated_column(self):
        df = pd.DataFrame(
            {
                "merchant-name": ["A"],
                "amount": [1.0],
                "primary-account-num": ["X"],
                "transaction-date": ["2025-01-01"],
            }
        )
        result = resolve_columns(df)
        assert "merchant_name" in result.columns

    def test_error_includes_available(self):
        df = pd.DataFrame({"foo": [1], "bar": [2]})
        with pytest.raises(ColumnMismatchError) as exc_info:
            resolve_columns(df)
        assert "foo" in exc_info.value.available
