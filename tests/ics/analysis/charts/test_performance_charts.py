"""Tests for performance chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.performance import (
    chart_product_code_performance,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartProductCodePerformance:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Prod Code": ["100", "200", "Total"],
                "Accounts": [20, 15, 35],
                "Activation %": [75.0, 60.0, 68.6],
                "Avg Swipes": [12.0, 8.0, 10.3],
                "Avg Spend": [150.0, 100.0, 128.6],
                "Avg Balance": [5000.0, 3000.0, 4143.0],
            }
        )
        result = chart_product_code_performance(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
