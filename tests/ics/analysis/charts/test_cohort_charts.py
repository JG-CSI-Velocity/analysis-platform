"""Tests for cohort chart builders (ax29, ax31, ax32)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.cohort import (
    chart_activation_summary,
    chart_cohort_milestones,
    chart_growth_patterns,
)


class TestChartCohortMilestones:
    """ax29: Grouped bar of avg swipes at milestones by cohort."""

    def test_returns_figure(self, chart_config):
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
                "M6 Avg Swipes": ["N/A", "N/A"],
                "M12 Avg Swipes": ["N/A", "N/A"],
            }
        )
        fig = chart_cohort_milestones(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_traces_for_available_milestones(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02"],
                "Cohort Size": [20],
                "M1 Avg Swipes": [3.5],
                "M3 Avg Swipes": [5.0],
            }
        )
        fig = chart_cohort_milestones(df, chart_config)
        assert len(fig.data) == 2

    def test_grouped_layout(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02"],
                "M1 Avg Swipes": [3.5],
            }
        )
        fig = chart_cohort_milestones(df, chart_config)
        assert fig.layout.barmode == "group"


class TestChartActivationSummary:
    """ax31: Bar chart of aggregate activation rates."""

    def test_returns_figure(self, chart_config):
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
        fig = chart_activation_summary(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_four_bars(self, chart_config):
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
        fig = chart_activation_summary(df, chart_config)
        assert len(fig.data[0].x) == 4

    def test_skips_na_values(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": [
                    "M1 Activation Rate",
                    "M3 Activation Rate",
                    "M6 Activation Rate",
                    "M12 Activation Rate",
                ],
                "Value": [62.1, 55.0, "N/A", "N/A"],
            }
        )
        fig = chart_activation_summary(df, chart_config)
        assert len(fig.data[0].x) == 2


class TestChartGrowthPatterns:
    """ax32: Line chart of swipe trajectories across milestones."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02", "2025-03"],
                "Cohort Size": [20, 15],
                "M1 Swipes": [100, 80],
                "M3 Swipes": [150, 120],
                "M6 Swipes": ["N/A", "N/A"],
                "M12 Swipes": ["N/A", "N/A"],
            }
        )
        fig = chart_growth_patterns(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_one_line_per_cohort(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02", "2025-03"],
                "Cohort Size": [20, 15],
                "M1 Swipes": [100, 80],
                "M3 Swipes": [150, 120],
                "M6 Swipes": [200, "N/A"],
                "M12 Swipes": ["N/A", "N/A"],
            }
        )
        fig = chart_growth_patterns(df, chart_config)
        assert len(fig.data) == 2

    def test_lines_mode(self, chart_config):
        df = pd.DataFrame(
            {
                "Opening Month": ["2025-02"],
                "Cohort Size": [20],
                "M1 Swipes": [100],
                "M3 Swipes": [150],
                "M6 Swipes": ["N/A"],
                "M12 Swipes": ["N/A"],
            }
        )
        fig = chart_growth_patterns(df, chart_config)
        assert fig.data[0].mode == "lines+markers"
