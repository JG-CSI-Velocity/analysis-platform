"""Tests for ars_analysis.helpers."""

from unittest.mock import MagicMock

import pytest

from ars_analysis.helpers import (
    FIGURE_SIZES,
    _fig,
    _report,
    _save,
    _save_chart,
    _slide,
    safe_run,
)


@pytest.fixture
def ctx():
    """Minimal ctx dict for testing."""
    return {
        "all_slides": [],
        "_progress_callback": None,
        "_make_figure": None,
        "_save_to_excel": None,
    }


class TestReport:
    def test_prints_message(self, ctx, capsys):
        _report(ctx, "hello")
        assert "hello" in capsys.readouterr().out

    def test_calls_callback(self, ctx):
        cb = MagicMock()
        ctx["_progress_callback"] = cb
        _report(ctx, "test")
        cb.assert_called_once_with("test")

    def test_no_callback(self, ctx):
        _report(ctx, "no crash")


class TestFig:
    def test_default_size(self, ctx):
        fig, ax = _fig(ctx)
        w, h = fig.get_size_inches()
        assert (w, h) == FIGURE_SIZES["single"]
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_half_size(self, ctx):
        fig, ax = _fig(ctx, "half")
        w, h = fig.get_size_inches()
        assert (w, h) == FIGURE_SIZES["half"]
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_uses_make_figure(self, ctx):
        mock_fig = MagicMock()
        ctx["_make_figure"] = MagicMock(return_value=(mock_fig, None))
        fig, ax = _fig(ctx, "single")
        assert fig is mock_fig


class TestSaveChart:
    def test_saves_and_returns_path(self, ctx, tmp_path):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = tmp_path / "test.png"
        result = _save_chart(fig, path)
        assert result == str(path)
        assert path.exists()


class TestSlide:
    def test_appends_slide(self, ctx):
        _slide(ctx, "A1", {"title": "Test"}, category="Overview")
        assert len(ctx["all_slides"]) == 1
        assert ctx["all_slides"][0]["id"] == "A1"
        assert ctx["all_slides"][0]["category"] == "Overview"
        assert ctx["all_slides"][0]["include"] is True

    def test_default_category(self, ctx):
        _slide(ctx, "A1", {"title": "Test"})
        assert ctx["all_slides"][0]["category"] == "General"


class TestSave:
    def test_calls_save_fn(self, ctx):
        mock_fn = MagicMock()
        ctx["_save_to_excel"] = mock_fn
        import pandas as pd

        df = pd.DataFrame({"a": [1]})
        _save(ctx, df, "Sheet1", "Title")
        mock_fn.assert_called_once()

    def test_no_save_fn(self, ctx):
        import pandas as pd

        df = pd.DataFrame({"a": [1]})
        _save(ctx, df, "Sheet1", "Title")  # Should not crash

    def test_handles_error(self, ctx, capsys):
        ctx["_save_to_excel"] = MagicMock(side_effect=ValueError("test error"))
        import pandas as pd

        df = pd.DataFrame({"a": [1]})
        _save(ctx, df, "Sheet1", "Title")
        assert "test error" in capsys.readouterr().out


class TestSafeRun:
    def test_success(self, ctx):
        def fn(c):
            c["ran"] = True
            return c

        result = safe_run(fn, ctx, "test")
        assert result["ran"] is True

    def test_failure_returns_ctx(self, ctx):
        def fn(c):
            raise RuntimeError("boom")

        result = safe_run(fn, ctx, "test")
        assert result is ctx
