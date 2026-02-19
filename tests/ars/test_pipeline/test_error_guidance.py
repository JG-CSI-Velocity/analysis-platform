"""Tests for the error guidance module."""

from ars_analysis.exceptions import ConfigError, DataError, OutputError
from ars_analysis.pipeline.error_guidance import get_error_guidance


def test_file_not_found_guidance():
    title, msg = get_error_guidance(FileNotFoundError("test.xlsx"))
    assert title == "File Not Found"
    assert "M: drive" in msg


def test_permission_error_guidance():
    title, msg = get_error_guidance(PermissionError("locked"))
    assert title == "File Locked"
    assert "Excel" in msg


def test_data_error_guidance():
    title, msg = get_error_guidance(DataError("bad columns"))
    assert title == "Data Problem"


def test_config_error_guidance():
    title, msg = get_error_guidance(ConfigError("missing config"))
    assert title == "Setup Issue"


def test_output_error_guidance():
    title, msg = get_error_guidance(OutputError("template missing"))
    assert title == "Output Error"
    assert "Template" in msg


def test_unknown_error_fallback():
    title, msg = get_error_guidance(RuntimeError("something weird"))
    assert title == "Unexpected Error"
    assert "log file" in msg


def test_isinstance_catches_subclass():
    """ConfigError is a subclass of ARSError, should match ConfigError first."""
    title, _ = get_error_guidance(ConfigError("test"))
    # Should match ConfigError, not fall through to a generic handler
    assert title == "Setup Issue"
