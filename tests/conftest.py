"""Root conftest -- auto-skip kaleido-dependent tests on Windows."""

import sys

import pytest

# Modules whose tests run full pipelines with chart export (kaleido hangs on Windows)
_KALEIDO_FILES = {
    "test_cli.py",
    "test_pipeline.py",
}

# Individual test names that trigger kaleido
_KALEIDO_TESTS = {
    "test_plotly_figure",
    "test_creates_parent_dirs",
    "test_save_chart_png",
    "test_generates_excel",
}


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests that hang on Windows due to kaleido."""
    if sys.platform != "win32":
        return

    skip = pytest.mark.skip(reason="kaleido hangs on Windows -- validate with real PPTX output")

    for item in items:
        filename = item.path.name if hasattr(item.path, "name") else ""
        # Skip entire CLI/pipeline test files (they run full pipelines with chart export)
        if filename in _KALEIDO_FILES:
            item.add_marker(skip)
            continue
        # Skip integration tests
        if "integration" in str(item.path):
            item.add_marker(skip)
            continue
        # Skip individual chart-rendering tests
        if item.name in _KALEIDO_TESTS:
            item.add_marker(skip)
