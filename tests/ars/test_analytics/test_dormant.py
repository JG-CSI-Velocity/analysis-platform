"""Tests for dormant opportunity analysis (A20 series)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ars_analysis.analytics.insights.dormant import (
    DormantOpportunity,
    _detect_debit_col,
    _detect_spend_cols,
    _find_declining_accounts,
    _find_dormant_accounts,
)
from ars_analysis.pipeline.context import (
    ClientInfo,
    DataSubsets,
    OutputPaths,
    PipelineContext,
)


@pytest.fixture
def dormant_df():
    """DataFrame with a mix of debit/non-debit accounts and declining spend."""
    n = 80
    return pd.DataFrame(
        {
            "Date Opened": pd.date_range("2019-01-01", periods=n, freq="ME"),
            "Stat Code": ["O"] * 65 + ["C"] * 15,
            "Product Code": ["DDA"] * n,
            "Debit?": ["Yes"] * 50 + ["No"] * 30,
            "Business?": ["No"] * 60 + ["Yes"] * 20,
            "Branch": ["Main"] * 30 + ["North"] * 25 + ["South"] * 25,
            "Avg Bal": (
                [2000.0 + i * 100 for i in range(50)]  # debit holders
                + [5000.0 + i * 200 for i in range(30)]  # non-debit (higher balance)
            ),
            # 6 spend months: first 3 high, last 3 declining for rows 50-79
            "Feb24 Spend": [800.0 + i * 10 for i in range(n)],
            "Mar24 Spend": [790.0 + i * 10 for i in range(n)],
            "Apr24 Spend": [780.0 + i * 10 for i in range(n)],
            "May24 Spend": [400.0 + i * 5 for i in range(50)] + [300.0 - i * 5 for i in range(30)],
            "Jun24 Spend": [380.0 + i * 5 for i in range(50)] + [250.0 - i * 5 for i in range(30)],
            "Jul24 Spend": [370.0 + i * 5 for i in range(50)] + [200.0 - i * 5 for i in range(30)],
        }
    )


@pytest.fixture
def dormant_ctx(dormant_df, tmp_output_dir):
    """PipelineContext for dormant opportunity tests."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = dormant_df
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


class TestDetectColumns:
    def test_detect_debit_col(self, dormant_df):
        assert _detect_debit_col(dormant_df) == "Debit?"

    def test_detect_debit_col_alt(self):
        df = pd.DataFrame({"DC Indicator": ["Y", "N"]})
        assert _detect_debit_col(df) == "DC Indicator"

    def test_detect_debit_col_none(self):
        df = pd.DataFrame({"Other": [1, 2]})
        assert _detect_debit_col(df) is None

    def test_detect_spend_cols(self, dormant_df):
        cols = _detect_spend_cols(dormant_df)
        assert len(cols) == 6
        assert all(c.endswith(" Spend") for c in cols)


class TestFindDormantAccounts:
    def test_returns_dataframe(self, dormant_df):
        result = _find_dormant_accounts(dormant_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_only_non_debit(self, dormant_df):
        result = _find_dormant_accounts(dormant_df)
        assert not result["Debit?"].isin(["Yes"]).any()

    def test_high_balance_only(self, dormant_df):
        result = _find_dormant_accounts(dormant_df)
        q75 = dormant_df["Avg Bal"].quantile(0.75)
        assert (result["Avg Bal"] >= q75).all()

    def test_none_when_all_debit(self, dormant_df):
        dormant_df["Debit?"] = "Yes"
        assert _find_dormant_accounts(dormant_df) is None

    def test_none_without_debit_col(self, dormant_df):
        df = dormant_df.drop(columns=["Debit?"])
        assert _find_dormant_accounts(df) is None

    def test_none_without_balance_col(self, dormant_df):
        df = dormant_df.drop(columns=["Avg Bal"])
        assert _find_dormant_accounts(df) is None


class TestFindDecliningAccounts:
    def test_returns_dataframe(self, dormant_df):
        result = _find_declining_accounts(dormant_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_has_decline_column(self, dormant_df):
        result = _find_declining_accounts(dormant_df)
        assert "spend_decline" in result.columns

    def test_decline_above_threshold(self, dormant_df):
        result = _find_declining_accounts(dormant_df)
        assert (result["spend_decline"] > 0.20).all()

    def test_none_with_few_spend_cols(self):
        df = pd.DataFrame(
            {
                "Feb24 Spend": [100, 200],
                "Mar24 Spend": [90, 180],
            }
        )
        assert _find_declining_accounts(df) is None

    def test_none_when_all_increasing(self, dormant_df):
        # Make all spend columns increasing
        n = len(dormant_df)
        for col in _detect_spend_cols(dormant_df):
            dormant_df[col] = [500.0 + i * 50 for i in range(n)]
        # With increasing spend, no account should decline >20%
        result = _find_declining_accounts(dormant_df)
        assert result is None or len(result) == 0


class TestDormantOpportunityModule:
    def test_produces_slides(self, dormant_ctx):
        module = DormantOpportunity()
        results = module.run(dormant_ctx)
        successful = [r for r in results if r.success]
        assert len(successful) >= 1

    def test_a20_1_dormant_summary(self, dormant_ctx):
        module = DormantOpportunity()
        results = module.run(dormant_ctx)
        a20_1 = [r for r in results if r.slide_id == "A20.1"]
        assert len(a20_1) == 1
        assert a20_1[0].chart_path.exists()
        assert "$" in a20_1[0].notes

    def test_a20_2_at_risk(self, dormant_ctx):
        module = DormantOpportunity()
        results = module.run(dormant_ctx)
        a20_2 = [r for r in results if r.slide_id == "A20.2"]
        assert len(a20_2) == 1
        assert a20_2[0].chart_path.exists()
        assert "declining" in a20_2[0].notes.lower() or "accounts" in a20_2[0].notes.lower()

    def test_a20_3_priority_matrix(self, dormant_ctx):
        module = DormantOpportunity()
        results = module.run(dormant_ctx)
        a20_3 = [r for r in results if r.slide_id == "A20.3"]
        assert len(a20_3) == 1
        assert a20_3[0].chart_path.exists()

    def test_no_data_returns_failure(self, dormant_ctx):
        dormant_ctx.data = pd.DataFrame()
        module = DormantOpportunity()
        results = module.run(dormant_ctx)
        assert len(results) == 1
        assert not results[0].success

    def test_no_debit_col_partial(self, dormant_ctx):
        dormant_ctx.data = dormant_ctx.data.drop(columns=["Debit?"])
        module = DormantOpportunity()
        results = module.run(dormant_ctx)
        # A20.2 and A20.3 should still work (declining spend doesn't need debit col)
        successful = [r for r in results if r.success]
        assert len(successful) >= 1

    def test_module_metadata(self):
        module = DormantOpportunity()
        assert module.module_id == "insights.dormant"
        assert module.section == "insights"
