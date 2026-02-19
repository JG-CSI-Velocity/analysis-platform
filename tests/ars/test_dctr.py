"""Tests for ars_analysis.dctr -- A6/A7 DCTR Analysis Suite.

Unit tests for pure utility functions + smoke tests for run_dctr_* analysis
functions verifying the 3 acceptance criteria:
1. Output correct -- results dict populated
2. Slide appended -- ctx["all_slides"] grows with correct category
3. Chart/Excel created -- chart PNG exists or _save_to_excel called
"""

from pathlib import Path

import pandas as pd
import pytest

from ars_analysis.dctr import (
    AGE_ORDER,
    BALANCE_ORDER,
    HOLDER_AGE_ORDER,
    _dctr,
    analyze_historical_dctr,
    categorize_account_age,
    categorize_balance,
    categorize_holder_age,
    map_to_decade,
    run_dctr_1,
    run_dctr_2,
    run_dctr_3,
    run_dctr_4_5,
    run_dctr_6_7,
    run_dctr_8,
    run_dctr_9,
    run_dctr_10,
    run_dctr_11,
    run_dctr_12,
    run_dctr_13,
    run_dctr_14,
    run_dctr_15,
    run_dctr_16,
    run_dctr_funnel,
    run_dctr_combo_slide,
    run_dctr_segment_trends,
    run_dctr_decade_trend,
    run_dctr_l12m_trend,
    run_dctr_l12m_funnel,
    run_dctr_branch_trend,
    run_dctr_heatmap,
    run_dctr_seasonality,
    run_dctr_vintage,
    run_dctr_decade_pb,
    run_dctr_eligible_vs_non,
    run_dctr_branch_l12m,
    run_dctr_suite,
)


# ---------------------------------------------------------------------------
# Pure utility function tests (no ctx required)
# ---------------------------------------------------------------------------


class TestDctr:
    def test_basic_rate(self):
        df = pd.DataFrame({"Debit?": ["Yes", "Yes", "No", "No"]})
        total, with_debit, rate = _dctr(df)
        assert total == 4
        assert with_debit == 2
        assert rate == pytest.approx(0.5)  # returns fraction, not percentage

    def test_all_debit(self):
        df = pd.DataFrame({"Debit?": ["Yes", "Yes", "Yes"]})
        total, with_debit, rate = _dctr(df)
        assert rate == pytest.approx(1.0)

    def test_empty_df(self):
        df = pd.DataFrame({"Debit?": []})
        total, with_debit, rate = _dctr(df)
        assert total == 0
        assert rate == 0


class TestCategorizeAccountAge:
    def test_new_account(self):
        assert categorize_account_age(90) in AGE_ORDER

    def test_old_account(self):
        result = categorize_account_age(5000)
        assert result in AGE_ORDER

    def test_zero_days(self):
        result = categorize_account_age(0)
        assert result in AGE_ORDER


class TestCategorizeHolderAge:
    def test_young(self):
        assert categorize_holder_age(20) in HOLDER_AGE_ORDER

    def test_middle(self):
        assert categorize_holder_age(40) in HOLDER_AGE_ORDER

    def test_senior(self):
        assert categorize_holder_age(70) in HOLDER_AGE_ORDER


class TestCategorizeBalance:
    def test_negative(self):
        result = categorize_balance(-100)
        assert result in BALANCE_ORDER

    def test_zero(self):
        result = categorize_balance(0)
        assert result in BALANCE_ORDER

    def test_high_balance(self):
        result = categorize_balance(200000)
        assert result in BALANCE_ORDER


class TestMapToDecade:
    def test_2020s(self):
        # Recent years get individual year strings, not decade
        assert map_to_decade(2023) == "2023"

    def test_1990s(self):
        assert map_to_decade(1995) == "1990s"

    def test_old(self):
        result = map_to_decade(1960)
        assert "Before" in result or "1960" in result


class TestAnalyzeHistoricalDctr:
    def test_basic_analysis(self):
        df = pd.DataFrame(
            {
                "Debit?": ["Yes", "No", "Yes", "No"],
                "Business?": ["No", "No", "Yes", "No"],
                "Date Opened": pd.to_datetime(
                    ["2020-01-01", "2020-06-01", "2019-03-15", "2018-12-01"]
                ),
            }
        )
        yearly, decade, metrics = analyze_historical_dctr(df)
        assert "overall_dctr" in metrics
        # overall_dctr is a fraction (0-1) not percentage
        assert metrics["overall_dctr"] == pytest.approx(0.5)
        assert not yearly.empty


# ---------------------------------------------------------------------------
# Fixture: ctx with dctr_1 pre-run (many functions depend on it)
# ---------------------------------------------------------------------------


@pytest.fixture
def dctr_ctx(ars_ctx):
    """ARS context with run_dctr_1 already executed (satisfies dependencies)."""
    run_dctr_1(ars_ctx)
    return ars_ctx


# ---------------------------------------------------------------------------
# Smoke tests for run_dctr_* analysis functions
# ---------------------------------------------------------------------------


class TestRunDctr1:
    """DCTR-1: Historical DCTR (Eligible) -- data only, no chart."""

    def test_populates_results(self, ars_ctx):
        run_dctr_1(ars_ctx)
        assert "dctr_1" in ars_ctx["results"]
        ins = ars_ctx["results"]["dctr_1"]["insights"]
        assert "overall_dctr" in ins
        assert 0 <= ins["overall_dctr"] <= 1

    def test_calls_excel_export(self, ars_ctx):
        run_dctr_1(ars_ctx)
        assert ars_ctx["_save_to_excel"].called


class TestRunDctr2:
    """DCTR-2: Open vs Eligible + Chart (no slide -- combo_slide handles that)."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_2(dctr_ctx)
        assert "dctr_2" in dctr_ctx["results"]

    def test_creates_chart(self, dctr_ctx):
        run_dctr_2(dctr_ctx)
        pngs = list(Path(dctr_ctx["chart_dir"]).glob("dctr_*.png"))
        assert len(pngs) >= 1


class TestRunDctr3:
    """DCTR-3: Last 12 months + Chart (no slide -- combo_slide handles that)."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_3(dctr_ctx)
        assert "dctr_3" in dctr_ctx["results"]


class TestRunDctr4_5:
    """DCTR-4/5: Personal & Business historical."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_4_5(dctr_ctx)
        assert "dctr_4" in dctr_ctx["results"]
        assert "dctr_5" in dctr_ctx["results"]


class TestRunDctr6_7:
    """DCTR-6/7: Personal & Business L12M monthly."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_6_7(dctr_ctx)
        assert "dctr_6" in dctr_ctx["results"]
        assert "dctr_7" in dctr_ctx["results"]


class TestRunDctr8:
    """DCTR-8: Comprehensive summary table."""

    def test_populates_results(self, dctr_ctx):
        # dctr_8 reads from dctr_1 through dctr_7
        run_dctr_3(dctr_ctx)
        run_dctr_4_5(dctr_ctx)
        run_dctr_6_7(dctr_ctx)
        run_dctr_8(dctr_ctx)
        assert "dctr_8" in dctr_ctx["results"]


class TestRunDctr9:
    """DCTR-9: Branch DCTR analysis."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_9(dctr_ctx)
        assert "dctr_9" in dctr_ctx["results"]


class TestRunDctr10:
    """DCTR-10: Account age breakdown + Chart."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_10(dctr_ctx)
        assert "dctr_10" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_10(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial

    def test_creates_chart(self, dctr_ctx):
        run_dctr_10(dctr_ctx)
        pngs = list(Path(dctr_ctx["chart_dir"]).glob("dctr_account_age*.png"))
        assert len(pngs) >= 1


class TestRunDctr11:
    """DCTR-11: Account holder age + Chart."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_11(dctr_ctx)
        assert "dctr_11" in dctr_ctx["results"]

    def test_with_correct_column_name(self, dctr_ctx):
        """When column name matches, function produces full results."""
        dctr_ctx["eligible_data"] = dctr_ctx["eligible_data"].rename(
            columns={"Holder Age": "Account Holder Age"}
        )
        run_dctr_11(dctr_ctx)
        assert dctr_ctx["results"]["dctr_11"]  # non-empty dict

    def test_adds_slide_with_data(self, dctr_ctx):
        dctr_ctx["eligible_data"] = dctr_ctx["eligible_data"].rename(
            columns={"Holder Age": "Account Holder Age"}
        )
        initial = len(dctr_ctx["all_slides"])
        run_dctr_11(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctr12:
    """DCTR-12: Balance range breakdown."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_12(dctr_ctx)
        assert "dctr_12" in dctr_ctx["results"]


class TestRunDctr13:
    """DCTR-13: Cross-tab holder age x balance."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_13(dctr_ctx)
        assert "dctr_13" in dctr_ctx["results"]


class TestRunDctr14:
    """DCTR-14: Cross-tab account age x balance."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_14(dctr_ctx)
        assert "dctr_14" in dctr_ctx["results"]

    def test_adds_heatmap_slide(self, dctr_ctx):
        before = len(dctr_ctx["all_slides"])
        run_dctr_14(dctr_ctx)
        heatmap_slides = [
            s for s in dctr_ctx["all_slides"] if "A7.23" in s["id"]
        ]
        assert len(heatmap_slides) >= 1

    def test_creates_heatmap_chart(self, dctr_ctx):
        run_dctr_14(dctr_ctx)
        chart_path = Path(dctr_ctx["chart_dir"]) / "dctr_14_acctage_balance_heatmap.png"
        assert chart_path.exists()


class TestRunDctr15:
    """DCTR-15: Cross-tab branch x account age."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_15(dctr_ctx)
        assert "dctr_15" in dctr_ctx["results"]

    def test_adds_heatmap_slide(self, dctr_ctx):
        run_dctr_15(dctr_ctx)
        heatmap_slides = [
            s for s in dctr_ctx["all_slides"] if "A7.24" in s["id"]
        ]
        assert len(heatmap_slides) >= 1

    def test_creates_heatmap_chart(self, dctr_ctx):
        run_dctr_15(dctr_ctx)
        chart_path = Path(dctr_ctx["chart_dir"]) / "dctr_15_branch_age_heatmap.png"
        assert chart_path.exists()


class TestRunDctr16:
    """DCTR-16: Branch L12M monthly performance table."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_16(dctr_ctx)
        assert "dctr_16" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_16(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrFunnel:
    """DCTR Funnel: Historical account & debit card funnel."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_funnel(dctr_ctx)
        assert "dctr_funnel" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_funnel(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial

    def test_creates_chart(self, dctr_ctx):
        run_dctr_funnel(dctr_ctx)
        pngs = list(Path(dctr_ctx["chart_dir"]).glob("dctr_funnel*.png"))
        assert len(pngs) >= 1


class TestRunDctrSegmentTrends:
    """Segment Trends: P/B x Historical/L12M grouped bar."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_segment_trends(dctr_ctx)
        assert "dctr_segment_trends" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_segment_trends(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrDecadeTrend:
    """Decade Trend: Decade trend line chart."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_decade_trend(dctr_ctx)
        assert "dctr_decade_trend" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_decade_trend(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial

    def test_creates_chart(self, dctr_ctx):
        run_dctr_decade_trend(dctr_ctx)
        pngs = list(Path(dctr_ctx["chart_dir"]).glob("dctr_decade_trend*.png"))
        assert len(pngs) >= 1


class TestRunDctrL12mTrend:
    """L12M Trend: Monthly DCTR trend line chart."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_l12m_trend(dctr_ctx)
        assert "dctr_l12m_trend" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_l12m_trend(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial

    def test_creates_chart(self, dctr_ctx):
        run_dctr_l12m_trend(dctr_ctx)
        pngs = list(Path(dctr_ctx["chart_dir"]).glob("dctr_l12m_trend*.png"))
        assert len(pngs) >= 1


class TestRunDctrL12mFunnel:
    """L12M Funnel: L12M funnel with P/B split."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_l12m_funnel(dctr_ctx)
        assert "dctr_l12m_funnel" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_l12m_funnel(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrBranchTrend:
    """Branch Trend: Branch historical vs L12M change tracking."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_branch_trend(dctr_ctx)
        assert "dctr_branch_trend" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_branch_trend(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrHeatmap:
    """Heatmap: Monthly DCTR heatmap by branch."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_heatmap(dctr_ctx)
        assert "dctr_heatmap" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_heatmap(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrSeasonality:
    """Seasonality: Monthly DCTR seasonality patterns."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_seasonality(dctr_ctx)
        assert "dctr_seasonality" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_seasonality(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrVintage:
    """Vintage: Vintage & cohort analysis."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_vintage(dctr_ctx)
        assert "dctr_vintage" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_vintage(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrDecadePb:
    """Decade P/B: Personal vs Business by Decade (requires dctr_4/5)."""

    def test_skips_gracefully_without_deps(self, dctr_ctx):
        """Returns early when dctr_4 results not available."""
        run_dctr_decade_pb(dctr_ctx)
        assert "dctr_decade_pb" not in dctr_ctx["results"]

    def test_populates_results_with_deps(self, dctr_ctx):
        run_dctr_4_5(dctr_ctx)
        run_dctr_decade_pb(dctr_ctx)
        assert "dctr_decade_pb" in dctr_ctx["results"]

    def test_adds_slide_with_deps(self, dctr_ctx):
        run_dctr_4_5(dctr_ctx)
        initial = len(dctr_ctx["all_slides"])
        run_dctr_decade_pb(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrEligibleVsNon:
    """Eligible vs Non: Eligible vs non-eligible DCTR comparison."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_eligible_vs_non(dctr_ctx)
        assert "dctr_elig_vs_non" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_eligible_vs_non(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrBranchL12m:
    """Branch L12M: Branch L12M detail table."""

    def test_populates_results(self, dctr_ctx):
        run_dctr_branch_l12m(dctr_ctx)
        assert "dctr_branch_l12m" in dctr_ctx["results"]

    def test_adds_slide(self, dctr_ctx):
        initial = len(dctr_ctx["all_slides"])
        run_dctr_branch_l12m(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


class TestRunDctrComboSlide:
    """Combo Slide: Combined DCTR overview slide (requires dctr_1+2+3)."""

    def test_skips_without_deps(self, dctr_ctx):
        """Returns early when dctr_2 results not available."""
        initial = len(dctr_ctx["all_slides"])
        run_dctr_combo_slide(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) == initial

    def test_adds_slide_with_deps(self, dctr_ctx):
        run_dctr_2(dctr_ctx)
        run_dctr_3(dctr_ctx)
        initial = len(dctr_ctx["all_slides"])
        run_dctr_combo_slide(dctr_ctx)
        assert len(dctr_ctx["all_slides"]) > initial


# ---------------------------------------------------------------------------
# Full suite integration test
# ---------------------------------------------------------------------------


class TestRunDctrSuite:
    """Full DCTR suite: all analyses run in sequence."""

    def test_suite_produces_slides(self, ars_ctx):
        run_dctr_suite(ars_ctx)
        dctr_slides = [s for s in ars_ctx["all_slides"] if s["category"] == "DCTR"]
        # Suite should produce at least 10 DCTR slides
        assert len(dctr_slides) >= 10

    def test_suite_populates_results(self, ars_ctx):
        run_dctr_suite(ars_ctx)
        # Key result keys should be present
        assert "dctr_1" in ars_ctx["results"]
        assert "dctr_decade_trend" in ars_ctx["results"]
        assert "dctr_l12m_trend" in ars_ctx["results"]

    def test_suite_creates_charts(self, ars_ctx):
        run_dctr_suite(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("dctr_*.png"))
        # Suite should produce multiple chart files
        assert len(pngs) >= 5
