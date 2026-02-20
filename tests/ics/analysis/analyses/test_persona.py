"""Tests for analyses/persona.py -- Persona Deep-Dive (ax55-ax62)."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.persona import (
    PERSONA_ORDER,
    _classify_accounts,
    analyze_persona_by_balance,
    analyze_persona_by_branch,
    analyze_persona_by_source,
    analyze_persona_cohort_trend,
    analyze_persona_contribution,
    analyze_persona_overview,
    analyze_persona_revenue,
    analyze_persona_velocity,
)


class TestClassifyAccounts:
    """Shared per-account classifier."""

    def test_returns_dataframe(self, ics_stat_o_debit, sample_settings):
        result = _classify_accounts(ics_stat_o_debit, sample_settings)
        assert isinstance(result, pd.DataFrame)

    def test_has_persona_column(self, ics_stat_o_debit, sample_settings):
        result = _classify_accounts(ics_stat_o_debit, sample_settings)
        if not result.empty:
            assert "Persona" in result.columns

    def test_personas_are_valid(self, ics_stat_o_debit, sample_settings):
        result = _classify_accounts(ics_stat_o_debit, sample_settings)
        if not result.empty:
            assert set(result["Persona"].unique()).issubset(set(PERSONA_ORDER))

    def test_has_swipe_columns(self, ics_stat_o_debit, sample_settings):
        result = _classify_accounts(ics_stat_o_debit, sample_settings)
        if not result.empty:
            assert "M1 Swipes" in result.columns
            assert "M3 Swipes" in result.columns

    def test_has_enrichment_columns(self, ics_stat_o_debit, sample_settings):
        result = _classify_accounts(ics_stat_o_debit, sample_settings)
        if not result.empty:
            for col in ("Branch", "Source", "Curr Bal", "Total L12M Swipes"):
                assert col in result.columns

    def test_empty_input(self, sample_settings):
        empty = pd.DataFrame()
        result = _classify_accounts(empty, sample_settings)
        assert result.empty


class TestAnalyzePersonaOverview:
    """ax55: Persona Overview."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona Overview"
        assert result.sheet_name == "55_Persona_Overview"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = [
            "Persona",
            "Account Count",
            "% of Total",
            "Total M1 Swipes",
            "Total M3 Swipes",
            "Avg M1 Swipes",
            "Avg M3 Swipes",
            "Total L12M Spend",
            "Avg Balance",
        ]
        assert list(result.df.columns) == expected

    def test_has_four_personas(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert len(result.df) == 4
        assert list(result.df["Persona"]) == PERSONA_ORDER

    def test_percentages_sum_to_100(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_overview(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        total_pct = result.df["% of Total"].sum()
        assert abs(total_pct - 100.0) < 0.5


class TestAnalyzePersonaContribution:
    """ax56: Persona Swipe Contribution."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_contribution(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona Swipe Contribution"
        assert result.sheet_name == "56_Persona_Contrib"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_contribution(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = [
            "Persona",
            "% of Accounts",
            "% of M1 Swipes",
            "% of M3 Swipes",
            "% of L12M Swipes",
            "% of L12M Spend",
        ]
        assert list(result.df.columns) == expected

    def test_account_pct_sums_to_100(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_contribution(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        total = result.df["% of Accounts"].sum()
        assert abs(total - 100.0) < 0.5


class TestAnalyzePersonaByBranch:
    """ax57: Persona by Branch."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona by Branch"
        assert result.sheet_name == "57_Persona_Branch"

    def test_has_persona_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            for persona in PERSONA_ORDER:
                assert persona in result.df.columns

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_persona_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            last_branch = str(result.df.iloc[-1]["Branch"]).lower()
            assert "total" in last_branch


class TestAnalyzePersonaBySource:
    """ax58: Persona by Source."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona by Source"
        assert result.sheet_name == "58_Persona_Source"

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_persona_by_source(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            last_source = str(result.df.iloc[-1]["Source"]).lower()
            assert "total" in last_source


class TestAnalyzePersonaRevenue:
    """ax59: Persona Revenue Impact."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_revenue(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona Revenue Impact"
        assert result.sheet_name == "59_Persona_Revenue"

    def test_has_metric_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_revenue(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert list(result.df.columns) == ["Metric", "Value"]

    def test_has_interchange_metric(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_revenue(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = list(result.df["Metric"])
        assert "Total L12M Interchange" in metrics

    def test_has_revenue_lift(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_revenue(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = list(result.df["Metric"])
        assert "Revenue Lift (25% Never -> Slow)" in metrics


class TestAnalyzePersonaByBalance:
    """ax60: Persona by Balance Tier."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_by_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona by Balance Tier"
        assert result.sheet_name == "60_Persona_Balance"

    def test_has_persona_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_by_balance(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            for persona in PERSONA_ORDER:
                assert persona in result.df.columns


class TestAnalyzePersonaVelocity:
    """ax61: Persona Velocity."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_velocity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona Velocity"
        assert result.sheet_name == "61_Persona_Velocity"

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_velocity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = ["Persona", "Days Bucket", "Count", "% of Persona"]
        assert list(result.df.columns) == expected

    def test_all_personas_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_velocity(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            personas_in_result = set(result.df["Persona"].unique())
            for persona in PERSONA_ORDER:
                assert persona in personas_in_result


class TestAnalyzePersonaCohortTrend:
    """ax62: Persona Cohort Trend."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_cohort_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "Persona Cohort Trend"
        assert result.sheet_name == "62_Persona_Cohort"

    def test_has_persona_pct_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_cohort_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert "Opening Month" in result.df.columns
            assert "Fast Activator %" in result.df.columns
            assert "Total" in result.df.columns

    def test_cohorts_sorted(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_persona_cohort_trend(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if len(result.df) > 1:
            months = list(result.df["Opening Month"])
            assert months == sorted(months)
