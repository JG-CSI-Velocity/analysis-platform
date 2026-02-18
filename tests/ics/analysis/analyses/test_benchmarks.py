"""Tests for analyses/benchmarks.py."""

from ics_toolkit.analysis.analyses.benchmarks import (
    INTERCHANGE_RATE,
    THRESHOLDS,
    traffic_light,
)


class TestBenchmarkConstants:
    def test_interchange_rate_range(self):
        assert 0 < INTERCHANGE_RATE < 0.05

    def test_thresholds_have_expected_keys(self):
        assert "activation_rate" in THRESHOLDS
        assert "active_rate" in THRESHOLDS


class TestTrafficLight:
    def test_green(self):
        assert traffic_light(65.0, "activation_rate") == "green"

    def test_yellow(self):
        assert traffic_light(45.0, "activation_rate") == "yellow"

    def test_red(self):
        assert traffic_light(20.0, "activation_rate") == "red"

    def test_unknown_metric(self):
        assert traffic_light(50.0, "unknown") == "gray"

    def test_boundary_green(self):
        assert traffic_light(60.0, "activation_rate") == "green"

    def test_boundary_yellow(self):
        assert traffic_light(40.0, "activation_rate") == "yellow"
