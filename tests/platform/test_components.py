"""Tests for platform_app.components -- pure logic, no Streamlit dependency."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from platform_app.components.download import MIME_MAP
from shared.types import AnalysisResult

# ---------------------------------------------------------------------------
# download.py
# ---------------------------------------------------------------------------


class TestMimeMap:
    def test_xlsx(self):
        assert ".xlsx" in MIME_MAP
        assert "spreadsheet" in MIME_MAP[".xlsx"]

    def test_pptx(self):
        assert ".pptx" in MIME_MAP
        assert "presentation" in MIME_MAP[".pptx"]

    def test_png(self):
        assert MIME_MAP[".png"] == "image/png"

    def test_csv(self):
        assert MIME_MAP[".csv"] == "text/csv"

    def test_html(self):
        assert MIME_MAP[".html"] == "text/html"

    def test_all_extensions_are_dotted(self):
        for ext in MIME_MAP:
            assert ext.startswith("."), f"Extension {ext!r} should start with '.'"


# ---------------------------------------------------------------------------
# results_display.py -- _find_chart_images helper
# ---------------------------------------------------------------------------


class TestFindChartImages:
    def test_finds_pngs(self, tmp_path):
        from platform_app.components.results_display import _find_chart_images

        (tmp_path / "chart1.png").write_bytes(b"fake")
        (tmp_path / "chart2.png").write_bytes(b"fake")
        (tmp_path / "report.xlsx").write_bytes(b"fake")

        result = _find_chart_images(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".png" for p in result)

    def test_finds_nested_pngs(self, tmp_path):
        from platform_app.components.results_display import _find_chart_images

        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        (charts_dir / "deep.png").write_bytes(b"fake")

        result = _find_chart_images(tmp_path)
        assert len(result) == 1

    def test_empty_dir(self, tmp_path):
        from platform_app.components.results_display import _find_chart_images

        result = _find_chart_images(tmp_path)
        assert result == []

    def test_no_pngs(self, tmp_path):
        from platform_app.components.results_display import _find_chart_images

        (tmp_path / "report.xlsx").write_bytes(b"fake")
        result = _find_chart_images(tmp_path)
        assert result == []

    def test_returns_sorted(self, tmp_path):
        from platform_app.components.results_display import _find_chart_images

        (tmp_path / "b_chart.png").write_bytes(b"fake")
        (tmp_path / "a_chart.png").write_bytes(b"fake")

        result = _find_chart_images(tmp_path)
        assert result[0].name == "a_chart.png"
        assert result[1].name == "b_chart.png"


# ---------------------------------------------------------------------------
# client_selector.py -- _load_registry isolation
# ---------------------------------------------------------------------------


class TestLoadRegistry:
    def test_returns_dict_when_no_registry(self):
        """Without a master config file, returns empty dict."""
        from platform_app.components.client_selector import _load_registry

        # Clear the cached version so test runs fresh
        _load_registry.clear()
        result = _load_registry()
        assert isinstance(result, dict)
        # Clean up cache
        _load_registry.clear()


# ---------------------------------------------------------------------------
# AnalysisResult used across components
# ---------------------------------------------------------------------------


class TestSharedAnalysisResult:
    def test_frozen(self):
        ar = AnalysisResult(name="test", data={"main": pd.DataFrame()})
        with pytest.raises(AttributeError):
            ar.name = "changed"

    def test_default_fields(self):
        ar = AnalysisResult(name="test")
        assert ar.data == {}
        assert ar.charts == []
        assert ar.summary == ""
        assert ar.metadata == {}

    def test_data_dict(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        ar = AnalysisResult(name="test", data={"main": df})
        assert "main" in ar.data
        assert len(ar.data["main"]) == 3


# ---------------------------------------------------------------------------
# styles.py -- pure string functions, no Streamlit dependency
# ---------------------------------------------------------------------------


class TestPageCSS:
    def test_page_css_contains_pipeline_header(self):
        from platform_app.components.styles import PAGE_CSS

        assert ".pipeline-header" in PAGE_CSS

    def test_page_css_contains_sidebar_section(self):
        from platform_app.components.styles import PAGE_CSS

        assert ".sidebar-section" in PAGE_CSS

    def test_page_css_contains_status_chips(self):
        from platform_app.components.styles import PAGE_CSS

        assert ".status-ready" in PAGE_CSS
        assert ".status-error" in PAGE_CSS


# ---------------------------------------------------------------------------
# core/module_registry.py
# ---------------------------------------------------------------------------


class TestModuleRegistry:
    def test_build_registry_returns_list(self):
        from platform_app.core.module_registry import build_registry

        result = build_registry()
        assert isinstance(result, list)
        assert len(result) > 50  # ARS(8) + ICS(44) + TXN(31) + V4(12)

    def test_all_modules_have_required_fields(self):
        from platform_app.core.module_registry import build_registry

        for m in build_registry():
            assert m.key, "module missing key"
            assert m.name, "module missing name"
            assert m.product, "module missing product"
            assert m.category, "module missing category"

    def test_product_enum_values(self):
        from platform_app.core.module_registry import Product

        assert Product.ARS == "ars"
        assert Product.TXN == "txn"
        assert Product.ICS == "ics"

    def test_get_modules_by_product(self):
        from platform_app.core.module_registry import Product, get_modules_by_product

        ars = get_modules_by_product(Product.ARS)
        assert len(ars) == 8
        assert all(m.product == Product.ARS for m in ars)

    def test_get_categories_returns_sorted(self):
        from platform_app.core.module_registry import Product, get_categories

        cats = get_categories(Product.ARS)
        assert cats == sorted(cats)
        assert "Core" in cats

    def test_keys_are_unique(self):
        from platform_app.core.module_registry import build_registry

        keys = [m.key for m in build_registry()]
        assert len(keys) == len(set(keys)), "duplicate module keys found"

    def test_module_info_is_frozen(self):
        from platform_app.core.module_registry import build_registry

        m = build_registry()[0]
        with pytest.raises(AttributeError):
            m.key = "changed"


# ---------------------------------------------------------------------------
# core/run_logger.py
# ---------------------------------------------------------------------------


class TestRunLogger:
    def test_generate_run_id_format(self):
        from platform_app.core.run_logger import generate_run_id

        run_id = generate_run_id()
        assert len(run_id) == 15  # YYYYMMDD_HHMMSS
        assert "_" in run_id

    def test_hash_file(self, tmp_path):
        from platform_app.core.run_logger import hash_file

        f = tmp_path / "test.txt"
        f.write_text("hello")
        h = hash_file(f)
        assert len(h) == 16
        assert isinstance(h, str)

    def test_hash_file_missing(self, tmp_path):
        from platform_app.core.run_logger import hash_file

        assert hash_file(tmp_path / "nope.txt") == ""

    def test_log_and_load_roundtrip(self, tmp_path):
        from platform_app.core.run_logger import RunRecord, load_history, log_run

        record = RunRecord(
            run_id="20260207_120000",
            timestamp="2026-02-07 12:00:00",
            csm="jg",
            client_id="1234",
            client_name="Test CU",
            pipeline="ars",
            modules_run=["ars_attrition"],
            runtime_seconds=5.2,
            status="success",
            output_dir=str(tmp_path),
            result_count=3,
        )
        log_run(record, log_dir=tmp_path)

        history = load_history(log_dir=tmp_path)
        assert len(history) == 1
        assert history[0].run_id == "20260207_120000"
        assert history[0].client_id == "1234"

    def test_load_empty_history(self, tmp_path):
        from platform_app.core.run_logger import load_history

        assert load_history(log_dir=tmp_path) == []


# ---------------------------------------------------------------------------
# core/templates.py
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_builtin_templates_exist(self):
        from platform_app.core.templates import BUILTIN_TEMPLATES

        assert "ARS Full Suite" in BUILTIN_TEMPLATES
        assert "ICS Full Suite" in BUILTIN_TEMPLATES
        assert len(BUILTIN_TEMPLATES) == 6

    def test_load_includes_builtins(self, tmp_path):
        from platform_app.core.templates import load_templates

        templates = load_templates(path=tmp_path / "nonexistent.yaml")
        assert "ARS Full Suite" in templates

    def test_save_and_load_roundtrip(self, tmp_path):
        from platform_app.core.templates import load_templates, save_template

        yaml_path = tmp_path / "templates.yaml"
        save_template("My Custom", ["ars_attrition", "ars_value"], path=yaml_path)

        templates = load_templates(path=yaml_path)
        assert "My Custom" in templates
        assert templates["My Custom"] == ["ars_attrition", "ars_value"]

    def test_delete_builtin_fails(self):
        from platform_app.core.templates import delete_template

        assert delete_template("ARS Full Suite") is False

    def test_delete_user_template(self, tmp_path):
        from platform_app.core.templates import delete_template, save_template

        yaml_path = tmp_path / "templates.yaml"
        save_template("Temp", ["ars_attrition"], path=yaml_path)
        assert delete_template("Temp", path=yaml_path) is True


# ---------------------------------------------------------------------------
# core/session_manager.py
# ---------------------------------------------------------------------------


class TestSessionManager:
    def test_client_workspace_properties(self):
        from platform_app.core.session_manager import ClientWorkspace

        ws = ClientWorkspace(
            csm="jg",
            client_id="1234",
            client_name="Test CU",
            root=Path("/data/jg/1234"),
            oddd_file=Path("/data/jg/1234/odd.xlsx"),
        )
        assert ws.has_ars_data is True
        assert ws.has_txn_data is False
        assert ws.has_ics_data is False
        assert "ars" in ws.available_pipelines

    def test_auto_detect_files(self, tmp_path):
        from platform_app.core.session_manager import auto_detect_files

        (tmp_path / "1234-ODD.xlsx").write_bytes(b"fake")
        (tmp_path / "transactions.csv").write_bytes(b"fake")

        detected = auto_detect_files(tmp_path)
        assert detected["oddd"] is not None
        assert detected["tran"] is not None

    def test_discover_csm_folders(self, tmp_path):
        from platform_app.core.session_manager import discover_csm_folders

        (tmp_path / "alice").mkdir()
        (tmp_path / "bob").mkdir()
        (tmp_path / ".hidden").mkdir()

        result = discover_csm_folders(tmp_path)
        assert result == ["alice", "bob"]

    def test_discover_clients(self, tmp_path):
        from platform_app.core.session_manager import discover_clients

        (tmp_path / "1234").mkdir()
        (tmp_path / "5678").mkdir()

        result = discover_clients(tmp_path)
        assert result == ["1234", "5678"]
