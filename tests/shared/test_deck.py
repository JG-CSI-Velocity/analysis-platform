"""Tests for shared.deck module."""

from shared.context import PipelineContext
from shared.deck import add_slide, report


class TestReport:
    def test_prints_message(self, capsys):
        ctx = PipelineContext()
        report(ctx, "Loading data...")
        assert "Loading data..." in capsys.readouterr().out

    def test_calls_progress_callback(self):
        messages = []
        ctx = PipelineContext(progress_callback=messages.append)
        report(ctx, "Step 1")
        assert messages == ["Step 1"]

    def test_no_callback_no_error(self):
        ctx = PipelineContext(progress_callback=None)
        report(ctx, "No callback")  # should not raise


class TestAddSlide:
    def test_appends_to_slides(self):
        ctx = PipelineContext()
        add_slide(ctx, "slide_1", {"title": "Test"})
        assert len(ctx.all_slides) == 1
        assert ctx.all_slides[0]["id"] == "slide_1"
        assert ctx.all_slides[0]["include"] is True

    def test_default_category(self):
        ctx = PipelineContext()
        add_slide(ctx, "s", {})
        assert ctx.all_slides[0]["category"] == "General"

    def test_custom_category(self):
        ctx = PipelineContext()
        add_slide(ctx, "s", {}, category="Competition")
        assert ctx.all_slides[0]["category"] == "Competition"

    def test_multiple_slides(self):
        ctx = PipelineContext()
        add_slide(ctx, "a", {"v": 1})
        add_slide(ctx, "b", {"v": 2})
        assert len(ctx.all_slides) == 2
        assert ctx.all_slides[0]["id"] == "a"
        assert ctx.all_slides[1]["id"] == "b"
