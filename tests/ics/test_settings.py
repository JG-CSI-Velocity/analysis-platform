"""Tests for settings.py -- master config integration and field expansion."""

import json

import pytest

from ics_toolkit.settings import AnalysisClientConfig, AnalysisSettings


@pytest.fixture()
def _csv_file(tmp_path):
    """Create a minimal CSV so AnalysisSettings data_file validation passes."""
    f = tmp_path / "1776-ref.csv"
    f.write_text("col1,col2\n1,2\n")
    return f


@pytest.fixture()
def _master_file(tmp_path):
    """Create a master config JSON file."""

    def _make(data: dict):
        f = tmp_path / "clients.json"
        f.write_text(json.dumps(data))
        return f

    return _make


# ---------------------------------------------------------------------------
# AnalysisClientConfig expansion
# ---------------------------------------------------------------------------


class TestAnalysisClientConfigExpansion:
    def test_new_fields_accepted(self):
        cfg = AnalysisClientConfig(
            open_stat_codes=["A"],
            interchange_rate=0.025,
            branch_mapping={"01": "Main"},
            prod_code_mapping={"100": "Checking"},
        )
        assert cfg.interchange_rate == 0.025
        assert cfg.branch_mapping == {"01": "Main"}
        assert cfg.prod_code_mapping == {"100": "Checking"}

    def test_all_none_by_default(self):
        cfg = AnalysisClientConfig()
        assert cfg.interchange_rate is None
        assert cfg.branch_mapping is None
        assert cfg.prod_code_mapping is None


# ---------------------------------------------------------------------------
# Master config -> AnalysisSettings integration
# ---------------------------------------------------------------------------


class TestMasterConfigIntegration:
    def test_applies_stat_codes(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"open_stat_codes": ["A", "O"]}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.open_stat_codes == ["A", "O"]

    def test_applies_closed_stat_codes(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"closed_stat_codes": ["C", "X"]}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.closed_stat_codes == ["C", "X"]

    def test_applies_interchange_rate(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"interchange_rate": 0.025}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.interchange_rate == 0.025

    def test_applies_client_name(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"client_name": "Liberty Federal CU"}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.client_name == "Liberty Federal CU"

    def test_applies_branch_mapping(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"branch_mapping": {"01": "Main"}}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.branch_mapping == {"01": "Main"}

    def test_applies_prod_code_mapping(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"prod_code_mapping": {"100": "Checking"}}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.prod_code_mapping == {"100": "Checking"}

    def test_config_yaml_overrides_master(self, tmp_path, _csv_file, _master_file):
        """config.yaml clients dict takes priority over master file."""
        master = _master_file({"1776": {"open_stat_codes": ["A"]}})
        s = AnalysisSettings(
            data_file=_csv_file,
            client_config_path=master,
            clients={"1776": AnalysisClientConfig(open_stat_codes=["X"])},
        )
        assert s.open_stat_codes == ["X"]

    def test_config_yaml_overrides_interchange(self, tmp_path, _csv_file, _master_file):
        master = _master_file({"1776": {"interchange_rate": 0.015}})
        s = AnalysisSettings(
            data_file=_csv_file,
            client_config_path=master,
            clients={"1776": AnalysisClientConfig(interchange_rate=0.030)},
        )
        assert s.interchange_rate == 0.030

    def test_missing_master_file_graceful(self, tmp_path, _csv_file):
        """Missing master config file does not raise."""
        s = AnalysisSettings(
            data_file=_csv_file,
            client_config_path=tmp_path / "nonexistent.json",
        )
        assert s.open_stat_codes == ["O"]  # defaults

    def test_unknown_client_uses_defaults(self, tmp_path, _master_file):
        """Client not in master file gets defaults."""
        master = _master_file({"1776": {"open_stat_codes": ["A"]}})
        # File named 9999-ref.csv -> client_id=9999, not in master
        csv = tmp_path / "9999-ref.csv"
        csv.write_text("col1,col2\n1,2\n")
        s = AnalysisSettings(data_file=csv, client_config_path=master)
        assert s.open_stat_codes == ["O"]  # default

    def test_no_client_config_path_no_io(self, _csv_file):
        """Without client_config_path, no master file loading occurs."""
        s = AnalysisSettings(data_file=_csv_file)
        assert s.open_stat_codes == ["O"]
        assert s.branch_mapping is None

    def test_client_config_path_expansion(self, tmp_path, _csv_file, _master_file):
        """Tilde paths are expanded."""
        master = _master_file({"1776": {"open_stat_codes": ["A"]}})
        s = AnalysisSettings(data_file=_csv_file, client_config_path=master)
        assert s.client_config_path.is_absolute()
