"""Tests for analyses/cohort.py and cohort_detail.py -- ax27, ax28, ax29, ax31, ax32, ax34, ax36."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.cohort import (
    analyze_cohort_activation,
    analyze_cohort_heatmap,
)
from ics_toolkit.analysis.analyses.cohort_detail import (
    analyze_activation_personas,
    analyze_activation_summary,
    analyze_branch_activation,
    analyze_cohort_milestones,
    analyze_growth_patterns,
)


class TestAnalyzeCohortActivation:
    """ax27: Cohort Activation by Opening Month."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_opening_month_column(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Opening Month" in result.df.columns

    def test_has_milestone_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for milestone in ["M1", "M3", "M6", "M12"]:
            assert f"{milestone} Active" in result.df.columns
            assert f"{milestone} Activation %" in result.df.columns

    def test_has_cohort_size_and_avg_bal(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Cohort Size" in result.df.columns
        assert "Avg Bal" in result.df.columns

    def test_cohorts_after_cohort_start(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            all_months = result.df["Opening Month"].values
            for month in all_months:
                assert month >= sample_settings.cohort_start


class TestAnalyzeCohortHeatmap:
    """ax28: Cohort Heatmap."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_heatmap(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_month_tag_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_heatmap(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            assert "Opening Month" in result.df.columns
            # At least some L12M tags should be columns
            tag_cols = [c for c in result.df.columns if c != "Opening Month"]
            assert len(tag_cols) > 0

    def test_values_are_non_negative_where_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_heatmap(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            numeric_cols = [c for c in result.df.columns if c != "Opening Month"]
            for col in numeric_cols:
                vals = pd.to_numeric(result.df[col], errors="coerce").dropna()
                if not vals.empty:
                    assert (vals >= 0).all()

    def test_months_before_cohort_are_blank(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        """Months before a cohort's opening month should be None/NaN, not 0."""
        result = analyze_cohort_heatmap(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            from datetime import datetime

            for _, row in result.df.iterrows():
                cohort_date = datetime.strptime(row["Opening Month"], "%Y-%m")
                for col in result.df.columns:
                    if col == "Opening Month":
                        continue
                    tag_date = datetime.strptime(col, "%b%y")
                    if tag_date < cohort_date:
                        assert pd.isna(row[col]), (
                            f"Cohort {row['Opening Month']}, month {col} "
                            f"should be blank but got {row[col]}"
                        )


class TestAnalyzeCohortMilestones:
    """ax29: Cohort Milestones."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_milestones(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_milestone_swipe_spend_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_milestones(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        for milestone in ["M1", "M3", "M6", "M12"]:
            assert f"{milestone} Active" in result.df.columns
            assert f"{milestone} Activation %" in result.df.columns
            assert f"{milestone} Avg Swipes" in result.df.columns
            assert f"{milestone} Avg Spend" in result.df.columns

    def test_has_cohort_metadata(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_cohort_milestones(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Opening Month" in result.df.columns
        assert "Cohort Size" in result.df.columns
        assert "Avg Bal" in result.df.columns


class TestAnalyzeActivationSummary:
    """ax31: Activation Summary."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_metric_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_has_milestone_rates(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = set(result.df["Metric"].values)
        assert "M1 Activation Rate" in metrics
        assert "M3 Activation Rate" in metrics
        assert "M6 Activation Rate" in metrics
        assert "M12 Activation Rate" in metrics


class TestAnalyzeGrowthPatterns:
    """ax32: Growth Patterns."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_growth_patterns(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_growth_patterns(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Opening Month" in result.df.columns
        assert "Cohort Size" in result.df.columns
        assert "M1 Swipes" in result.df.columns
        assert "M1->M3 Growth" in result.df.columns

    def test_has_growth_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_growth_patterns(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        growth_cols = ["M1->M3 Growth", "M3->M6 Growth", "M6->M12 Growth"]
        for col in growth_cols:
            assert col in result.df.columns


class TestAnalyzeActivationPersonas:
    """ax34: Activation Personas."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_personas(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_personas(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Category", "Account Count", "Total M1 Swipes", "Total M3 Swipes", "% of Total"}
        if not result.df.empty:
            assert expected.issubset(set(result.df.columns))

    def test_persona_categories_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_personas(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            categories = set(result.df["Category"].values)
            valid_categories = {
                "Fast Activator",
                "Slow Burner",
                "One and Done",
                "Never Activator",
            }
            # All present categories should be from the valid set
            assert categories.issubset(valid_categories)

    def test_percentages_sum_to_hundred(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_activation_personas(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            total_pct = result.df["% of Total"].sum()
            assert abs(total_pct - 100.0) < 0.1


class TestAnalyzeBranchActivation:
    """ax36: Branch Activation."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Branch", "Cohort Size", "Active Count", "Activation Rate"}
        assert expected.issubset(set(result.df.columns))

    def test_branches_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_branch_activation(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        if not result.df.empty:
            # Should have at least one branch row + Total
            assert len(result.df) >= 2
