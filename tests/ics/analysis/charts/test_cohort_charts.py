"""Tests for cohort chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.cohort import (
    chart_activation_summary,
    chart_cohort_milestones,
    chart_growth_patterns,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartCohortMilestones:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02", "2025-03"],
                "Cohort Size": [20, 15],
                "Avg Bal": [5000.0, 6000.0],
                "M1 Active": [10, 8],
                "M1 Activation %": [50.0, 53.3],
                "M1 Avg Swipes": [3.5, 4.2],
                "M1 Avg Spend": [50.0, 60.0],
                "M3 Active": [8, 6],
                "M3 Activation %": [40.0, 40.0],
                "M3 Avg Swipes": [5.0, 5.5],
                "M3 Avg Spend": [80.0, 90.0],
                "M6 Avg Swipes": [None, None],
                "M12 Avg Swipes": [None, None],
            }
        )
        result = chart_cohort_milestones(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartActivationSummary:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": [
                    "M1 Activation Rate",
                    "M3 Activation Rate",
                    "M6 Activation Rate",
                    "M12 Activation Rate",
                ],
                "Value": [62.1, 55.0, 48.3, 40.0],
            }
        )
        result = chart_activation_summary(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER

    def test_handles_na_values(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": [
                    "M1 Activation Rate",
                    "M3 Activation Rate",
                    "M6 Activation Rate",
                    "M12 Activation Rate",
                ],
                "Value": [62.1, 55.0, None, None],
            }
        )
        result = chart_activation_summary(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartGrowthPatterns:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02", "2025-03"],
                "Cohort Size": [20, 15],
                "M1 Swipes": [100, 80],
                "M3 Swipes": [150, 120],
                "M6 Swipes": [None, None],
                "M12 Swipes": [None, None],
            }
        )
        result = chart_growth_patterns(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
