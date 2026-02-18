"""Tests for txn_analysis.settings."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from txn_analysis.exceptions import ConfigError
from txn_analysis.settings import BRAND_COLORS, ChartConfig, OutputConfig, Settings

# -- ChartConfig ---------------------------------------------------------------


class TestChartConfig:
    def test_defaults(self):
        cfg = ChartConfig()
        assert cfg.theme == "consultant"
        assert cfg.width == 900
        assert cfg.height == 500
        assert cfg.scale == 3
        assert cfg.colors == BRAND_COLORS

    def test_custom_colors(self):
        cfg = ChartConfig(colors=["#000", "#fff"])
        assert cfg.colors == ["#000", "#fff"]


# -- OutputConfig --------------------------------------------------------------


class TestOutputConfig:
    def test_defaults(self):
        cfg = OutputConfig()
        assert cfg.excel is True
        assert cfg.chart_images is True
        assert cfg.powerpoint is False
        assert cfg.html_charts is False


# -- Settings ------------------------------------------------------------------


class TestSettings:
    def test_minimal(self, sample_csv_path: Path, tmp_path: Path):
        s = Settings(data_file=sample_csv_path, output_dir=tmp_path)
        assert s.data_file == sample_csv_path.resolve()
        assert s.top_n == 50

    def test_frozen(self, sample_csv_path: Path, tmp_path: Path):
        s = Settings(data_file=sample_csv_path, output_dir=tmp_path)
        with pytest.raises(Exception):
            s.top_n = 100  # type: ignore[misc]

    def test_extra_forbidden(self, sample_csv_path: Path, tmp_path: Path):
        with pytest.raises(Exception):
            Settings(data_file=sample_csv_path, output_dir=tmp_path, bogus=1)

    def test_data_file_not_found(self, tmp_path: Path):
        with pytest.raises(Exception, match="Data file not found"):
            Settings(data_file=tmp_path / "nope.csv")

    def test_unsupported_extension(self, tmp_path: Path):
        bad = tmp_path / "data.json"
        bad.write_text("{}")
        with pytest.raises(Exception, match="Unsupported file type"):
            Settings(data_file=bad)

    def test_client_id_derived_from_filename(self, tmp_path: Path):
        csv = tmp_path / "12345_txn_data.csv"
        csv.write_text("merchant_name,amount,primary_account_num,transaction_date\n")
        s = Settings(data_file=csv)
        assert s.client_id == "12345"
        assert s.client_name == "Client 12345"

    def test_client_id_not_derived_when_no_digits(self, sample_csv_path: Path):
        # sample_transactions.csv has no leading digits
        s = Settings(data_file=sample_csv_path)
        assert s.client_id is None

    def test_explicit_client_overrides_derivation(self, tmp_path: Path):
        csv = tmp_path / "12345_txn_data.csv"
        csv.write_text("merchant_name,amount,primary_account_num,transaction_date\n")
        s = Settings(data_file=csv, client_id="ABC", client_name="Test CU")
        assert s.client_id == "ABC"
        assert s.client_name == "Test CU"

    def test_defaults_preserved(self, sample_csv_path: Path):
        s = Settings(data_file=sample_csv_path)
        assert s.growth_min_threshold == 1000.0
        assert s.consistency_min_spend == 10000.0
        assert s.consistency_min_months == 3
        assert s.threat_min_accounts == 100
        assert s.threat_min_spend == 50000.0


# -- from_yaml -----------------------------------------------------------------


class TestFromYaml:
    def test_load_yaml(self, sample_csv_path: Path, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"data_file": str(sample_csv_path), "top_n": 25}))
        s = Settings.from_yaml(cfg)
        assert s.top_n == 25

    def test_cli_override_wins(self, sample_csv_path: Path, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"data_file": str(sample_csv_path), "top_n": 25}))
        s = Settings.from_yaml(cfg, top_n=10)
        assert s.top_n == 10

    def test_missing_yaml_falls_back(self, sample_csv_path: Path, tmp_path: Path):
        s = Settings.from_yaml(tmp_path / "nope.yaml", data_file=sample_csv_path)
        assert s.data_file == sample_csv_path.resolve()

    def test_bad_yaml_raises_config_error(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"top_n": "not_a_number"}))
        with pytest.raises(ConfigError):
            Settings.from_yaml(cfg)


# -- from_args -----------------------------------------------------------------


class TestFromArgs:
    def test_simple(self, sample_csv_path: Path):
        s = Settings.from_args(data_file=sample_csv_path, top_n=30)
        assert s.top_n == 30

    def test_bad_args_raises_config_error(self, tmp_path: Path):
        with pytest.raises(ConfigError):
            Settings.from_args(data_file=tmp_path / "nope.csv")
