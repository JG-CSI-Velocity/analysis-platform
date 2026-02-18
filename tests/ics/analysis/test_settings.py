"""Tests for settings.py -- Pydantic configuration."""

from pathlib import Path

import pytest
import yaml

from ics_toolkit.exceptions import ConfigError
from ics_toolkit.settings import (
    BRAND_COLORS,
    AnalysisSettings,
    ChartConfig,
    OutputConfig,
    Settings,
)


class TestAnalysisSettings:
    def test_direct_construction_with_valid_file(self, tmp_path):
        data_file = tmp_path / "test.csv"
        data_file.write_text("col1,col2\n1,2\n")

        s = AnalysisSettings(data_file=data_file)
        assert s.data_file == data_file
        assert s.client_id == "unknown"

    def test_for_analysis_with_valid_file(self, tmp_path):
        data_file = tmp_path / "test.csv"
        data_file.write_text("col1,col2\n1,2\n")

        unified = Settings.for_analysis(data_file=data_file)
        assert unified.analysis.data_file == data_file
        assert unified.analysis.client_id == "unknown"

    def test_extracts_client_id(self, tmp_path):
        data_file = tmp_path / "1453-test.csv"
        data_file.write_text("col1,col2\n1,2\n")

        s = AnalysisSettings(data_file=data_file)
        assert s.client_id == "1453"
        assert s.client_name == "Client 1453"

    def test_invalid_file_raises(self, tmp_path):
        data_file = tmp_path / "nonexistent.csv"

        with pytest.raises((ConfigError, Exception)):
            Settings.for_analysis(data_file=data_file)

    def test_unsupported_type_raises(self, tmp_path):
        data_file = tmp_path / "test.json"
        data_file.write_text("{}")

        with pytest.raises((ConfigError, Exception)):
            Settings.for_analysis(data_file=data_file)

    def test_from_yaml_with_overrides(self, tmp_path):
        data_file = tmp_path / "test.csv"
        data_file.write_text("col1,col2\n1,2\n")

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "analysis": {
                        "data_file": str(data_file),
                        "client_id": "1234",
                    },
                }
            )
        )

        unified = Settings.from_yaml(config_path=config_path)
        assert unified.analysis.client_id == "1234"

    def test_from_yaml_missing_config_uses_defaults(self, tmp_path):
        config_path = tmp_path / "nonexistent.yaml"
        unified = Settings.from_yaml(config_path=config_path)
        assert unified.analysis.output_dir == Path("output/")

    def test_defaults(self, tmp_path):
        data_file = tmp_path / "test.csv"
        data_file.write_text("col1,col2\n1,2\n")

        s = AnalysisSettings(data_file=data_file)
        assert s.cohort_start is None
        assert s.ics_not_in_dump == 0
        assert s.outputs.excel is True
        assert s.outputs.powerpoint is True
        assert s.charts.theme == "plotly_white"
        assert s.charts.colors == BRAND_COLORS
        assert s.charts.scale == 3
        assert s.last_12_months == []

    def test_not_frozen(self, tmp_path):
        """AnalysisSettings is a regular BaseModel, not frozen."""
        data_file = tmp_path / "test.csv"
        data_file.write_text("col1,col2\n1,2\n")

        s = AnalysisSettings(data_file=data_file)
        s.client_name = "New Name"
        assert s.client_name == "New Name"


class TestChartConfig:
    def test_defaults(self):
        c = ChartConfig()
        assert c.width == 900
        assert c.height == 500
        assert c.scale == 3


class TestOutputConfig:
    def test_defaults(self):
        o = OutputConfig()
        assert o.excel is True
        assert o.powerpoint is True
        assert o.html_charts is False
