"""Tests for txn_analysis storyline adapters and module structure."""

from __future__ import annotations

import importlib

import pandas as pd
import pytest


class TestStorylineAdapters:
    """Test the storyline adapter functions in ANALYSIS_REGISTRY."""

    def test_registry_has_storyline_adapters(self):
        from txn_analysis.analyses import ANALYSIS_REGISTRY

        names = [name for name, _ in ANALYSIS_REGISTRY]
        assert "demographics" in names
        assert "campaigns" in names
        assert "payroll" in names
        assert "lifecycle" in names

    def test_adapters_are_callable(self):
        from txn_analysis.analyses.storyline_adapters import (
            analyze_campaigns,
            analyze_demographics,
            analyze_lifecycle,
            analyze_payroll,
        )

        assert callable(analyze_demographics)
        assert callable(analyze_campaigns)
        assert callable(analyze_payroll)
        assert callable(analyze_lifecycle)

    def test_registry_count(self):
        from txn_analysis.analyses import ANALYSIS_REGISTRY

        assert len(ANALYSIS_REGISTRY) == 36

    def test_scorecard_is_last(self):
        from txn_analysis.analyses import ANALYSIS_REGISTRY

        last_name, _ = ANALYSIS_REGISTRY[-1]
        assert last_name == "portfolio_scorecard"


class TestStorylineModulesImportable:
    """Test that kept storyline modules are importable with run()."""

    @pytest.mark.parametrize(
        "mod_name",
        [
            "txn_analysis.storylines.v4_s5_demographics",
            "txn_analysis.storylines.v4_s7_campaigns",
            "txn_analysis.storylines.v4_s8_payroll",
            "txn_analysis.storylines.v4_s9_lifecycle",
        ],
    )
    def test_module_has_run(self, mod_name):
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, "run")
        assert callable(mod.run)


class TestSupportModules:
    """Test shared support modules import and expose expected API."""

    def test_chart_theme_imports(self):
        from txn_analysis.charts.theme import (
            CATEGORY_PALETTE,
            COLORS,
            apply_theme,
            format_currency,
        )

        assert isinstance(COLORS, dict)
        assert isinstance(CATEGORY_PALETTE, list)
        assert callable(apply_theme)
        assert callable(format_currency)

    def test_merchant_rules_imports(self):
        from txn_analysis.merchant_rules import standardize_merchant_name

        assert callable(standardize_merchant_name)

    def test_data_loader_imports(self):
        from txn_analysis.data_loader import load_data, load_odd

        assert callable(load_data)
        assert callable(load_odd)


class TestRunnerBridge:
    """Test the runner bridge functions."""

    def test_run_txn_missing_input(self):
        from pathlib import Path

        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn

        ctx = PipelineContext(output_dir=Path("/tmp/test"))
        with pytest.raises(FileNotFoundError, match="No 'tran' or 'txn_dir'"):
            run_txn(ctx)


class TestWrapStorylineResult:
    """Test the _wrap_storyline_result helper."""

    def test_wraps_with_sheets(self):
        from txn_analysis.analyses.storyline_adapters import _wrap_storyline_result

        result_dict = {
            "title": "Test Title",
            "sections": [
                {"heading": "A", "figures": ["fig1", "fig2"], "tables": []},
                {"heading": "B", "figures": ["fig3"], "tables": []},
            ],
            "sheets": [
                {"name": "Sheet1", "df": pd.DataFrame({"x": [1, 2]})},
            ],
        }
        ar = _wrap_storyline_result("test", result_dict)
        assert ar.name == "test"
        assert ar.title == "Test Title"
        assert len(ar.df) == 2
        assert ar.metadata["section_count"] == 2
        assert ar.metadata["chart_count"] == 3
        assert ar.metadata["sheet_count"] == 1

    def test_wraps_empty_result(self):
        from txn_analysis.analyses.storyline_adapters import _wrap_storyline_result

        result_dict = {
            "title": "Empty",
            "sections": [],
            "sheets": [],
        }
        ar = _wrap_storyline_result("empty", result_dict)
        assert ar.name == "empty"
        assert ar.df.empty
        assert ar.metadata["section_count"] == 0
