"""Smoke tests -- verify package imports and basic wiring."""

from ars_analysis import __version__
from ars_analysis.exceptions import ARSError, ConfigError, DataError, OutputError


def test_version():
    assert __version__ == "2.0.0"


def test_exception_hierarchy():
    assert issubclass(ConfigError, ARSError)
    assert issubclass(DataError, ARSError)
    assert issubclass(OutputError, ARSError)


def test_exception_detail():
    err = ConfigError("bad config", detail={"file": "ars_config.json"})
    assert str(err) == "bad config"
    assert err.detail == {"file": "ars_config.json"}
    assert "ConfigError" in repr(err)
    assert "ars_config.json" in repr(err)


def test_exception_no_detail():
    err = DataError("missing column")
    assert err.detail == {}
    assert "detail" not in repr(err)


def test_chart_figure_import():
    from ars_analysis.charts.guards import chart_figure

    assert callable(chart_figure)


def test_chart_style_constants():
    from ars_analysis.charts.style import BUSINESS, PERSONAL, TITLE_SIZE

    assert PERSONAL == "#4472C4"
    assert BUSINESS == "#ED7D31"
    assert TITLE_SIZE == 24
