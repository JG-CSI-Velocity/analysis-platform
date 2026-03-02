"""Extended chart tests for M9, M15, M16 analysis chart functions."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from txn_analysis.settings import ChartConfig, Settings


@pytest.fixture()
def chart_config() -> ChartConfig:
    return ChartConfig()


@pytest.fixture()
def settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test", ic_rate=0.015)


# ---------------------------------------------------------------------------
# M15: Recurring Payment Charts
# ---------------------------------------------------------------------------


class TestRecurringCharts:
    def _recurring_result(self) -> pd.DataFrame:
        """Synthetic recurring payments data."""
        return pd.DataFrame(
            {
                "Merchant": [f"Merchant_{i}" for i in range(10)],
                "Recurring Accounts": np.random.default_rng(42).integers(5, 100, 10),
                "Total Recurring Spend": np.random.default_rng(42).uniform(1000, 50000, 10).round(2),
                "Avg Monthly Spend": np.random.default_rng(42).uniform(10, 500, 10).round(2),
            }
        )

    def _onset_result(self) -> pd.DataFrame:
        """Synthetic onset month data."""
        return pd.DataFrame(
            {
                "Month": ["2025-07", "2025-08", "2025-09", "2025-10"],
                "New Recurring": [12, 15, 8, 20],
                "Cumulative": [12, 27, 35, 55],
            }
        )

    def test_recurring_merchants_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.recurring import chart_recurring_merchants

        df = self._recurring_result()
        result = AnalysisResult(
            name="recurring_payments",
            title="Recurring Payments",
            data={"main": df},
        )
        fig = chart_recurring_merchants(result, chart_config)
        assert fig is not None
        plt.close(fig)

    def test_recurring_onsets_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.recurring import chart_recurring_onsets

        df = self._onset_result()
        result = AnalysisResult(
            name="recurring_payments",
            title="Recurring Payments",
            data={"main": self._recurring_result(), "onset_months": df},
        )
        fig = chart_recurring_onsets(result, chart_config)
        assert fig is not None
        plt.close(fig)

    def test_recurring_empty_graceful(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.recurring import chart_recurring_merchants

        result = AnalysisResult(
            name="recurring_payments",
            title="Recurring Payments",
            data={"main": pd.DataFrame()},
        )
        fig = chart_recurring_merchants(result, chart_config)
        assert fig is not None
        plt.close(fig)


# ---------------------------------------------------------------------------
# M16: Time Pattern Charts (no dedicated chart module -- verify data)
# ---------------------------------------------------------------------------


class TestTimePatternsData:
    def test_time_patterns_heatmap_data(self):
        """Verify M16 enriched heatmap data is chart-ready."""
        from txn_analysis.analyses.time_patterns import analyze_time_patterns

        dates = [f"2025-07-{d:02d}" for d in range(1, 29)]
        df = pd.DataFrame(
            {
                "transaction_date": dates,
                "amount": [50.0 + i * 2 for i in range(28)],
                "primary_account_num": [f"A{i % 5:03d}" for i in range(28)],
                "merchant_name": ["Test"] * 28,
                "business_flag": ["No"] * 28,
            }
        )
        result = analyze_time_patterns(df, df, df, Settings(data_file=None))
        assert "wom_dow_heatmap" in result.data
        heat = result.data["wom_dow_heatmap"]
        # Verify shape is suitable for heatmap (weeks x days)
        assert "week_label" in heat.columns
        day_cols = [c for c in heat.columns if c != "week_label"]
        assert len(day_cols) == 7  # Mon-Sun

    def test_day_of_month_chart_data(self):
        """Verify M16 day_of_month sheet has chart-ready data."""
        from txn_analysis.analyses.time_patterns import analyze_time_patterns

        dates = [f"2025-07-{d:02d}" for d in [3, 10, 18, 28]]
        df = pd.DataFrame(
            {
                "transaction_date": dates,
                "amount": [100.0] * 4,
                "primary_account_num": ["A001"] * 4,
                "merchant_name": ["Test"] * 4,
                "business_flag": ["No"] * 4,
            }
        )
        result = analyze_time_patterns(df, df, df, Settings(data_file=None))
        assert "day_of_month" in result.data
        dom = result.data["day_of_month"]
        assert "Period" in dom.columns
        assert "% of Spend" in dom.columns


# ---------------------------------------------------------------------------
# M9: Scorecard Bullet Chart
# ---------------------------------------------------------------------------


class TestScorecardChart:
    def test_scorecard_bullets(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        df = pd.DataFrame(
            {
                "metric": [
                    "Active Accounts",
                    "Avg Spend/Account/Month",
                    "Avg Txn/Account/Month",
                    "Average Ticket",
                ],
                "value": [500, 750.0, 18.5, 42.50],
                "benchmark": ["", 774.25, 20.2, 40.0],
                "status": ["", "At", "Below", "Above"],
                "format": ["", "$", "", "$"],
            }
        )
        result = AnalysisResult(
            name="portfolio_scorecard",
            title="Scorecard",
            data={"main": df},
            metadata={"benchmark_source": "PULSE 2024"},
        )
        fig = chart_scorecard_bullets(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_scorecard_empty(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.scorecard import chart_scorecard_bullets

        result = AnalysisResult(
            name="portfolio_scorecard",
            title="Scorecard",
            data={"main": pd.DataFrame()},
        )
        fig = chart_scorecard_bullets(result, chart_config)
        assert fig is not None
        plt.close(fig)


# ---------------------------------------------------------------------------
# Chart Registry
# ---------------------------------------------------------------------------


class TestChartRegistry:
    def test_registry_keys_match_analysis_names(self):
        """Every chart registry key should map to a valid analysis name."""
        from txn_analysis.analyses import ANALYSIS_REGISTRY
        from txn_analysis.charts import CHART_REGISTRY

        analysis_names = {name for name, _ in ANALYSIS_REGISTRY}
        for key in CHART_REGISTRY:
            base_name = key.split(":")[0]
            assert base_name in analysis_names, f"Chart '{key}' has no matching analysis '{base_name}'"

    def test_registry_has_m15_m22(self):
        from txn_analysis.charts import CHART_REGISTRY

        expected = [
            "recurring_payments",
            "wallet_radar",
            "spending_trends",
            "spending_profile",
            "txn_distribution",
            "segment_comparison",
            "portfolio_scorecard",
        ]
        for name in expected:
            assert name in CHART_REGISTRY, f"{name} missing from CHART_REGISTRY"

    def test_registry_has_m23_m24_m25(self):
        from txn_analysis.charts import CHART_REGISTRY

        expected = [
            "mailer_effectiveness",
            "mailer_effectiveness:decay",
            "mailer_effectiveness:cumulative",
            "mailer_effectiveness:lift",
            "activation",
            "activation:reactivation",
            "rfm",
            "rfm:heatmap",
        ]
        for name in expected:
            assert name in CHART_REGISTRY, f"{name} missing from CHART_REGISTRY"


# ---------------------------------------------------------------------------
# M23: Mailer Effectiveness Charts
# ---------------------------------------------------------------------------


class TestMailerEffectivenessCharts:
    def test_did_parallel_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.mailer_effectiveness import chart_did_parallel

        its_df = pd.DataFrame(
            {
                "Month": ["2025-04", "2025-05", "2025-06", "2025-07", "2025-08"],
                "actual_spend": [200, 210, 220, 280, 260],
                "fitted": [200, 210, 220, 230, 240],
                "counterfactual": [200, 210, 220, 230, 240],
                "post": [0, 0, 0, 1, 1],
            }
        )
        result = AnalysisResult(
            name="mailer_effectiveness",
            title="Mailer Effectiveness",
            data={"its": its_df},
            metadata={"did_estimate": 35.0},
        )
        fig = chart_did_parallel(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_decay_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.mailer_effectiveness import chart_decay_curve

        decay_df = pd.DataFrame(
            {
                "Month": ["2025-07", "2025-08", "2025-09"],
                "Months Post-Mailer": [1, 2, 3],
                "Responder Avg": [300, 280, 260],
                "Non-Responder Avg": [200, 200, 200],
                "Lift": [100, 80, 60],
            }
        )
        result = AnalysisResult(
            name="mailer_effectiveness",
            title="Mailer Effectiveness",
            data={"decay": decay_df},
            metadata={"half_life": 4.2},
        )
        fig = chart_decay_curve(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_cumulative_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.mailer_effectiveness import chart_cumulative_lift

        cum_df = pd.DataFrame(
            {
                "Month": ["2025-07", "2025-08", "2025-09"],
                "Responder Total": [5000, 4800, 4500],
                "Counterfactual": [3000, 3000, 3000],
                "Incremental": [2000, 1800, 1500],
                "Cumulative Incremental": [2000, 3800, 5300],
            }
        )
        result = AnalysisResult(
            name="mailer_effectiveness",
            title="Mailer Effectiveness",
            data={"cumulative": cum_df},
            metadata={},
        )
        fig = chart_cumulative_lift(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_lift_violin_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.mailer_effectiveness import chart_lift_violin

        lift_df = pd.DataFrame(
            {
                "account": [f"A{i:03d}" for i in range(20)],
                "group": ["Responder"] * 10 + ["Non-Responder"] * 10,
                "pre_avg": [100.0] * 20,
                "post_avg": [130.0] * 10 + [100.0] * 10,
                "lift": [30.0] * 10 + [0.0] * 10,
                "lift_pct": [30.0] * 10 + [0.0] * 10,
            }
        )
        result = AnalysisResult(
            name="mailer_effectiveness",
            title="Mailer Effectiveness",
            data={"lift_distribution": lift_df},
            metadata={},
        )
        fig = chart_lift_violin(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_empty_its_graceful(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.mailer_effectiveness import chart_did_parallel

        result = AnalysisResult(
            name="mailer_effectiveness",
            title="Mailer Effectiveness",
            data={},
            metadata={},
        )
        fig = chart_did_parallel(result, chart_config)
        assert fig is not None
        plt.close(fig)


# ---------------------------------------------------------------------------
# M24: Activation & Dormancy Charts
# ---------------------------------------------------------------------------


class TestActivationCharts:
    def test_dormancy_bars(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.activation import chart_dormancy_bars

        dormancy_df = pd.DataFrame(
            {
                "Status": ["Active", "At-Risk", "Dormant", "Lost"],
                "Accounts": [300, 80, 50, 20],
                "Avg Days Since Last Txn": [10, 45, 75, 120],
                "% of Total": [66.7, 17.8, 11.1, 4.4],
            }
        )
        result = AnalysisResult(
            name="activation",
            title="Dormancy",
            data={"dormancy": dormancy_df},
            metadata={},
        )
        fig = chart_dormancy_bars(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_reactivation_flow(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.activation import chart_reactivation_flow

        react_df = pd.DataFrame(
            {
                "Month": ["2025-07", "2025-08", "2025-09"],
                "Active": [400, 420, 410],
                "New": [30, 25, 20],
                "Reactivated": [10, 15, 12],
                "Went Dormant": [20, 15, 22],
            }
        )
        result = AnalysisResult(
            name="activation",
            title="Activation",
            data={"reactivation": react_df},
            metadata={},
        )
        fig = chart_reactivation_flow(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_empty_dormancy_graceful(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.activation import chart_dormancy_bars

        result = AnalysisResult(
            name="activation",
            title="Activation",
            data={},
            metadata={},
        )
        fig = chart_dormancy_bars(result, chart_config)
        assert fig is not None
        plt.close(fig)


# ---------------------------------------------------------------------------
# M25: RFM Charts
# ---------------------------------------------------------------------------


class TestRFMCharts:
    def test_rfm_segments_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.rfm import chart_rfm_segments

        seg_df = pd.DataFrame(
            {
                "Segment": ["Champions", "Loyal", "At-Risk", "Lost"],
                "Accounts": [50, 120, 80, 30],
                "Avg Spend": [5000.0, 2500.0, 800.0, 100.0],
                "Avg Txns": [45.0, 25.0, 10.0, 2.0],
                "Avg Recency (days)": [5, 15, 60, 120],
                "% of Total": [17.9, 42.9, 28.6, 10.7],
            }
        )
        result = AnalysisResult(
            name="rfm",
            title="RFM",
            data={"main": seg_df},
            metadata={"total_accounts": 280},
        )
        fig = chart_rfm_segments(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_rfm_heatmap_chart(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.rfm import chart_rfm_heatmap

        heatmap_df = pd.DataFrame(
            {
                "Recency Score": [1, 1, 2, 2, 3, 3, 4, 4],
                "Frequency Score": [1, 2, 1, 2, 1, 2, 1, 2],
                "Avg Monetary": [100, 200, 150, 300, 200, 400, 250, 500],
                "Count": [10, 15, 12, 20, 8, 25, 5, 18],
            }
        )
        result = AnalysisResult(
            name="rfm",
            title="RFM",
            data={"heatmap": heatmap_df},
            metadata={},
        )
        fig = chart_rfm_heatmap(result, chart_config)
        assert fig is not None
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_rfm_empty_graceful(self, chart_config):
        from txn_analysis.analyses.base import AnalysisResult
        from txn_analysis.charts.rfm import chart_rfm_segments

        result = AnalysisResult(
            name="rfm",
            title="RFM",
            data={"main": pd.DataFrame()},
            metadata={},
        )
        fig = chart_rfm_segments(result, chart_config)
        assert fig is not None
        plt.close(fig)
