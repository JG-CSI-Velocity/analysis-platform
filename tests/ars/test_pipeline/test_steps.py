"""Tests for pipeline steps (load, subsets, analyze)."""

import pandas as pd
import pytest

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import _REGISTRY, clear_registry, register
from ars_analysis.exceptions import DataError
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
from ars_analysis.pipeline.steps.analyze import step_analyze, step_analyze_selected
from ars_analysis.pipeline.steps.load import step_load_file
from ars_analysis.pipeline.steps.subsets import step_subsets

# --- Fixtures ---


@pytest.fixture
def odd_df():
    """DataFrame mimicking an ODD file with required columns."""
    return pd.DataFrame({
        "Stat Code": ["O"] * 6 + ["C"] * 4,
        "Product Code": ["DDA"] * 5 + ["SAV"] * 5,
        "Date Opened": pd.to_datetime(["2025-06-15"] * 10),
        "Balance": [1000.0 + i * 100 for i in range(10)],
        "Business?": ["No"] * 4 + ["Yes"] * 2 + ["No"] * 2 + ["Yes"] * 1 + ["No"] * 1,
        "Branch": ["Main"] * 6 + ["North"] * 4,
    })


@pytest.fixture
def ctx(tmp_path, odd_df):
    """PipelineContext with data loaded."""
    paths = OutputPaths(
        base_dir=tmp_path,
        charts_dir=tmp_path / "charts",
        excel_dir=tmp_path,
        pptx_dir=tmp_path,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2026.02",
            eligible_stat_codes=["O"],
            eligible_prod_codes=["DDA", "SAV"],
        ),
        paths=paths,
        data=odd_df,
        data_original=odd_df,
    )


@pytest.fixture
def ctx_no_data(tmp_path):
    """PipelineContext without data."""
    return PipelineContext(
        client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
        paths=OutputPaths(base_dir=tmp_path),
    )


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = dict(_REGISTRY)
    clear_registry()
    yield
    clear_registry()
    _REGISTRY.update(saved)


# --- Load step tests ---


class TestLoadStep:
    def test_load_csv_file(self, tmp_path, odd_df):
        csv_path = tmp_path / "test_data.csv"
        odd_df.to_csv(csv_path, index=False)

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        step_load_file(ctx, csv_path)
        assert ctx.data is not None
        assert len(ctx.data) == 10

    def test_load_xlsx_file(self, tmp_path, odd_df):
        xlsx_path = tmp_path / "test_data.xlsx"
        odd_df.to_excel(xlsx_path, index=False)

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        step_load_file(ctx, xlsx_path)
        assert ctx.data is not None
        assert len(ctx.data) == 10

    def test_load_missing_columns_raises(self, tmp_path):
        bad_df = pd.DataFrame({"Wrong Column Name Here": list(range(50))})
        csv_path = tmp_path / "bad.csv"
        bad_df.to_csv(csv_path, index=False)

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        with pytest.raises(DataError, match="missing required columns"):
            step_load_file(ctx, csv_path)

    def test_load_unsupported_format_raises(self, tmp_path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("hello")

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        with pytest.raises(DataError, match="Unsupported file format"):
            step_load_file(ctx, txt_path)

    def test_load_empty_file_raises(self, tmp_path):
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("a,b\n")

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        with pytest.raises(DataError, match="too small"):
            step_load_file(ctx, empty_csv)

    def test_load_renames_alias_columns(self, tmp_path):
        """Files with 'Prod Code' or 'Current Balance' get renamed to canonical names."""
        alias_df = pd.DataFrame({
            "Stat Code": ["O"] * 10,
            "Prod Code": ["DDA"] * 10,
            "Date Opened": pd.to_datetime(["2025-06-15"] * 10),
            "Current Balance": [1000.0 + i for i in range(10)],
            "Business?": ["No"] * 10,
        })
        csv_path = tmp_path / "alias_test.csv"
        alias_df.to_csv(csv_path, index=False)

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        step_load_file(ctx, csv_path)
        assert "Product Code" in ctx.data.columns
        assert "Balance" in ctx.data.columns
        assert "Prod Code" not in ctx.data.columns
        assert "Current Balance" not in ctx.data.columns

    def test_load_prearses_dates(self, tmp_path, odd_df):
        csv_path = tmp_path / "test_data.csv"
        odd_df.to_csv(csv_path, index=False)

        ctx = PipelineContext(
            client=ClientInfo(client_id="1200", client_name="Test CU", month="2026.02"),
            paths=OutputPaths(base_dir=tmp_path),
        )
        step_load_file(ctx, csv_path)
        assert pd.api.types.is_datetime64_any_dtype(ctx.data["Date Opened"])


# --- Subsets step tests ---


class TestSubsetsStep:
    def test_creates_open_accounts(self, ctx):
        step_subsets(ctx)
        assert ctx.subsets.open_accounts is not None
        assert len(ctx.subsets.open_accounts) == 6  # 6 "O" stat codes

    def test_creates_eligible_data(self, ctx):
        step_subsets(ctx)
        assert ctx.subsets.eligible_data is not None
        assert len(ctx.subsets.eligible_data) == 6  # O with DDA or SAV

    def test_creates_personal_business_split(self, ctx):
        step_subsets(ctx)
        assert ctx.subsets.eligible_personal is not None
        assert ctx.subsets.eligible_business is not None
        # Of 6 eligible: 4 personal, 2 business
        assert len(ctx.subsets.eligible_personal) == 4
        assert len(ctx.subsets.eligible_business) == 2

    def test_no_data_raises(self, ctx_no_data):
        with pytest.raises(DataError, match="no data loaded"):
            step_subsets(ctx_no_data)

    def test_no_eligible_stat_codes_skips_eligible(self, ctx):
        ctx.client.eligible_stat_codes = []
        step_subsets(ctx)
        assert ctx.subsets.eligible_data is None


# --- Analyze step tests ---


def _make_test_module(module_id="test.mod"):
    class TestMod(AnalysisModule):
        display_name = "Test"
        section = "overview"
        required_columns = ("Stat Code",)

        def run(self, ctx):
            return [AnalysisResult(slide_id="T1", title="Test Result")]

    TestMod.module_id = module_id
    return TestMod


class TestAnalyzeStep:
    def test_analyze_runs_registered_modules(self, ctx):
        cls = _make_test_module("overview.stat_codes")
        register(cls)
        step_analyze(ctx)
        assert "overview.stat_codes" in ctx.results
        assert len(ctx.results["overview.stat_codes"]) == 1

    def test_analyze_skips_modules_with_validation_errors(self, ctx):
        cls = _make_test_module("test.needs_col")
        cls.required_columns = ("Nonexistent Column",)
        register(cls)
        step_analyze(ctx)
        assert "test.needs_col" not in ctx.results

    def test_analyze_selected_runs_specific_modules(self, ctx):
        cls = _make_test_module("test.selected")
        register(cls)
        step_analyze_selected(ctx, ["test.selected"])
        assert "test.selected" in ctx.results

    def test_analyze_no_modules_is_noop(self, ctx):
        step_analyze(ctx)
        assert ctx.results == {}

    def test_analyze_collects_all_slides(self, ctx):
        cls = _make_test_module("overview.stat_codes")
        register(cls)
        step_analyze(ctx)
        assert len(ctx.all_slides) == 1
        assert ctx.all_slides[0].slide_id == "T1"

    def test_analyze_isolates_module_failures(self, ctx):
        class FailMod(AnalysisModule):
            module_id = "test.fail"
            display_name = "Fail"
            section = "overview"

            def run(self, ctx):
                raise RuntimeError("boom")

        register(FailMod)
        # Should not raise
        step_analyze(ctx)
        assert "test.fail" not in ctx.results
