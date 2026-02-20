"""Tests for data_loader.py -- data loading and cleaning."""

import pandas as pd
import pytest

from ics_toolkit.analysis.data_loader import _enrich_labels, load_data
from ics_toolkit.exceptions import DataError
from ics_toolkit.settings import AnalysisSettings as Settings


class TestLoadData:
    def test_loads_xlsx(self, sample_settings, sample_df):
        df = load_data(sample_settings)
        assert len(df) == len(sample_df)
        assert "ICS Account" in df.columns

    def test_discovers_l12m(self, sample_settings):
        load_data(sample_settings)
        assert len(sample_settings.last_12_months) == 12

    def test_normalizes_ics_account(self, tmp_path):
        df = pd.DataFrame(
            {
                "ICS Account": ["yes", "NO", "Y", "n", ""],
                "Stat Code": ["O", "O", "C", "O", "O"],
                "Debit?": ["Yes", "No", "Yes", "No", "Yes"],
                "Business?": ["No", "No", "No", "No", "No"],
                "Date Opened": ["2025-01-01"] * 5,
                "Prod Code": ["100"] * 5,
                "Branch": ["Main"] * 5,
                "Source": ["DM"] * 5,
                "Curr Bal": [100] * 5,
            }
        )
        data_file = tmp_path / "test.xlsx"
        df.to_excel(data_file, index=False, engine="openpyxl")

        settings = Settings(data_file=data_file, client_id="test")
        result = load_data(settings)

        assert list(result["ICS Account"]) == ["Yes", "No", "Yes", "No", "No"]

    def test_normalizes_stat_code(self, tmp_path):
        df = pd.DataFrame(
            {
                "ICS Account": ["Yes"] * 3,
                "Stat Code": ["o", " O ", "c"],
                "Debit?": ["Yes"] * 3,
                "Business?": ["No"] * 3,
                "Date Opened": ["2025-01-01"] * 3,
                "Prod Code": ["100"] * 3,
                "Branch": ["Main"] * 3,
                "Source": ["DM"] * 3,
                "Curr Bal": [100] * 3,
            }
        )
        data_file = tmp_path / "test.xlsx"
        df.to_excel(data_file, index=False, engine="openpyxl")

        settings = Settings(data_file=data_file, client_id="test")
        result = load_data(settings)

        assert list(result["Stat Code"]) == ["O", "O", "C"]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(Exception):
            Settings(data_file=tmp_path / "nonexistent.xlsx")

    def test_missing_required_columns_raises(self, tmp_path):
        df = pd.DataFrame({"Col1": [1], "Col2": [2]})
        data_file = tmp_path / "bad.xlsx"
        df.to_excel(data_file, index=False, engine="openpyxl")

        settings = Settings.model_construct(
            data_file=data_file,
            client_id="test",
            client_name="Test",
            output_dir=tmp_path,
            cohort_start="2025-01",
            ics_not_in_dump=0,
        )

        with pytest.raises(DataError, match="Missing required columns"):
            load_data(settings)

    def test_loads_csv(self, tmp_path, sample_df):
        data_file = tmp_path / "test.csv"
        sample_df.to_csv(data_file, index=False)

        settings = Settings(data_file=data_file, client_id="test")
        result = load_data(settings)
        assert len(result) == len(sample_df)

    def test_coerces_balance_to_numeric(self, sample_settings):
        df = load_data(sample_settings)
        assert df["Curr Bal"].dtype in ("float64", "float32")

    def test_parses_dates(self, sample_settings):
        df = load_data(sample_settings)
        assert pd.api.types.is_datetime64_any_dtype(df["Date Opened"])

    def test_stat_codes_preserved(self, tmp_path):
        """Stat codes are left as-is in the data (no remapping)."""
        df = pd.DataFrame(
            {
                "ICS Account": ["Yes"] * 3,
                "Stat Code": ["A", "A", "C"],
                "Debit?": ["Yes"] * 3,
                "Business?": ["No"] * 3,
                "Date Opened": ["2025-01-01"] * 3,
                "Prod Code": ["100"] * 3,
                "Branch": ["Main"] * 3,
                "Source": ["DM"] * 3,
                "Curr Bal": [100] * 3,
            }
        )
        data_file = tmp_path / "test.xlsx"
        df.to_excel(data_file, index=False, engine="openpyxl")

        settings = Settings(data_file=data_file, client_id="test")
        result = load_data(settings)
        assert list(result["Stat Code"]) == ["A", "A", "C"]


class TestEnrichLabels:
    def _make_df(self):
        return pd.DataFrame(
            {
                "Branch": ["01", "02", "03"],
                "Prod Code": ["100", "200", "300"],
                "Curr Bal": [1000, 2000, 3000],
            }
        )

    def _make_settings(self, **kwargs):
        defaults = {
            "data_file": None,
            "client_id": "test",
            "client_name": "Test",
            "output_dir": "output/",
            "branch_mapping": None,
            "prod_code_mapping": None,
        }
        defaults.update(kwargs)
        return Settings.model_construct(**defaults)

    def test_branch_mapping_applied(self):
        df = self._make_df()
        settings = self._make_settings(
            branch_mapping={"01": "Main Office", "02": "North Branch"},
        )
        result = _enrich_labels(df, settings)
        assert result["Branch"].tolist() == ["Main Office", "North Branch", "03"]

    def test_prod_code_mapping_applied(self):
        df = self._make_df()
        settings = self._make_settings(
            prod_code_mapping={"100": "Regular Checking", "200": "Savings"},
        )
        result = _enrich_labels(df, settings)
        assert result["Prod Code"].tolist() == ["Regular Checking", "Savings", "300"]

    def test_no_mapping_passthrough(self):
        df = self._make_df()
        settings = self._make_settings()
        result = _enrich_labels(df, settings)
        assert result["Branch"].tolist() == ["01", "02", "03"]
        assert result["Prod Code"].tolist() == ["100", "200", "300"]

    def test_partial_mapping_keeps_unmapped(self):
        df = self._make_df()
        settings = self._make_settings(branch_mapping={"01": "Main Office"})
        result = _enrich_labels(df, settings)
        assert result["Branch"].tolist() == ["Main Office", "02", "03"]

    def test_missing_column_ignored(self):
        df = pd.DataFrame({"Other": [1, 2, 3]})
        settings = self._make_settings(
            branch_mapping={"01": "Main"},
            prod_code_mapping={"100": "Checking"},
        )
        result = _enrich_labels(df, settings)
        assert "Branch" not in result.columns
