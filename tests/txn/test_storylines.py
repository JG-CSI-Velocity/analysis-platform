"""Tests for txn_analysis storyline modules and V4 runner."""

from __future__ import annotations

import importlib

import pandas as pd
import pytest


class TestStorylineRegistry:
    """Test the storyline registry and module structure."""

    def test_registry_has_all_storylines(self):
        from txn_analysis.storylines import STORYLINE_REGISTRY

        keys = [k for k, _ in STORYLINE_REGISTRY]
        assert len(keys) == 11
        expected = [
            "s1_portfolio",
            "s2_merchant",
            "s3_competition",
            "s3b_threats",
            "s3c_segmentation",
            "s4_finserv",
            "s5_demographics",
            "s6_risk",
            "s7_campaigns",
            "s8_payroll",
            "s9_lifecycle",
        ]
        assert keys == expected

    def test_all_storyline_modules_have_run(self):
        from txn_analysis.storylines import STORYLINE_REGISTRY

        for key, module in STORYLINE_REGISTRY:
            assert hasattr(module, "run"), f"{key} module missing run()"
            assert callable(module.run), f"{key}.run is not callable"

    def test_storyline_modules_importable(self):
        modules = [
            "txn_analysis.storylines.v4_s1_portfolio_health",
            "txn_analysis.storylines.v4_s2_merchant_intel",
            "txn_analysis.storylines.v4_s3_competition",
            "txn_analysis.storylines.v4_s3_threat_analysis",
            "txn_analysis.storylines.v4_s3_segmentation",
            "txn_analysis.storylines.v4_s4_finserv",
            "txn_analysis.storylines.v4_s5_demographics",
            "txn_analysis.storylines.v4_s6_risk",
            "txn_analysis.storylines.v4_s7_campaigns",
            "txn_analysis.storylines.v4_s8_payroll",
            "txn_analysis.storylines.v4_s9_lifecycle",
        ]
        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            assert hasattr(mod, "run")


class TestV4SupportModules:
    """Test V4 support modules import and expose expected API."""

    def test_v4_themes_imports(self):
        from txn_analysis.v4_themes import (
            CATEGORY_PALETTE,
            COLORS,
            apply_theme,
            format_currency,
        )

        assert isinstance(COLORS, dict)
        assert isinstance(CATEGORY_PALETTE, list)
        assert callable(apply_theme)
        assert callable(format_currency)

    def test_v4_merchant_rules_imports(self):
        from txn_analysis.v4_merchant_rules import standardize_merchant_name

        assert callable(standardize_merchant_name)

    def test_v4_data_loader_imports(self):
        from txn_analysis.v4_data_loader import load_all, load_config

        assert callable(load_config)
        assert callable(load_all)

    def test_v4_html_report_imports(self):
        from txn_analysis.v4_html_report import build_kpi_html

        assert callable(build_kpi_html)

    def test_v4_excel_report_imports(self):
        from txn_analysis.v4_excel_report import generate_excel_report

        assert callable(generate_excel_report)

    def test_v4_run_imports(self):
        from txn_analysis.v4_run import (
            ALL_STORYLINES,
            STORYLINE_LABELS,
            run_pipeline,
        )

        assert callable(run_pipeline)
        assert len(ALL_STORYLINES) == 11
        assert len(STORYLINE_LABELS) == 11


class TestV4RunnerBridge:
    """Test the V4 result conversion in runner.py."""

    def test_convert_v4_results(self):
        from shared.types import AnalysisResult as SharedResult
        from txn_analysis.runner import _convert_v4_results

        v4_results = {
            "s1_portfolio": {
                "title": "S1: Portfolio Health",
                "description": "Monthly trends, activation, balances",
                "sections": [
                    {
                        "heading": "Monthly Trends",
                        "narrative": "...",
                        "figures": ["fig1", "fig2"],
                        "tables": [],
                    },
                    {
                        "heading": "Activation",
                        "narrative": "...",
                        "figures": ["fig3"],
                        "tables": [],
                    },
                ],
                "sheets": [
                    {
                        "name": "Monthly Trends",
                        "df": pd.DataFrame({"month": ["Jan"], "spend": [1000]}),
                    },
                    {
                        "name": "Activation",
                        "df": pd.DataFrame({"status": ["Active"], "count": [50]}),
                    },
                ],
            },
            "s6_risk": {
                "title": "S6: Risk & Balance",
                "description": "Balance tiers, correlation",
                "sections": [],
                "sheets": [],
            },
        }

        results = _convert_v4_results(v4_results)

        assert "s1_portfolio" in results
        assert "s6_risk" in results

        s1 = results["s1_portfolio"]
        assert isinstance(s1, SharedResult)
        assert s1.name == "s1_portfolio"
        assert s1.summary == "S1: Portfolio Health"
        assert "Monthly Trends" in s1.data
        assert "Activation" in s1.data
        assert s1.metadata["section_count"] == 2
        assert s1.metadata["chart_count"] == 3

        s6 = results["s6_risk"]
        assert s6.data == {}
        assert s6.metadata["section_count"] == 0

    def test_convert_v4_results_empty(self):
        from txn_analysis.runner import _convert_v4_results

        assert _convert_v4_results({}) == {}

    def test_run_txn_v4_missing_txn_dir(self):
        from pathlib import Path

        from shared.context import PipelineContext
        from txn_analysis.runner import run_txn_v4

        ctx = PipelineContext(output_dir=Path("/tmp/test"))
        with pytest.raises(FileNotFoundError, match="No 'txn_dir' input"):
            run_txn_v4(ctx)
