"""Tests for the overview analysis modules."""

import pandas as pd
import pytest

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.analytics.overview.eligibility import EligibilityFunnel
from ars_analysis.analytics.overview.product_codes import ProductCodeDistribution
from ars_analysis.analytics.overview.stat_codes import StatCodeDistribution
from ars_analysis.pipeline.context import ClientInfo, DataSubsets, OutputPaths, PipelineContext


@pytest.fixture
def stat_code_df():
    """DataFrame with stat code + business flag columns."""
    return pd.DataFrame(
        {
            "Stat Code": ["O"] * 6 + ["C"] * 3 + ["F"] * 1,
            "Business?": ["No"] * 4 + ["Yes"] * 2 + ["No"] * 2 + ["Yes"] * 1 + ["No"] * 1,
            "Balance": [1000.0] * 10,
        }
    )


@pytest.fixture
def ctx_with_data(stat_code_df, tmp_output_dir):
    """PipelineContext with stat code data loaded."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    return PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=paths,
        data=stat_code_df,
        subsets=DataSubsets(),
    )


class TestStatCodeDistribution:
    def test_module_attributes(self):
        mod = StatCodeDistribution()
        assert mod.module_id == "overview.stat_codes"
        assert mod.section == "overview"
        assert "Stat Code" in mod.required_columns

    def test_validate_passes_with_required_columns(self, ctx_with_data):
        mod = StatCodeDistribution()
        errors = mod.validate(ctx_with_data)
        assert errors == []

    def test_validate_fails_without_stat_code(self, ctx_with_data):
        ctx_with_data.data = ctx_with_data.data.drop(columns=["Stat Code"])
        mod = StatCodeDistribution()
        errors = mod.validate(ctx_with_data)
        assert len(errors) == 1
        assert "Stat Code" in errors[0]

    def test_run_returns_analysis_results(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        assert len(results) == 1
        assert isinstance(results[0], AnalysisResult)

    def test_run_result_has_correct_slide_id(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        assert results[0].slide_id == "A1"

    def test_run_produces_excel_data(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        excel = results[0].excel_data
        assert "Distribution" in excel
        assert "Summary" in excel

    def test_run_summary_has_correct_stat_codes(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        summary = results[0].excel_data["Summary"]
        codes = set(summary["Stat Code"].tolist())
        assert codes == {"O", "C", "F"}

    def test_run_summary_counts_are_correct(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        summary = results[0].excel_data["Summary"]
        # O=6, C=3, F=1
        o_row = summary[summary["Stat Code"] == "O"].iloc[0]
        assert o_row["Total Count"] == 6
        assert o_row["Business Count"] == 2
        assert o_row["Personal Count"] == 4

    def test_run_generates_chart(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        assert results[0].chart_path is not None
        assert results[0].chart_path.exists()

    def test_run_notes_contain_top_code(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        # O is the top code (6 out of 10)
        assert "O" in results[0].notes
        assert "60.0%" in results[0].notes

    def test_run_marks_success(self, ctx_with_data):
        mod = StatCodeDistribution()
        results = mod.run(ctx_with_data)
        assert results[0].success is True
        assert results[0].error == ""


# -- Product Code Distribution ------------------------------------------------


class TestProductCodeDistribution:
    def test_module_attributes(self):
        mod = ProductCodeDistribution()
        assert mod.module_id == "overview.product_codes"
        assert mod.section == "overview"
        assert "Product Code" in mod.required_columns

    def test_validate_passes_with_required_columns(self, overview_ctx):
        mod = ProductCodeDistribution()
        errors = mod.validate(overview_ctx)
        assert errors == []

    def test_validate_fails_without_product_code(self, overview_ctx):
        overview_ctx.data = overview_ctx.data.drop(columns=["Product Code"])
        mod = ProductCodeDistribution()
        errors = mod.validate(overview_ctx)
        assert len(errors) == 1
        assert "Product Code" in errors[0]

    def test_run_returns_analysis_results(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        assert len(results) == 1
        assert isinstance(results[0], AnalysisResult)

    def test_run_result_has_correct_slide_id(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        assert results[0].slide_id == "A1b"

    def test_run_produces_excel_data(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        excel = results[0].excel_data
        assert "Distribution" in excel
        assert "Summary" in excel

    def test_run_summary_has_correct_product_codes(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        summary = results[0].excel_data["Summary"]
        codes = set(summary["Product Code"].tolist())
        assert codes == {"DDA", "SAV", "CD"}

    def test_run_summary_counts_are_correct(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        summary = results[0].excel_data["Summary"]
        # DDA=12 (10+2), SAV=5, CD=3
        dda_row = summary[summary["Product Code"] == "DDA"].iloc[0]
        assert dda_row["Total Count"] == 12

    def test_run_generates_chart(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        assert results[0].chart_path is not None
        assert results[0].chart_path.exists()

    def test_run_marks_success(self, overview_ctx):
        mod = ProductCodeDistribution()
        results = mod.run(overview_ctx)
        assert results[0].success is True


# -- Eligibility Funnel -------------------------------------------------------


class TestEligibilityFunnel:
    def test_module_attributes(self):
        mod = EligibilityFunnel()
        assert mod.module_id == "overview.eligibility"
        assert mod.section == "overview"
        assert "Stat Code" in mod.required_columns
        assert "Product Code" in mod.required_columns

    def test_validate_passes_with_required_columns(self, overview_ctx):
        mod = EligibilityFunnel()
        errors = mod.validate(overview_ctx)
        assert errors == []

    def test_validate_fails_without_stat_code(self, overview_ctx):
        overview_ctx.data = overview_ctx.data.drop(columns=["Stat Code"])
        mod = EligibilityFunnel()
        errors = mod.validate(overview_ctx)
        assert len(errors) > 0
        assert "Stat Code" in errors[0]

    def test_run_returns_analysis_results(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        assert len(results) == 1
        assert isinstance(results[0], AnalysisResult)

    def test_run_result_has_correct_slide_id(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        assert results[0].slide_id == "A3"

    def test_run_produces_funnel_data(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        funnel = results[0].excel_data["Funnel"]
        assert "Stage" in funnel.columns
        assert "Count" in funnel.columns
        assert "Drop-off" in funnel.columns

    def test_funnel_has_correct_stages(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        funnel = results[0].excel_data["Funnel"]
        main_stages = funnel[~funnel["Stage"].str.startswith("   ")]
        # Without mailable: 5 stages (Total, Open, Stat, Prod, Eligible)
        assert len(main_stages) == 5

    def test_funnel_total_is_full_data(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        funnel = results[0].excel_data["Funnel"]
        total_row = funnel[funnel["Stage"].str.contains("Total")]
        assert total_row.iloc[0]["Count"] == len(overview_ctx.data)

    def test_funnel_eligible_matches_subsets(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        funnel = results[0].excel_data["Funnel"]
        eligible_row = funnel[funnel["Stage"].str.contains("ELIGIBLE")]
        assert eligible_row.iloc[0]["Count"] == len(overview_ctx.subsets.eligible_data)

    def test_funnel_counts_are_decreasing(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        funnel = results[0].excel_data["Funnel"]
        main_stages = funnel[~funnel["Stage"].str.startswith("   ")]
        counts = main_stages["Count"].tolist()
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i - 1]

    def test_funnel_has_pb_split(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        funnel = results[0].excel_data["Funnel"]
        split_rows = funnel[funnel["Stage"].str.startswith("   ")]
        assert len(split_rows) == 2

    def test_run_generates_chart(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        assert results[0].chart_path is not None
        assert results[0].chart_path.exists()

    def test_run_stores_results_in_context(self, overview_ctx):
        mod = EligibilityFunnel()
        mod.run(overview_ctx)
        assert "a3" in overview_ctx.results
        assert "funnel" in overview_ctx.results["a3"]
        assert "insights" in overview_ctx.results["a3"]

    def test_run_marks_success(self, overview_ctx):
        mod = EligibilityFunnel()
        results = mod.run(overview_ctx)
        assert results[0].success is True
