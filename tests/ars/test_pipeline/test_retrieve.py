"""Tests for ars.pipeline.steps.retrieve -- ODD file retrieval."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ars_analysis.pipeline.steps.retrieve import (
    RetrieveResult,
    _path_accessible,
    _place_odd,
    retrieve_all,
)


@pytest.fixture
def mock_settings(tmp_path):
    """Create a mock ARSSettings with temp directories."""
    settings = MagicMock()
    settings.paths.retrieve_dir = tmp_path / "retrieve"
    settings.csm_sources.sources = {}
    return settings


@pytest.fixture
def csm_source(tmp_path):
    """Create a CSM source directory with a sample ODD file."""
    source_dir = tmp_path / "csm_source"
    source_dir.mkdir()
    odd_file = source_dir / "1453-2026-02-Connex CU-ODD.xlsx"
    odd_file.write_bytes(b"fake xlsx data")
    return source_dir


class TestRetrieveResult:
    def test_empty_result(self):
        r = RetrieveResult()
        assert r.total == 0
        assert r.copied == []

    def test_total(self):
        r = RetrieveResult(
            copied=[("A", "f1")],
            skipped=[("B", "f2")],
            errors=[("C", "f3", "err")],
        )
        assert r.total == 3


class TestPlaceOdd:
    def test_copies_file(self, tmp_path):
        source = tmp_path / "source.xlsx"
        source.write_bytes(b"data")
        parsed = {
            "client_id": "1453",
            "year": "2026",
            "month": "02",
            "filename": "1453-2026-02-Test-ODD.xlsx",
        }
        result = RetrieveResult()
        dest = tmp_path / "dest"

        _place_odd(source, parsed, "JamesG", dest, result)

        target = dest / "JamesG" / "2026.02" / "1453" / "1453-2026-02-Test-ODD.xlsx"
        assert target.exists()
        assert len(result.copied) == 1

    def test_skips_existing(self, tmp_path):
        parsed = {
            "client_id": "1453",
            "year": "2026",
            "month": "02",
            "filename": "test.xlsx",
        }
        dest = tmp_path / "dest"
        target = dest / "JamesG" / "2026.02" / "1453" / "test.xlsx"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing")

        result = RetrieveResult()
        _place_odd(tmp_path / "src.xlsx", parsed, "JamesG", dest, result)

        assert len(result.skipped) == 1
        assert len(result.copied) == 0

    def test_handles_bytes(self, tmp_path):
        parsed = {
            "client_id": "1776",
            "year": "2026",
            "month": "01",
            "filename": "1776-2026-01-Bank-ODD.xlsx",
        }
        dest = tmp_path / "dest"
        result = RetrieveResult()

        _place_odd(b"zip-extracted-bytes", parsed, "CSM1", dest, result)

        target = dest / "CSM1" / "2026.01" / "1776" / "1776-2026-01-Bank-ODD.xlsx"
        assert target.exists()
        assert target.read_bytes() == b"zip-extracted-bytes"


class TestPathAccessible:
    def test_existing_path(self, tmp_path):
        assert _path_accessible(tmp_path) is True

    def test_nonexistent_path(self, tmp_path):
        assert _path_accessible(tmp_path / "nope") is False

    def test_timeout_returns_none(self):
        """A path that blocks forever should return None after timeout."""
        import time

        class HangingPath:
            def exists(self):
                time.sleep(10)
                return True

        result = _path_accessible(HangingPath(), timeout=0.1)
        assert result is None


class TestRetrieveAll:
    def test_empty_sources(self, mock_settings):
        result = retrieve_all(mock_settings, target_month="2026.02")
        assert result.total == 0

    def test_with_source(self, mock_settings, csm_source):
        mock_settings.csm_sources.sources = {"TestCSM": csm_source}
        result = retrieve_all(mock_settings, target_month="2026.02")
        assert len(result.copied) == 1
        assert result.copied[0][0] == "TestCSM"

    def test_nonexistent_source(self, mock_settings):
        mock_settings.csm_sources.sources = {"Bad": Path("/nonexistent/path")}
        result = retrieve_all(mock_settings, target_month="2026.02")
        assert result.total == 0
