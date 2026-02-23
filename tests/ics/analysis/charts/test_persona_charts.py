"""Tests for persona chart builders."""

import pandas as pd
import pytest

from ics_toolkit.analysis.charts.persona import (
    chart_persona_by_branch,
    chart_persona_by_source,
    chart_persona_cohort_trend,
    chart_persona_contribution,
    chart_persona_map,
    chart_persona_revenue,
)
from ics_toolkit.analysis.charts.style import PERSONA_ORDER

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def persona_overview_df():
    return pd.DataFrame(
        {
            "Persona": PERSONA_ORDER,
            "Account Count": [564, 241, 59, 204],
            "% of Total": [52.8, 22.6, 5.5, 19.1],
            "Total M1 Swipes": [7945, 0, 220, 0],
            "Total M3 Swipes": [17419, 4247, 0, 0],
            "Avg M1 Swipes": [14.1, 0.0, 3.7, 0.0],
            "Avg M3 Swipes": [30.9, 17.6, 0.0, 0.0],
            "Total L12M Spend": [250000, 80000, 5000, 0],
            "Avg Balance": [15000, 12000, 8000, 5000],
        }
    )


@pytest.fixture
def persona_contrib_df():
    return pd.DataFrame(
        {
            "Persona": PERSONA_ORDER,
            "% of Accounts": [52.8, 22.6, 5.5, 19.1],
            "% of M1 Swipes": [97.3, 0.0, 2.7, 0.0],
            "% of M3 Swipes": [80.4, 19.6, 0.0, 0.0],
            "% of L12M Swipes": [75.0, 20.0, 3.0, 2.0],
            "% of L12M Spend": [74.6, 23.9, 1.5, 0.0],
        }
    )


@pytest.fixture
def persona_branch_df():
    return pd.DataFrame(
        {
            "Branch": ["Main", "North", "South", "Total"],
            "Fast Activator": [200, 180, 184, 564],
            "Slow Burner": [80, 90, 71, 241],
            "One and Done": [20, 19, 20, 59],
            "Never Activator": [70, 65, 69, 204],
            "Total": [370, 354, 344, 1068],
            "Fast Activator %": [54.1, 50.8, 53.5, 52.8],
        }
    )


@pytest.fixture
def persona_source_df():
    return pd.DataFrame(
        {
            "Source": ["DM", "REF", "Web", "Total"],
            "Fast Activator": [150, 300, 114, 564],
            "Slow Burner": [60, 120, 61, 241],
            "One and Done": [15, 30, 14, 59],
            "Never Activator": [75, 80, 49, 204],
            "Total": [300, 530, 238, 1068],
            "Fast Activator %": [50.0, 56.6, 47.9, 52.8],
        }
    )


@pytest.fixture
def persona_revenue_df():
    return pd.DataFrame(
        {
            "Metric": [
                "Total L12M Interchange",
                "Fast Activator Interchange",
                "Fast Activator % of Interchange",
                "Slow Burner Interchange",
                "Avg Spend per Fast Activator",
                "Avg Spend per Slow Burner",
                "Never Activator Count",
                "Revenue Lift (25% Never -> Slow)",
            ],
            "Value": [6097.0, 4550.0, 74.6, 1456.0, 443.3, 331.9, 204, 308.5],
        }
    )


@pytest.fixture
def persona_cohort_df():
    return pd.DataFrame(
        {
            "Opening Month": ["2025-02", "2025-03", "2025-04"],
            "Fast Activator %": [55.0, 50.0, 53.0],
            "Slow Burner %": [20.0, 25.0, 22.0],
            "One and Done %": [5.0, 6.0, 4.0],
            "Never Activator %": [20.0, 19.0, 21.0],
            "Total": [100, 80, 90],
        }
    )


class TestChartPersonaMap:
    def test_returns_png_bytes(self, persona_overview_df, chart_config):
        result = chart_persona_map(persona_overview_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartPersonaContribution:
    def test_returns_png_bytes(self, persona_contrib_df, chart_config):
        result = chart_persona_contribution(persona_contrib_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartPersonaByBranch:
    def test_returns_png_bytes(self, persona_branch_df, chart_config):
        result = chart_persona_by_branch(persona_branch_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartPersonaBySource:
    def test_returns_png_bytes(self, persona_source_df, chart_config):
        result = chart_persona_by_source(persona_source_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartPersonaRevenue:
    def test_returns_png_bytes(self, persona_revenue_df, chart_config):
        result = chart_persona_revenue(persona_revenue_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartPersonaCohortTrend:
    def test_returns_png_bytes(self, persona_cohort_df, chart_config):
        result = chart_persona_cohort_trend(persona_cohort_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
