"""Tests for ars_analysis.ars_config -- path resolution and migration."""

import json
from pathlib import Path

import pytest

from ars_analysis.ars_config import (
    ARS_BASE,
    ARCHIVE_PATH,
    CONFIG_PATH,
    PRESENTATIONS_PATH,
    TEMPLATE_PATH,
    _get_base,
    migrate_config,
)


class TestPathResolution:
    def test_ars_base_is_path(self):
        assert isinstance(ARS_BASE, Path)

    def test_derived_paths_under_base(self):
        assert str(PRESENTATIONS_PATH).startswith(str(ARS_BASE))
        assert str(ARCHIVE_PATH).startswith(str(ARS_BASE))
        assert str(CONFIG_PATH).startswith(str(ARS_BASE))

    def test_template_path_is_path(self):
        assert isinstance(TEMPLATE_PATH, Path)

    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ARS_BASE", str(tmp_path))
        result = _get_base()
        assert result == tmp_path


class TestMigrateConfig:
    def test_merge_new_entries(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARS_BASE", str(tmp_path))
        config_dir = tmp_path / "Config"
        config_dir.mkdir()
        config_file = config_dir / "clients_config.json"
        config_file.write_text(json.dumps({"existing": {"name": "Test"}}))

        old = tmp_path / "old_config.json"
        old.write_text(json.dumps({"new_client": {"name": "New", "ICRate": 0.005}}))

        # Re-import to pick up new ARS_BASE
        import importlib

        import ars_analysis.ars_config as cfg_mod

        importlib.reload(cfg_mod)

        result = cfg_mod.migrate_config(old)
        assert "new_client" in result
        assert "existing" in result

    def test_missing_old_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            migrate_config(tmp_path / "nonexistent.json")
