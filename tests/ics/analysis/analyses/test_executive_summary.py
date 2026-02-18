"""Tests for analyses/executive_summary.py -- ax999."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.executive_summary import analyze_executive_summary
from ics_toolkit.analysis.analyses.templates import kpi_summary


class TestAnalyzeExecutiveSummary:
    """ax999: Executive Summary."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_metric_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_expected_metrics_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = set(result.df["Metric"].values)
        assert "Total ICS Accounts" in metrics
        assert "Penetration Rate" in metrics
        assert "Stat O Count" in metrics
        assert "Active Rate (L12M)" in metrics
        assert "Top Branch" in metrics
        assert "Bottom Branch" in metrics
        assert "Fast Activator %" in metrics
        assert "Never Activator %" in metrics
        assert "Never Activator Count" in metrics
        assert "Revenue at Risk" in metrics
        assert "Estimated Interchange" in metrics

    def test_without_prior_results(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=None,
        )
        assert result.error is None
        active_row = result.df[result.df["Metric"] == "Active Rate (L12M)"]
        assert active_row["Value"].iloc[0] == "N/A"

    def test_with_prior_results(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        activity_kpis = kpi_summary(
            [
                ("Total Accounts", 100),
                ("Active Accounts", 75),
                ("% Active", 62.5),
                ("Total Swipes", 5000),
                ("Total Spend", 150000.00),
            ]
        )
        mock_activity = AnalysisResult(
            name="Activity Summary",
            title="test",
            df=activity_kpis,
        )

        persona_df = pd.DataFrame(
            {
                "Category": [
                    "Fast Activator",
                    "Slow Burner",
                    "One and Done",
                    "Never Activator",
                ],
                "Account Count": [40, 20, 15, 25],
                "Total M1 Swipes": [200, 0, 50, 0],
                "Total M3 Swipes": [300, 100, 0, 0],
                "% of Total": [40.0, 20.0, 15.0, 25.0],
            }
        )
        mock_personas = AnalysisResult(
            name="Activation Personas",
            title="test",
            df=persona_df,
        )

        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=[mock_activity, mock_personas],
        )
        assert result.error is None

        active_row = result.df[result.df["Metric"] == "Active Rate (L12M)"]
        assert active_row["Value"].iloc[0] == "62.5"

        fast_row = result.df[result.df["Metric"] == "Fast Activator %"]
        assert fast_row["Value"].iloc[0] == "40.0"

    def test_total_ics_uses_dataframe_length(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
        )
        total_row = result.df[result.df["Metric"] == "Total ICS Accounts"]
        assert int(total_row["Value"].iloc[0]) == len(ics_all)

    def test_stat_o_count(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
        )
        stat_o_row = result.df[result.df["Metric"] == "Stat O Count"]
        assert int(stat_o_row["Value"].iloc[0]) == len(ics_stat_o)

    def test_empty_prior_results_list(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=[],
        )
        assert result.error is None
        swipes_row = result.df[result.df["Metric"] == "Total Swipes (L12M)"]
        assert swipes_row["Value"].iloc[0] == "N/A"

    def test_metadata_has_hero_kpis(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "hero_kpis" in result.metadata
        assert "Total ICS Accounts" in result.metadata["hero_kpis"]
        assert "Penetration Rate" in result.metadata["hero_kpis"]
        assert "Active Rate" in result.metadata["hero_kpis"]

    def test_metadata_has_traffic_lights(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "traffic_lights" in result.metadata
        tl = result.metadata["traffic_lights"]
        for key in ("Penetration Rate", "Active Rate"):
            assert tl[key] in ("green", "yellow", "red")

    def test_metadata_has_narrative(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "narrative" in result.metadata
        assert isinstance(result.metadata["narrative"], list)

    def test_narrative_with_prior_results(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        activity_kpis = kpi_summary([("% Active", 62.5), ("Total Swipes", 5000)])
        mock_activity = AnalysisResult(name="Activity Summary", title="test", df=activity_kpis)

        revenue_kpis = kpi_summary(
            [
                ("Estimated Annual Interchange", 15000.0),
                ("Revenue at Risk (Dormant)", 5000.0),
            ]
        )
        mock_revenue = AnalysisResult(name="Revenue Impact", title="test", df=revenue_kpis)

        persona_df = pd.DataFrame(
            {
                "Category": ["Fast Activator", "Never Activator"],
                "Account Count": [40, 25],
                "Total M1 Swipes": [200, 0],
                "Total M3 Swipes": [300, 0],
                "% of Total": [61.5, 38.5],
            }
        )
        mock_personas = AnalysisResult(name="Activation Personas", title="test", df=persona_df)

        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=[mock_activity, mock_revenue, mock_personas],
        )

        narrative = result.metadata["narrative"]
        types = [b["type"] for b in narrative]
        assert "what" in types
        assert "so_what" in types
        assert "now_what" in types
