"""Tests for client_registry.py -- master config loading."""

import json

import pytest
import yaml

from ics_toolkit.client_registry import (
    MasterClientConfig,
    get_client_config,
    load_master_config,
    resolve_master_config_path,
)

# ---------------------------------------------------------------------------
# MasterClientConfig model
# ---------------------------------------------------------------------------


class TestMasterClientConfig:
    def test_basic_fields(self):
        cfg = MasterClientConfig(
            open_stat_codes=["A"],
            interchange_rate=0.0195,
            client_name="Test CU",
        )
        assert cfg.open_stat_codes == ["A"]
        assert cfg.interchange_rate == 0.0195
        assert cfg.client_name == "Test CU"

    def test_extra_fields_ignored(self):
        """ARS-only fields don't cause validation errors."""
        cfg = MasterClientConfig(
            open_stat_codes=["O"],
            eligible_stat_code="O",
            eligible_prod_code="100",
            eligible_mailable="Y",
            reg_e_opt_in="Y",
        )
        assert cfg.open_stat_codes == ["O"]

    def test_branch_mapping(self):
        cfg = MasterClientConfig(
            branch_mapping={"01": "Main Office", "02": "North Branch"},
        )
        assert cfg.branch_mapping["01"] == "Main Office"
        assert len(cfg.branch_mapping) == 2

    def test_prod_code_mapping(self):
        cfg = MasterClientConfig(
            prod_code_mapping={"100": "Regular Checking", "200": "Savings"},
        )
        assert cfg.prod_code_mapping["100"] == "Regular Checking"

    def test_all_none_defaults(self):
        cfg = MasterClientConfig()
        assert cfg.open_stat_codes is None
        assert cfg.closed_stat_codes is None
        assert cfg.interchange_rate is None
        assert cfg.branch_mapping is None
        assert cfg.prod_code_mapping is None
        assert cfg.client_name is None

    def test_frozen(self):
        cfg = MasterClientConfig(open_stat_codes=["O"])
        with pytest.raises(Exception):
            cfg.open_stat_codes = ["A"]

    def test_ars_key_normalization_branch_mapping(self):
        """BranchMapping -> branch_mapping."""
        cfg = MasterClientConfig(BranchMapping={"01": "Main"})
        assert cfg.branch_mapping == {"01": "Main"}

    def test_ars_key_normalization_ic_rate(self):
        """ICRate -> interchange_rate."""
        cfg = MasterClientConfig(ICRate=0.025)
        assert cfg.interchange_rate == 0.025

    def test_ars_key_normalization_nsf_od_fee(self):
        """NSF_OD_Fee is normalized but not consumed (extra=ignore)."""
        cfg = MasterClientConfig(NSF_OD_Fee=25.0)
        # nsf_od_fee is not a field on the model, so it's ignored
        assert cfg.interchange_rate is None

    def test_snake_case_takes_priority_over_ars(self):
        """If both snake_case and ARS key exist, snake_case wins."""
        cfg = MasterClientConfig(
            interchange_rate=0.018,
            ICRate=0.025,
        )
        assert cfg.interchange_rate == 0.018


# ---------------------------------------------------------------------------
# resolve_master_config_path
# ---------------------------------------------------------------------------


class TestResolveMasterConfigPath:
    def test_explicit_path_found(self, tmp_path):
        f = tmp_path / "clients.json"
        f.write_text("{}")
        result = resolve_master_config_path(explicit_path=f)
        assert result == f

    def test_explicit_path_not_found(self, tmp_path):
        result = resolve_master_config_path(explicit_path=tmp_path / "missing.json")
        assert result is None

    def test_env_var_found(self, tmp_path, monkeypatch):
        f = tmp_path / "clients.json"
        f.write_text("{}")
        monkeypatch.setenv("ICS_CLIENT_CONFIG", str(f))
        result = resolve_master_config_path()
        assert result == f

    def test_env_var_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ICS_CLIENT_CONFIG", str(tmp_path / "nope.json"))
        result = resolve_master_config_path()
        assert result is None

    def test_no_config_returns_none(self, monkeypatch):
        monkeypatch.delenv("ICS_CLIENT_CONFIG", raising=False)
        result = resolve_master_config_path()
        # On dev machines without M drive, returns None
        assert result is None or result.exists()

    def test_explicit_takes_priority_over_env(self, tmp_path, monkeypatch):
        explicit_file = tmp_path / "explicit.json"
        explicit_file.write_text("{}")
        env_file = tmp_path / "env.json"
        env_file.write_text("{}")
        monkeypatch.setenv("ICS_CLIENT_CONFIG", str(env_file))
        result = resolve_master_config_path(explicit_path=explicit_file)
        assert result == explicit_file


# ---------------------------------------------------------------------------
# load_master_config
# ---------------------------------------------------------------------------


class TestLoadMasterConfig:
    def test_load_json(self, tmp_path):
        data = {
            "1776": {"open_stat_codes": ["O"], "interchange_rate": 0.018},
            "1759": {"open_stat_codes": ["A"]},
        }
        f = tmp_path / "clients.json"
        f.write_text(json.dumps(data))
        result = load_master_config(f)
        assert len(result) == 2
        assert result["1776"].open_stat_codes == ["O"]
        assert result["1776"].interchange_rate == 0.018
        assert result["1759"].open_stat_codes == ["A"]

    def test_load_yaml(self, tmp_path):
        data = {"1776": {"open_stat_codes": ["O"], "client_name": "Liberty CU"}}
        f = tmp_path / "clients.yaml"
        f.write_text(yaml.dump(data))
        result = load_master_config(f)
        assert len(result) == 1
        assert result["1776"].client_name == "Liberty CU"

    def test_load_yml_extension(self, tmp_path):
        data = {"1776": {"open_stat_codes": ["O"]}}
        f = tmp_path / "clients.yml"
        f.write_text(yaml.dump(data))
        result = load_master_config(f)
        assert len(result) == 1

    def test_invalid_json_returns_empty(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json{{{")
        result = load_master_config(f)
        assert result == {}

    def test_invalid_yaml_returns_empty(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  :\n    :\n      - ][")
        result = load_master_config(f)
        assert result == {}

    def test_invalid_client_entry_skipped(self, tmp_path):
        data = {"1776": {"open_stat_codes": ["O"]}, "bad": "not_a_dict"}
        f = tmp_path / "clients.json"
        f.write_text(json.dumps(data))
        result = load_master_config(f)
        assert len(result) == 1
        assert "1776" in result
        assert "bad" not in result

    def test_unsupported_format_returns_empty(self, tmp_path):
        f = tmp_path / "clients.toml"
        f.write_text("")
        result = load_master_config(f)
        assert result == {}

    def test_non_dict_root_returns_empty(self, tmp_path):
        f = tmp_path / "clients.json"
        f.write_text(json.dumps([1, 2, 3]))
        result = load_master_config(f)
        assert result == {}

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "clients.yaml"
        f.write_text("")
        result = load_master_config(f)
        assert result == {}

    def test_numeric_client_id_coerced_to_str(self, tmp_path):
        data = {1776: {"open_stat_codes": ["O"]}}
        f = tmp_path / "clients.json"
        f.write_text(json.dumps(data))
        result = load_master_config(f)
        assert "1776" in result

    def test_ars_compatible_entry(self, tmp_path):
        """Full ARS-style entry with extra fields loads correctly."""
        data = {
            "1776": {
                "eligible_stat_code": "O",
                "eligible_prod_code": "100",
                "ICRate": 0.018,
                "BranchMapping": {"01": "Main"},
                "NSF_OD_Fee": 25.0,
                "open_stat_codes": ["O"],
            }
        }
        f = tmp_path / "clients.json"
        f.write_text(json.dumps(data))
        result = load_master_config(f)
        assert result["1776"].open_stat_codes == ["O"]
        assert result["1776"].interchange_rate == 0.018
        assert result["1776"].branch_mapping == {"01": "Main"}


# ---------------------------------------------------------------------------
# get_client_config
# ---------------------------------------------------------------------------


class TestGetClientConfig:
    def test_found(self):
        registry = {"1776": MasterClientConfig(open_stat_codes=["O"])}
        result = get_client_config("1776", registry)
        assert result is not None
        assert result.open_stat_codes == ["O"]

    def test_not_found(self):
        registry = {"1776": MasterClientConfig()}
        result = get_client_config("9999", registry)
        assert result is None

    def test_strips_whitespace(self):
        registry = {"1776": MasterClientConfig(client_name="Test")}
        result = get_client_config("  1776  ", registry)
        assert result is not None
        assert result.client_name == "Test"

    def test_empty_registry(self):
        result = get_client_config("1776", {})
        assert result is None
