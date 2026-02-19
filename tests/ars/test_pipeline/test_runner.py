"""Tests for the pipeline runner."""

import pytest

from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
from ars_analysis.pipeline.runner import PipelineStep, run_pipeline


@pytest.fixture
def ctx():
    """Minimal PipelineContext for runner tests."""
    return PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(),
    )


def _noop_step(ctx):
    pass


def _failing_step(ctx):
    raise ValueError("intentional failure")


def test_run_pipeline_all_succeed(ctx):
    steps = [
        PipelineStep("step_a", _noop_step),
        PipelineStep("step_b", _noop_step),
    ]
    results = run_pipeline(ctx, steps)
    assert len(results) == 2
    assert all(r.success for r in results)


def test_run_pipeline_critical_failure_stops_execution(ctx):
    steps = [
        PipelineStep("step_a", _noop_step),
        PipelineStep("step_fail", _failing_step, critical=True),
        PipelineStep("step_c", _noop_step),
    ]
    results = run_pipeline(ctx, steps)
    # step_c should not have run
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False
    assert "intentional failure" in results[1].error


def test_run_pipeline_non_critical_failure_continues(ctx):
    steps = [
        PipelineStep("step_a", _noop_step),
        PipelineStep("step_warn", _failing_step, critical=False),
        PipelineStep("step_c", _noop_step),
    ]
    results = run_pipeline(ctx, steps)
    assert len(results) == 3
    assert results[0].success is True
    assert results[1].success is False
    assert results[2].success is True


def test_run_pipeline_empty_steps(ctx):
    results = run_pipeline(ctx, [])
    assert results == []


def test_step_result_has_elapsed_time(ctx):
    steps = [PipelineStep("step_a", _noop_step)]
    results = run_pipeline(ctx, steps)
    assert results[0].elapsed_seconds >= 0


def test_pipeline_step_is_frozen():
    step = PipelineStep("test", _noop_step)
    with pytest.raises(AttributeError):
        step.name = "changed"


def test_pipeline_step_default_critical():
    step = PipelineStep("test", _noop_step)
    assert step.critical is True
