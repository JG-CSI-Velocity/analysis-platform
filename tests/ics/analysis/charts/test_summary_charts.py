"""Tests for summary chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.summary import chart_penetration_by_branch

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartPenetrationByBranch:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Total Accounts": [100, 80, 180],
                "ICS Accounts": [30, 20, 50],
                "Penetration %": [30.0, 25.0, 27.8],
            }
        )
        result = chart_penetration_by_branch(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
