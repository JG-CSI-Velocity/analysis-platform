"""Tests for the batch processing module."""

from datetime import datetime

import pandas as pd

from ars_analysis.pipeline.batch import BatchResult, _build_steps, run_batch
from ars_analysis.pipeline.steps.scan import ScannedFile


def _make_scanned(tmp_path, client_id="1234"):
    """Create a ScannedFile with a real formatted xlsx."""
    file_path = tmp_path / f"{client_id}_formatted.xlsx"
    df = pd.DataFrame({
        "Account Number": [f"A{i}" for i in range(20)],
        "Date Opened": pd.date_range("2020-01-01", periods=20, freq="M"),
        "Status Code": ["A"] * 15 + ["C"] * 5,
        "Current Balance": [1000 + i * 100 for i in range(20)],
    })
    df.to_excel(file_path, index=False)

    return ScannedFile(
        client_id=client_id,
        csm_name="TestCSM",
        filename=file_path.name,
        file_path=file_path,
        month="2026.01",
        file_size_mb=0.1,
        is_formatted=True,
        modified_time=datetime.now(),
    )


class _MockSettings:
    """Minimal mock for ARSSettings used by batch tests."""
    clients = {}


class TestBatchResult:
    """BatchResult dataclass basic tests."""

    def test_fields(self):
        r = BatchResult(
            client_id="1234", client_name="Test",
            success=True, elapsed=5.0, slide_count=10,
        )
        assert r.success
        assert r.slide_count == 10
        assert r.error == ""


class TestBuildSteps:
    """_build_steps creates a valid pipeline step list."""

    def test_default_steps(self, tmp_path):
        steps = _build_steps(tmp_path / "test.xlsx")
        assert len(steps) == 5
        names = [s.name for s in steps]
        assert "load_data" in names
        assert "create_subsets" in names
        assert "run_analyses" in names
        assert "generate_output" in names
        assert "archive" in names

    def test_with_module_ids(self, tmp_path):
        steps = _build_steps(tmp_path / "test.xlsx", module_ids=["overview.stat_codes"])
        assert len(steps) == 5


class TestRunBatch:
    """run_batch() processes multiple clients."""

    def test_empty_files(self):
        results = run_batch([], settings=_MockSettings())
        assert results == []

    def test_processes_files(self, tmp_path):
        scanned = _make_scanned(tmp_path, "1234")
        results = run_batch([scanned], settings=_MockSettings())
        assert len(results) == 1
        assert results[0].client_id == "1234"

    def test_multiple_clients(self, tmp_path):
        files = [
            _make_scanned(tmp_path, "1001"),
            _make_scanned(tmp_path, "1002"),
        ]
        results = run_batch(files, settings=_MockSettings())
        assert len(results) == 2
        ids = {r.client_id for r in results}
        assert "1001" in ids
        assert "1002" in ids

    def test_with_workers_param(self, tmp_path):
        """max_workers parameter is accepted and defaults to sequential."""
        files = [_make_scanned(tmp_path, "2001")]
        results = run_batch(files, settings=_MockSettings(), max_workers=1)
        assert len(results) == 1

    def test_parallel_workers(self, tmp_path):
        """Parallel mode processes all clients and returns results."""
        files = [
            _make_scanned(tmp_path, "3001"),
            _make_scanned(tmp_path, "3002"),
        ]
        results = run_batch(files, settings=_MockSettings(), max_workers=2)
        assert len(results) == 2
        ids = {r.client_id for r in results}
        assert "3001" in ids
        assert "3002" in ids

    def test_local_temp_flag(self, tmp_path):
        """use_local_temp copies to temp and produces results."""
        files = [_make_scanned(tmp_path, "4001")]
        results = run_batch(files, settings=_MockSettings(), use_local_temp=True)
        assert len(results) == 1
        assert results[0].client_id == "4001"

    def test_parallel_with_local_temp(self, tmp_path):
        """Combined parallel + local temp produces results for all clients."""
        files = [
            _make_scanned(tmp_path, "5001"),
            _make_scanned(tmp_path, "5002"),
        ]
        results = run_batch(
            files, settings=_MockSettings(),
            max_workers=2, use_local_temp=True,
        )
        assert len(results) == 2
        ids = {r.client_id for r in results}
        assert "5001" in ids
        assert "5002" in ids
