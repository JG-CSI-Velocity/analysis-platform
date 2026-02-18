"""Shared fixtures for chart tests."""

import pandas as pd
import pytest

from ics_toolkit.settings import ChartConfig


@pytest.fixture
def chart_config() -> ChartConfig:
    """Default chart config for testing."""
    return ChartConfig()


@pytest.fixture
def crosstab_df() -> pd.DataFrame:
    """Sample crosstab DataFrame (Source x categories + Total)."""
    return pd.DataFrame(
        {
            "Source": ["DM", "REF", "Web", "Total"],
            "O": [10, 20, 5, 35],
            "C": [3, 7, 2, 12],
            "Total": [13, 27, 7, 47],
        }
    )


@pytest.fixture
def kpi_df() -> pd.DataFrame:
    """Sample KPI summary DataFrame (Metric/Value)."""
    return pd.DataFrame(
        {
            "Metric": [
                "Total ICS Accounts",
                "Open (Stat Code O)",
                "Closed (Stat Code C)",
                "% Open",
                "% Closed",
            ],
            "Value": [100, 80, 20, 80.0, 20.0],
        }
    )
