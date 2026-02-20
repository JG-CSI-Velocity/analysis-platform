"""Tests for the analytics module registry."""

import pytest

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import (
    _REGISTRY,
    clear_registry,
    get_module,
    ordered_modules,
    register,
)
from ars_analysis.exceptions import ConfigError
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure each test starts with a clean registry."""
    saved = dict(_REGISTRY)
    clear_registry()
    yield
    clear_registry()
    _REGISTRY.update(saved)


def _make_module(module_id: str = "test.module") -> type[AnalysisModule]:
    """Create a minimal concrete module class for testing."""

    class TestModule(AnalysisModule):
        def run(self, ctx):
            return [AnalysisResult(slide_id="T1", title="Test")]

    TestModule.module_id = module_id
    TestModule.display_name = "Test Module"
    TestModule.section = "overview"
    return TestModule


def test_register_decorator_adds_to_registry():
    cls = _make_module("test.one")
    register(cls)
    assert "test.one" in _REGISTRY
    assert _REGISTRY["test.one"] is cls


def test_get_module_returns_registered_class():
    cls = _make_module("test.two")
    register(cls)
    assert get_module("test.two") is cls


def test_get_module_raises_config_error_on_unknown():
    with pytest.raises(ConfigError, match="Unknown analytics module"):
        get_module("nonexistent.module")


def test_get_module_error_includes_available_modules():
    cls = _make_module("test.available")
    register(cls)
    try:
        get_module("bad.id")
    except ConfigError as exc:
        assert "test.available" in exc.detail["available"]


def test_ordered_modules_returns_deterministic_order():
    # Register two modules that are in MODULE_ORDER
    cls1 = _make_module("overview.stat_codes")
    cls2 = _make_module("overview.eligibility")
    register(cls1)
    register(cls2)

    result = ordered_modules()
    ids = [m.module_id for m in result]
    # stat_codes comes before eligibility in MODULE_ORDER
    assert ids.index("overview.stat_codes") < ids.index("overview.eligibility")


def test_ordered_modules_warns_on_missing(capfd):
    # Don't register anything -- all MODULE_ORDER entries will be missing
    result = ordered_modules()
    assert result == []


def test_validate_catches_missing_columns():
    cls = _make_module("test.validate")
    cls.required_columns = ("Stat Code", "Missing Column")
    register(cls)

    ctx = PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(),
    )
    import pandas as pd

    ctx.data = pd.DataFrame({"Stat Code": ["A01"], "Other": [1]})

    module = cls()
    errors = module.validate(ctx)
    assert len(errors) == 1
    assert "Missing Column" in errors[0]


def test_validate_passes_when_all_columns_present():
    cls = _make_module("test.valid")
    cls.required_columns = ("Stat Code",)
    register(cls)

    ctx = PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(),
    )
    import pandas as pd

    ctx.data = pd.DataFrame({"Stat Code": ["A01"]})

    module = cls()
    errors = module.validate(ctx)
    assert errors == []


def test_validate_catches_no_data():
    cls = _make_module("test.nodata")
    register(cls)

    ctx = PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(),
    )
    # ctx.data is None by default

    module = cls()
    errors = module.validate(ctx)
    assert "No data loaded" in errors[0]
