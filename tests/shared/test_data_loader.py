"""Tests for shared.data_loader module."""

import pandas as pd
import pytest

from shared.data_loader import _read_file, load_odd, load_tran


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "test.csv"
    df = pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})
    df.to_csv(p, index=False)
    return p


@pytest.fixture
def xlsx_file(tmp_path):
    p = tmp_path / "test.xlsx"
    df = pd.DataFrame({"col_a": [10, 20], "col_b": ["a", "b"]})
    df.to_excel(p, index=False)
    return p


@pytest.fixture
def tab_file(tmp_path):
    p = tmp_path / "transactions.csv"
    p.write_text(
        "merchant_name\tamount\ttransaction_date\tprimary_account_num\n"
        "WALMART\t25.50\t2025-01-15\t1001\n"
        "TARGET\t-12.00\t2025-01-16\t1002\n"
    )
    return p


class TestReadFile:
    def test_csv(self, csv_file):
        df = _read_file(csv_file)
        assert len(df) == 2
        assert list(df.columns) == ["col_a", "col_b"]

    def test_xlsx(self, xlsx_file):
        df = _read_file(xlsx_file)
        assert len(df) == 2
        assert list(df.columns) == ["col_a", "col_b"]

    def test_unsupported_format(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported file format"):
            _read_file(p)


class TestLoadOdd:
    def test_returns_dataframe(self, xlsx_file):
        df = load_odd(xlsx_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2


class TestLoadTran:
    def test_parses_amount_as_numeric(self, tab_file):
        df = load_tran(tab_file)
        assert df["amount"].dtype in ("float64", "int64")
        assert df["amount"].iloc[0] == 25.50

    def test_parses_transaction_date(self, tab_file):
        df = load_tran(tab_file)
        assert pd.api.types.is_datetime64_any_dtype(df["transaction_date"])

    def test_strips_column_whitespace(self, tmp_path):
        p = tmp_path / "tran.csv"
        p.write_text(" merchant_name \t amount \nSTORE\t10\n")
        df = load_tran(p)
        assert "merchant_name" in df.columns
        assert "amount" in df.columns
