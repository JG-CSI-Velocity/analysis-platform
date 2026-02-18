"""Tests for PipelineContext."""

from datetime import date
from pathlib import Path

from shared.context import PipelineContext


class TestPipelineContext:
    def test_defaults(self):
        ctx = PipelineContext()
        assert ctx.client_name == ""
        assert ctx.analysis_date == date.today()
        assert ctx.results == {}
        assert ctx.all_slides == []

    def test_with_values(self):
        ctx = PipelineContext(
            client_name="Test Bank",
            client_id="12345",
            output_dir=Path("/tmp/output"),
        )
        assert ctx.client_name == "Test Bank"
        assert ctx.output_dir == Path("/tmp/output")

    def test_mutable_results(self):
        ctx = PipelineContext()
        ctx.results["a1"] = "test"
        assert "a1" in ctx.results
