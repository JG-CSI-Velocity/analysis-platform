"""Tests for branch performance scorecard (A19 series)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ars_analysis.analytics.insights.branch_scorecard import (
    BranchScorecard,
    MIN_BRANCHES,
    _build_branch_data,
)
from ars_analysis.pipeline.context import (
    ClientInfo,
    DataSubsets,
    OutputPaths,
    PipelineContext,
)


@pytest.fixture
def branch_df():
    """DataFrame with 5 branches for scorecard tests."""
    n = 100
    branches = (
        ["Main"] * 30 + ["North"] * 25 + ["South"] * 20
        + ["West"] * 15 + ["East"] * 10
    )
    return pd.DataFrame({
        "Date Opened": pd.date_range("2020-01-01", periods=n, freq="ME"),
        "Stat Code": ["O"] * 80 + ["C"] * 20,
        "Product Code": ["DDA"] * n,
        "Debit?": ["Yes"] * 60 + ["No"] * 40,
        "Business?": ["No"] * 75 + ["Yes"] * 25,
        "Branch": branches,
        "Reg E Code 2024.02": ["Y"] * 40 + ["N"] * 30 + ["Y"] * 15 + ["N"] * 15,
        "Avg Bal": [1000.0 + i * 50 for i in range(n)],
    })


@pytest.fixture
def branch_ctx(branch_df, tmp_output_dir):
    """PipelineContext with branch data for scorecard tests."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = branch_df
    open_accts = df[df["Stat Code"] == "O"]
    return PipelineContext(
        client=ClientInfo(
            client_id="9999",
            client_name="Test CU",
            month="2024.09",
            eligible_stat_codes=["O"],
            ic_rate=0.0015,
        ),
        paths=paths,
        data=df,
        subsets=DataSubsets(
            open_accounts=open_accts,
            eligible_data=open_accts.copy(),
            eligible_personal=open_accts[open_accts["Business?"] == "No"],
            eligible_business=open_accts[open_accts["Business?"] == "Yes"],
            eligible_with_debit=open_accts[open_accts["Debit?"] == "Yes"],
        ),
        start_date=date(2024, 2, 1),
        end_date=date(2024, 9, 30),
    )


class TestBuildBranchData:
    def test_returns_dataframe(self, branch_ctx):
        result = _build_branch_data(branch_ctx)
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, branch_ctx):
        result = _build_branch_data(branch_ctx)
        for col in ("branch", "dctr", "rege_rate", "attrition_rate", "n_accounts"):
            assert col in result.columns

    def test_correct_branch_count(self, branch_ctx):
        result = _build_branch_data(branch_ctx)
        assert len(result) == 5

    def test_dctr_range(self, branch_ctx):
        result = _build_branch_data(branch_ctx)
        assert (result["dctr"] >= 0).all()
        assert (result["dctr"] <= 1).all()

    def test_attrition_range(self, branch_ctx):
        result = _build_branch_data(branch_ctx)
        assert (result["attrition_rate"] >= 0).all()
        assert (result["attrition_rate"] <= 1).all()

    def test_none_without_branch_column(self, branch_ctx):
        branch_ctx.data = branch_ctx.data.drop(columns=["Branch"])
        assert _build_branch_data(branch_ctx) is None

    def test_none_with_few_branches(self, branch_ctx):
        branch_ctx.data = branch_ctx.data[branch_ctx.data["Branch"].isin(["Main", "North"])]
        assert _build_branch_data(branch_ctx) is None

    def test_none_with_no_data(self, branch_ctx):
        branch_ctx.data = None
        assert _build_branch_data(branch_ctx) is None

    def test_accounts_sum_matches(self, branch_ctx):
        result = _build_branch_data(branch_ctx)
        assert result["n_accounts"].sum() == len(branch_ctx.data)


class TestBranchScorecardModule:
    def test_produces_two_slides(self, branch_ctx):
        module = BranchScorecard()
        results = module.run(branch_ctx)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_a19_1_scorecard(self, branch_ctx):
        module = BranchScorecard()
        results = module.run(branch_ctx)
        a19_1 = [r for r in results if r.slide_id == "A19.1"]
        assert len(a19_1) == 1
        assert a19_1[0].chart_path.exists()
        assert "Best" in a19_1[0].notes

    def test_a19_2_opportunity_map(self, branch_ctx):
        module = BranchScorecard()
        results = module.run(branch_ctx)
        a19_2 = [r for r in results if r.slide_id == "A19.2"]
        assert len(a19_2) == 1
        assert a19_2[0].chart_path.exists()
        assert "$" in a19_2[0].notes

    def test_few_branches_returns_failure(self, branch_ctx):
        branch_ctx.data = branch_ctx.data[branch_ctx.data["Branch"].isin(["Main", "North"])]
        module = BranchScorecard()
        results = module.run(branch_ctx)
        assert len(results) == 1
        assert not results[0].success
        assert str(MIN_BRANCHES) in results[0].error

    def test_no_debit_column_still_works(self, branch_ctx):
        branch_ctx.data = branch_ctx.data.drop(columns=["Debit?"])
        module = BranchScorecard()
        results = module.run(branch_ctx)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_module_metadata(self):
        module = BranchScorecard()
        assert module.module_id == "insights.branch_scorecard"
        assert module.section == "insights"
