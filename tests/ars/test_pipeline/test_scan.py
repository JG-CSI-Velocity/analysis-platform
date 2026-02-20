"""Tests for ars.pipeline.steps.scan -- ODD file scanning."""

from unittest.mock import MagicMock

import pytest

from ars_analysis.pipeline.steps.scan import (
    ScannedFile,
    available_csms,
    available_months,
    scan_ready_files,
)


@pytest.fixture
def mock_settings(tmp_path):
    """Create a mock ARSSettings with temp watch_root."""
    settings = MagicMock()
    settings.paths.watch_root = tmp_path / "ready"
    return settings


@pytest.fixture
def populated_watch_root(tmp_path):
    """Create a watch_root dir with CSM/month/client structure."""
    root = tmp_path / "ready"
    client_dir = root / "JamesG" / "2026.02" / "1453"
    client_dir.mkdir(parents=True)

    # Create a formatted file
    formatted = client_dir / "1453-2026-02-Connex CU-ODD-formatted.xlsx"
    formatted.write_bytes(b"formatted data " * 100)

    # Create a raw file too
    raw = client_dir / "1453-2026-02-Connex CU-ODD.xlsx"
    raw.write_bytes(b"raw data " * 100)

    # Another client with only raw
    client2 = root / "JamesG" / "2026.02" / "1776"
    client2.mkdir(parents=True)
    raw2 = client2 / "1776-2026-02-Bank-ODD.xlsx"
    raw2.write_bytes(b"raw data " * 50)

    return root


class TestScanReadyFiles:
    def test_empty_dir(self, mock_settings):
        result = scan_ready_files(mock_settings, target_month="2026.02")
        assert result == []

    def test_nonexistent_dir(self, mock_settings):
        result = scan_ready_files(mock_settings, target_month="2026.02")
        assert result == []

    def test_finds_formatted_file(self, mock_settings, populated_watch_root):
        mock_settings.paths.watch_root = populated_watch_root
        result = scan_ready_files(mock_settings, target_month="2026.02")
        assert len(result) == 2

        # 1453 should pick formatted over raw
        f1453 = next(f for f in result if f.client_id == "1453")
        assert f1453.is_formatted is True
        assert "formatted" in f1453.filename

    def test_client_filter(self, mock_settings, populated_watch_root):
        mock_settings.paths.watch_root = populated_watch_root
        result = scan_ready_files(
            mock_settings,
            target_month="2026.02",
            client_filter="1453",
        )
        assert len(result) == 1
        assert result[0].client_id == "1453"

    def test_csm_filter(self, mock_settings, populated_watch_root):
        mock_settings.paths.watch_root = populated_watch_root
        result = scan_ready_files(
            mock_settings,
            target_month="2026.02",
            csm_filter="JamesG",
        )
        assert len(result) == 2

    def test_wrong_month_empty(self, mock_settings, populated_watch_root):
        mock_settings.paths.watch_root = populated_watch_root
        result = scan_ready_files(mock_settings, target_month="2025.12")
        assert result == []


class TestAvailableMonths:
    def test_empty(self, mock_settings):
        result = available_months(mock_settings)
        assert result == []

    def test_finds_months(self, mock_settings, populated_watch_root):
        mock_settings.paths.watch_root = populated_watch_root
        result = available_months(mock_settings)
        assert "2026.02" in result


class TestAvailableCSMs:
    def test_empty(self, mock_settings):
        result = available_csms(mock_settings)
        assert result == []

    def test_finds_csms(self, mock_settings, populated_watch_root):
        mock_settings.paths.watch_root = populated_watch_root
        result = available_csms(mock_settings)
        assert "JamesG" in result


class TestScannedFile:
    def test_frozen(self):
        from datetime import datetime
        from pathlib import Path

        sf = ScannedFile(
            client_id="1453",
            csm_name="JamesG",
            filename="test.xlsx",
            file_path=Path("/tmp/test.xlsx"),
            month="2026.02",
            file_size_mb=1.5,
            is_formatted=True,
            modified_time=datetime.now(),
        )
        with pytest.raises(AttributeError):
            sf.client_id = "9999"
