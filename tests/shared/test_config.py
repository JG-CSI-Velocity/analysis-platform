"""Tests for shared config loading."""

from pathlib import Path

from shared.config import PlatformConfig, _deep_merge


class TestPlatformConfig:
    def test_default_config(self):
        cfg = PlatformConfig()
        assert cfg.base_output_dir == Path("output")
        assert cfg.chart_theme == "consultant"
        assert cfg.pipelines == {}

    def test_load_missing_file(self, tmp_path):
        cfg = PlatformConfig.load(tmp_path / "nonexistent.yaml")
        assert cfg.base_output_dir == Path("output")

    def test_load_yaml(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text("base_output_dir: /tmp/out\nchart_theme: dark\n")
        cfg = PlatformConfig.load(config_file)
        assert cfg.base_output_dir == Path("/tmp/out")
        assert cfg.chart_theme == "dark"


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}
