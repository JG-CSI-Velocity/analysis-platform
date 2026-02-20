"""Tests for analyses/summary.py -- ax01 through ax07."""

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.summary import (
    analyze_debit_by_branch,
    analyze_debit_by_prod,
    analyze_debit_dist,
    analyze_open_ics,
    analyze_penetration_by_branch,
    analyze_prod_code,
    analyze_stat_code,
    analyze_total_ics,
)


class TestAnalyzeTotalICS:
    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_total_ics(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_total_ics(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Category" in result.df.columns
        assert "Count" in result.df.columns
        assert "% of Total" in result.df.columns

    def test_counts_add_up(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_total_ics(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        total = result.df[result.df["Category"] == "Total Accounts"]["Count"].iloc[0]
        ics = result.df[result.df["Category"] == "ICS Accounts"]["Count"].iloc[0]
        non_ics = result.df[result.df["Category"] == "Non-ICS Accounts"]["Count"].iloc[0]
        assert ics + non_ics == total


class TestAnalyzeOpenICS:
    def test_returns_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_open_ics(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_only_open_accounts(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_open_ics(sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings)
        total = result.df[result.df["Category"] == "Total Open Accounts"]["Count"].iloc[0]
        open_count = len(sample_df[sample_df["Stat Code"] == "O"])
        assert total == open_count


class TestAnalyzeStatCode:
    def test_returns_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_stat_code(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_stat_code(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Stat Code"].values

    def test_includes_not_in_dump(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        sample_settings.ics_not_in_dump = 80
        result = analyze_stat_code(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Not in Data Dump" in result.df["Stat Code"].values


class TestAnalyzeProdCode:
    def test_returns_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_prod_code(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_prod_code(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Prod Code"].values


class TestAnalyzeDebitDist:
    def test_returns_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_debit_dist(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None


class TestAnalyzeDebitByProd:
    def test_returns_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_debit_by_prod(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_rate_column(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_debit_by_prod(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "% with Debit" in result.df.columns


class TestAnalyzeDebitByBranch:
    def test_returns_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_debit_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_rate_column(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_debit_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "% with Debit" in result.df.columns


class TestAnalyzePenetrationByBranch:
    """ax64: ICS Penetration by Branch."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_penetration_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.name == "ICS Penetration by Branch"
        assert result.error is None

    def test_has_expected_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_penetration_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        expected = {"Branch", "Total Accounts", "ICS Accounts", "Penetration %"}
        assert expected.issubset(set(result.df.columns))

    def test_has_total_row(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_penetration_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Total" in result.df["Branch"].values

    def test_penetration_between_0_and_100(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_penetration_by_branch(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        data = result.df[result.df["Branch"] != "Total"]
        assert (data["Penetration %"] >= 0).all()
        assert (data["Penetration %"] <= 100).all()
