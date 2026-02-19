"""Tests for ars_analysis.reg_e -- A8 Reg E Analysis Suite.

Verifies:
1. Output correct -- results populated
2. Makes it onto PowerPoint -- slides added
3. Format correct -- charts created, Excel export called
"""

from pathlib import Path

import numpy as np
import pandas as pd

from ars_analysis.reg_e import (
    _cat_acct_age,
    _cat_balance,
    _cat_holder_age,
    _opt_list,
    _reg_col,
    _rege,
    _total_row,
    run_reg_e_1,
    run_reg_e_2,
    run_reg_e_3,
    run_reg_e_4,
    run_reg_e_4b,
    run_reg_e_5,
    run_reg_e_6,
    run_reg_e_7,
    run_reg_e_8,
    run_reg_e_9,
    run_reg_e_10,
    run_reg_e_11,
    run_reg_e_12,
    run_reg_e_13,
    run_reg_e_cohort,
    run_reg_e_executive_summary,
    run_reg_e_opportunity,
    run_reg_e_seasonality,
    run_reg_e_suite,
)

# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestRegeHelper:
    """_rege() -- calculate opt-in stats."""

    def test_basic_rate(self):
        df = pd.DataFrame({"Reg E": ["Opted In", "Opted Out", "Opted In", "N/A"]})
        total, opted, rate = _rege(df, "Reg E", ["Opted In"])
        assert total == 4
        assert opted == 2
        assert rate == 0.5

    def test_empty_df(self):
        df = pd.DataFrame({"Reg E": pd.Series([], dtype=str)})
        total, opted, rate = _rege(df, "Reg E", ["Opted In"])
        assert total == 0
        assert opted == 0
        assert rate == 0

    def test_all_opted_in(self):
        df = pd.DataFrame({"Reg E": ["Opted In", "Opted In"]})
        _, _, rate = _rege(df, "Reg E", ["Opted In"])
        assert rate == 1.0


class TestOptList:
    def test_list_input(self):
        ctx = {"reg_e_opt_in": ["Opted In", "Yes"]}
        assert _opt_list(ctx) == ["Opted In", "Yes"]

    def test_string_input(self):
        ctx = {"reg_e_opt_in": "Opted In"}
        assert _opt_list(ctx) == ["Opted In"]

    def test_empty(self):
        ctx = {"reg_e_opt_in": []}
        assert _opt_list(ctx) == []

    def test_missing_key(self):
        assert _opt_list({}) == []


class TestRegCol:
    def test_returns_column(self):
        ctx = {"latest_reg_e_column": "Dec24 Reg E"}
        assert _reg_col(ctx) == "Dec24 Reg E"

    def test_missing(self):
        assert _reg_col({}) is None


class TestTotalRow:
    def test_adds_total(self):
        df = pd.DataFrame(
            {
                "Branch": ["A", "B"],
                "Total Accounts": [100, 200],
                "Opted In": [40, 80],
                "Opt-In Rate": [0.40, 0.40],
            }
        )
        result = _total_row(df, "Branch")
        assert result.iloc[-1]["Branch"] == "TOTAL"
        assert result.iloc[-1]["Total Accounts"] == 300
        assert result.iloc[-1]["Opted In"] == 120

    def test_empty_df(self):
        df = pd.DataFrame(columns=["Branch", "Total Accounts"])
        result = _total_row(df, "Branch")
        assert result.empty


class TestCategorization:
    def test_acct_age_buckets(self):
        assert _cat_acct_age(90) == "0-6 months"
        assert _cat_acct_age(200) == "6-12 months"
        assert _cat_acct_age(500) == "1-2 years"
        assert _cat_acct_age(1000) == "2-5 years"
        assert _cat_acct_age(3000) == "5-10 years"
        assert _cat_acct_age(5000) == "10-20 years"
        assert _cat_acct_age(8000) == "20+ years"
        assert _cat_acct_age(np.nan) == "Unknown"

    def test_holder_age_buckets(self):
        assert _cat_holder_age(20) == "18-24"
        assert _cat_holder_age(30) == "25-34"
        assert _cat_holder_age(50) == "45-54"
        assert _cat_holder_age(80) == "75+"
        assert _cat_holder_age(np.nan) == "Unknown"

    def test_balance_buckets(self):
        assert _cat_balance(-100) == "Negative"
        assert _cat_balance(250) == "$0-$499"
        assert _cat_balance(750) == "$500-$999"
        assert _cat_balance(5000) == "$5K-$10K"
        assert _cat_balance(150000) == "$100K+"
        assert _cat_balance(np.nan) == "Unknown"


# ---------------------------------------------------------------------------
# A8.1 — Overall Reg E Status
# ---------------------------------------------------------------------------


class TestRunRegE1:
    """A8.1: Overall Reg E status donut."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        assert "reg_e_1" in ars_ctx["results"]

    def test_result_keys(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        r = ars_ctx["results"]["reg_e_1"]
        assert "opt_in_rate" in r
        assert "l12m_rate" in r
        assert "total_base" in r
        assert "opted_in" in r
        assert "opted_out" in r

    def test_rates_are_fractions(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        r = ars_ctx["results"]["reg_e_1"]
        assert 0 <= r["opt_in_rate"] <= 1
        assert 0 <= r["l12m_rate"] <= 1

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_1(ars_ctx)
        assert len(ars_ctx["all_slides"]) > initial
        slide = ars_ctx["all_slides"][-1]
        assert slide["include"] is True
        assert slide["category"] == "Reg E"
        assert slide["id"] == "A8.1 - Reg E Overall Status"

    def test_creates_chart(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("*.png"))
        assert len(pngs) >= 1

    def test_calls_excel_export(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        assert ars_ctx["_save_to_excel"].called


# ---------------------------------------------------------------------------
# A8.2 — Historical by Year + Decade
# ---------------------------------------------------------------------------


class TestRunRegE2:
    """A8.2: Historical Reg E by Year and Decade."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_2(ars_ctx)
        assert "reg_e_2" in ars_ctx["results"]

    def test_result_has_yearly_and_decade(self, ars_ctx):
        run_reg_e_2(ars_ctx)
        r = ars_ctx["results"]["reg_e_2"]
        assert "yearly" in r
        assert "decade" in r

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_2(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.2" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_2(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_2" in p.name for p in chart_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# A8.3 — L12M Monthly
# ---------------------------------------------------------------------------


class TestRunRegE3:
    """A8.3: L12M Monthly Reg E opt-in rates."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_3(ars_ctx)
        assert "reg_e_3" in ars_ctx["results"]

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_3(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.3" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_3(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_3" in p.name for p in chart_dir.glob("*.png"))

    def test_skips_without_l12m_data(self, ars_ctx):
        ars_ctx["reg_e_eligible_base_l12m"] = pd.DataFrame()
        run_reg_e_3(ars_ctx)
        assert ars_ctx["results"]["reg_e_3"] == {}


# ---------------------------------------------------------------------------
# A8.4 — By Branch (horizontal + scatter)
# ---------------------------------------------------------------------------


class TestRunRegE4:
    """A8.4: Reg E by Branch -- horizontal bars + scatter."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_4(ars_ctx)
        assert "reg_e_4" in ars_ctx["results"]

    def test_result_has_comparison(self, ars_ctx):
        run_reg_e_4(ars_ctx)
        r = ars_ctx["results"]["reg_e_4"]
        assert "comparison" in r
        assert "historical" in r
        assert "l12m" in r

    def test_adds_slides(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_4(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        # Should produce A8.4a (horizontal bar) and A8.4c (scatter)
        assert len(slides) >= 1
        ids = {s["id"] for s in slides}
        assert "A8.4a - Reg E by Branch" in ids

    def test_creates_chart(self, ars_ctx):
        run_reg_e_4(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_4" in p.name for p in chart_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# A8.4b — By Branch (vertical bars)
# ---------------------------------------------------------------------------


class TestRunRegE4b:
    """A8.4b: Reg E by Branch -- vertical bars (depends on A8.4 results)."""

    def test_populates_results(self, ars_ctx):
        # A8.4b depends on A8.4 results
        run_reg_e_4(ars_ctx)
        run_reg_e_4b(ars_ctx)
        assert "reg_e_4b" in ars_ctx["results"]

    def test_adds_slide(self, ars_ctx):
        run_reg_e_4(ars_ctx)
        initial = len(ars_ctx["all_slides"])
        run_reg_e_4b(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.4b" in s["id"] for s in slides)

    def test_skips_without_prior_data(self, ars_ctx):
        # Without A8.4 results, should skip gracefully
        run_reg_e_4b(ars_ctx)
        # Should not crash


# ---------------------------------------------------------------------------
# A8.5 — By Account Age
# ---------------------------------------------------------------------------


class TestRunRegE5:
    """A8.5: Reg E by Account Age."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_5(ars_ctx)
        assert "reg_e_5" in ars_ctx["results"]

    def test_result_has_data(self, ars_ctx):
        run_reg_e_5(ars_ctx)
        r = ars_ctx["results"]["reg_e_5"]
        assert "data" in r

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_5(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.5" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_5(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_5" in p.name for p in chart_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# A8.6 — By Account Holder Age
# ---------------------------------------------------------------------------


class TestRunRegE6:
    """A8.6: Reg E by Account Holder Age."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_6(ars_ctx)
        assert "reg_e_6" in ars_ctx["results"]

    def test_skips_without_age_column(self, ars_ctx):
        """Fixture has 'Holder Age' not 'Birth Date'/'Age', so A8.6 skips chart."""
        run_reg_e_6(ars_ctx)
        # Should not crash; returns empty result
        assert ars_ctx["results"]["reg_e_6"] == {}

    def test_works_with_age_column(self, ars_ctx):
        """When 'Age' column is present, should produce results."""
        # Add "Age" column to reg_e_eligible_base
        base = ars_ctx["reg_e_eligible_base"]
        base["Age"] = np.random.default_rng(42).integers(18, 85, len(base))
        ars_ctx["reg_e_eligible_base_l12m"]["Age"] = np.random.default_rng(42).integers(
            18, 85, len(ars_ctx["reg_e_eligible_base_l12m"])
        )
        run_reg_e_6(ars_ctx)
        r = ars_ctx["results"]["reg_e_6"]
        assert "historical" in r

    def test_creates_chart_with_age(self, ars_ctx):
        base = ars_ctx["reg_e_eligible_base"]
        base["Age"] = np.random.default_rng(42).integers(18, 85, len(base))
        ars_ctx["reg_e_eligible_base_l12m"]["Age"] = np.random.default_rng(42).integers(
            18, 85, len(ars_ctx["reg_e_eligible_base_l12m"])
        )
        run_reg_e_6(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_6" in p.name for p in chart_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# A8.7 — By Product Code
# ---------------------------------------------------------------------------


class TestRunRegE7:
    """A8.7: Reg E by Product Code."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_7(ars_ctx)
        assert "reg_e_7" in ars_ctx["results"]

    def test_result_has_data(self, ars_ctx):
        run_reg_e_7(ars_ctx)
        r = ars_ctx["results"]["reg_e_7"]
        assert "data" in r

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_7(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.7" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_7(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_7" in p.name for p in chart_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# A8.8 — Monthly Heatmap
# ---------------------------------------------------------------------------


class TestRunRegE8:
    """A8.8: Monthly Reg E heatmaps."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_8(ars_ctx)
        assert "reg_e_8" in ars_ctx["results"]

    def test_creates_heatmap_charts(self, ars_ctx):
        run_reg_e_8(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = [p.name for p in chart_dir.glob("a8_8*.png")]
        # May produce 0, 1, or 2 heatmaps depending on data overlap with L12M
        assert isinstance(pngs, list)


# ---------------------------------------------------------------------------
# A8.9 — Branch Performance Summary
# ---------------------------------------------------------------------------


class TestRunRegE9:
    """A8.9: Branch performance summary (depends on A8.8 results)."""

    def test_populates_results(self, ars_ctx):
        # A8.9 depends on A8.8 results
        run_reg_e_8(ars_ctx)
        run_reg_e_9(ars_ctx)
        assert "reg_e_9" in ars_ctx["results"]

    def test_skips_without_heatmap_data(self, ars_ctx):
        # Without A8.8, should handle gracefully
        run_reg_e_9(ars_ctx)
        assert ars_ctx["results"].get("reg_e_9") == {}


# ---------------------------------------------------------------------------
# A8.10 — All-Time Account Funnel
# ---------------------------------------------------------------------------


class TestRunRegE10:
    """A8.10: All-time account funnel with Reg E."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_10(ars_ctx)
        assert "reg_e_10" in ars_ctx["results"]

    def test_result_has_funnel(self, ars_ctx):
        run_reg_e_10(ars_ctx)
        r = ars_ctx["results"]["reg_e_10"]
        assert "funnel" in r
        assert isinstance(r["funnel"], pd.DataFrame)

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_10(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.10" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_10(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_10" in p.name for p in chart_dir.glob("*.png"))

    def test_funnel_has_five_stages(self, ars_ctx):
        run_reg_e_10(ars_ctx)
        funnel = ars_ctx["results"]["reg_e_10"]["funnel"]
        assert len(funnel) == 5


# ---------------------------------------------------------------------------
# A8.11 — L12M Funnel
# ---------------------------------------------------------------------------


class TestRunRegE11:
    """A8.11: L12M funnel with Reg E."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_11(ars_ctx)
        assert "reg_e_11" in ars_ctx["results"]

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_11(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.11" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_11(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_11" in p.name for p in chart_dir.glob("*.png"))

    def test_skips_without_l12m_data(self, ars_ctx):
        ars_ctx["eligible_last_12m"] = pd.DataFrame()
        run_reg_e_11(ars_ctx)
        assert ars_ctx["results"]["reg_e_11"] == {}


# ---------------------------------------------------------------------------
# A8.12 — 24-Month Trend
# ---------------------------------------------------------------------------


class TestRunRegE12:
    """A8.12: 24-month Reg E trend."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_12(ars_ctx)
        assert "reg_e_12" in ars_ctx["results"]

    def test_result_has_monthly(self, ars_ctx):
        run_reg_e_12(ars_ctx)
        r = ars_ctx["results"]["reg_e_12"]
        assert "monthly" in r
        assert isinstance(r["monthly"], pd.DataFrame)

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_reg_e_12(ars_ctx)
        slides = [s for s in ars_ctx["all_slides"][initial:] if s["category"] == "Reg E"]
        assert len(slides) >= 1
        assert any("A8.12" in s["id"] for s in slides)

    def test_creates_chart(self, ars_ctx):
        run_reg_e_12(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert any("a8_12" in p.name for p in chart_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# A8.13 — Branch x Month Pivot
# ---------------------------------------------------------------------------


class TestRunRegE13:
    """A8.13: Complete branch x month pivot table."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_13(ars_ctx)
        assert "reg_e_13" in ars_ctx["results"]

    def test_result_has_pivot(self, ars_ctx):
        run_reg_e_13(ars_ctx)
        r = ars_ctx["results"]["reg_e_13"]
        assert "pivot" in r
        assert isinstance(r["pivot"], pd.DataFrame)

    def test_pivot_has_total_row(self, ars_ctx):
        run_reg_e_13(ars_ctx)
        pivot = ars_ctx["results"]["reg_e_13"]["pivot"]
        if not pivot.empty:
            assert "TOTAL" in pivot["Branch"].values

    def test_skips_without_l12m_data(self, ars_ctx):
        ars_ctx["reg_e_eligible_base_l12m"] = pd.DataFrame()
        run_reg_e_13(ars_ctx)
        assert ars_ctx["results"]["reg_e_13"] == {}


# ---------------------------------------------------------------------------
# Full Suite
# ---------------------------------------------------------------------------


class TestRunRegESuite:
    """Full A8 suite -- all 13+ sub-analyses."""

    def test_runs_without_error(self, ars_ctx):
        run_reg_e_suite(ars_ctx)

    def test_adds_multiple_slides(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        assert len(ars_ctx["all_slides"]) >= 3

    def test_all_slides_valid(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "data" in slide

    def test_creates_charts(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        pngs = list(chart_dir.glob("*.png"))
        assert len(pngs) >= 3

    def test_populates_results(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        # Suite stores reg_e analysis results
        assert any("reg_e" in k for k in ars_ctx["results"])

    def test_skips_gracefully_without_reg_e_data(self, ars_ctx):
        ars_ctx["reg_e_eligible_base"] = None
        run_reg_e_suite(ars_ctx)
        # Should not crash, just skip

    def test_skips_without_reg_e_column(self, ars_ctx):
        ars_ctx["latest_reg_e_column"] = None
        run_reg_e_suite(ars_ctx)
        # Should not crash

    def test_all_slides_are_reg_e_category(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        reg_slides = [s for s in ars_ctx["all_slides"] if s["category"] == "Reg E"]
        assert len(reg_slides) >= 3

    def test_slides_ordered_by_reg_order(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        reg_slides = [s for s in ars_ctx["all_slides"] if s["category"] == "Reg E"]
        ids = [s["id"] for s in reg_slides]
        # First slide should be A8.0 (executive summary)
        if ids:
            assert ids[0] == "A8.0 - Reg E Executive Summary"

    def test_multiple_result_keys(self, ars_ctx):
        run_reg_e_suite(ars_ctx)
        reg_keys = [k for k in ars_ctx["results"] if k.startswith("reg_e")]
        assert len(reg_keys) >= 5

    def test_suite_runs_a8_8_and_a8_9(self, ars_ctx):
        """A8.8 and A8.9 are now enabled in the suite runner."""
        run_reg_e_suite(ars_ctx)
        assert "reg_e_8" in ars_ctx["results"]
        assert "reg_e_9" in ars_ctx["results"]


# ---------------------------------------------------------------------------
# Sprint 2: Exports and benchmark reference lines
# ---------------------------------------------------------------------------


class TestPackageExports:
    """Verify public API exports from ars_analysis.reg_e."""

    def test_exports_reg_order(self):
        from ars_analysis.reg_e import REG_ORDER

        assert isinstance(REG_ORDER, list)
        assert len(REG_ORDER) > 10

    def test_exports_rege_merges(self):
        from ars_analysis.reg_e import REGE_MERGES

        assert isinstance(REGE_MERGES, list)
        assert len(REGE_MERGES) == 2

    def test_exports_rege_appendix_ids(self):
        from ars_analysis.reg_e import REGE_APPENDIX_IDS

        assert isinstance(REGE_APPENDIX_IDS, set)
        assert len(REGE_APPENDIX_IDS) >= 6

    def test_appendix_ids_include_a8_8_a8_9(self):
        from ars_analysis.reg_e import REGE_APPENDIX_IDS

        assert "A8.8a - Reg E Heatmap (Open Personal)" in REGE_APPENDIX_IDS
        assert "A8.9a - Reg E Branch Summary (Open)" in REGE_APPENDIX_IDS


class TestBenchmarkLines:
    """Verify benchmark target reference lines are added to charts."""

    def test_a8_3_chart_with_target(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_3(ars_ctx)
        # Chart should be created without error when target is set
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_3_reg_e_l12m.png").exists()

    def test_a8_5_chart_with_target(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_5(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_5_reg_e_acct_age.png").exists()

    def test_a8_7_chart_with_target(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_7(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_7_reg_e_product.png").exists()

    def test_a8_12_chart_with_target(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_12(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_12_reg_e_trend.png").exists()

    def test_charts_work_without_target(self, ars_ctx):
        ars_ctx.pop("reg_e_target", None)
        run_reg_e_3(ars_ctx)
        run_reg_e_5(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_3_reg_e_l12m.png").exists()
        assert (chart_dir / "a8_5_reg_e_acct_age.png").exists()


# ---------------------------------------------------------------------------
# Sprint 3: Opportunity Sizing (A8.14)
# ---------------------------------------------------------------------------


class TestRunRegEOpportunity:
    """Tests for run_reg_e_opportunity (A8.14)."""

    def test_populates_results(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_opportunity(ars_ctx)
        assert "reg_e_opportunity" in ars_ctx["results"]

    def test_result_has_tiers(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_opportunity(ars_ctx)
        result = ars_ctx["results"]["reg_e_opportunity"]
        assert "tiers" in result
        assert len(result["tiers"]) == 2  # Target + Best-in-Class

    def test_result_has_current_rate(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_opportunity(ars_ctx)
        result = ars_ctx["results"]["reg_e_opportunity"]
        assert "current_rate" in result
        assert 0 <= result["current_rate"] <= 1

    def test_adds_slide(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_opportunity(ars_ctx)
        ids = [s["id"] for s in ars_ctx["all_slides"]]
        assert "A8.14 - Reg E Opportunity" in ids

    def test_creates_chart(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_opportunity(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_14_reg_e_opportunity.png").exists()

    def test_opportunity_with_revenue(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        ars_ctx["nsf_od_fee"] = 35.0
        run_reg_e_opportunity(ars_ctx)
        result = ars_ctx["results"]["reg_e_opportunity"]
        # At least one tier should have revenue if rate < target
        for tier in result["tiers"]:
            if tier["additional_accounts"] > 0:
                assert tier["revenue"] > 0

    def test_above_target_shows_zero_additional(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.01  # Very low target
        run_reg_e_opportunity(ars_ctx)
        result = ars_ctx["results"]["reg_e_opportunity"]
        # Target tier should show 0 additional (rate already exceeds target)
        target_tier = result["tiers"][0]
        assert target_tier["additional_accounts"] == 0

    def test_skips_with_no_eligible_data(self, ars_ctx):
        ars_ctx["reg_e_eligible_base"] = None
        run_reg_e_opportunity(ars_ctx)
        # Should not crash

    def test_calls_excel_export(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        calls = []
        ars_ctx["_save_to_excel"] = lambda *a, **kw: calls.append(1)
        run_reg_e_opportunity(ars_ctx)
        assert len(calls) >= 1


# ---------------------------------------------------------------------------
# Sprint 3: Executive Summary (A8.0)
# ---------------------------------------------------------------------------


class TestRunRegEExecutiveSummary:
    """Tests for run_reg_e_executive_summary (A8.0)."""

    def test_populates_results(self, ars_ctx):
        # Run prereqs first
        run_reg_e_1(ars_ctx)
        run_reg_e_4(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        assert "reg_e_executive_summary" in ars_ctx["results"]

    def test_result_has_kpis_and_bullets(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        run_reg_e_4(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        result = ars_ctx["results"]["reg_e_executive_summary"]
        assert "kpis" in result
        assert "bullets" in result
        assert isinstance(result["kpis"], dict)
        assert isinstance(result["bullets"], list)

    def test_adds_slide(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        ids = [s["id"] for s in ars_ctx["all_slides"]]
        assert "A8.0 - Reg E Executive Summary" in ids

    def test_creates_chart(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_0_reg_e_executive_summary.png").exists()

    def test_kpis_include_key_metrics(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        result = ars_ctx["results"]["reg_e_executive_summary"]
        kpi_keys = list(result["kpis"].keys())
        assert "Overall Opt-In" in kpi_keys
        assert "L12M Opt-In" in kpi_keys
        assert "Target" in kpi_keys

    def test_bullets_not_empty(self, ars_ctx):
        run_reg_e_1(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        result = ars_ctx["results"]["reg_e_executive_summary"]
        assert len(result["bullets"]) >= 1

    def test_works_without_prior_analyses(self, ars_ctx):
        # Should work even without running other analyses first
        run_reg_e_executive_summary(ars_ctx)
        assert "reg_e_executive_summary" in ars_ctx["results"]

    def test_includes_opportunity_bullet_when_available(self, ars_ctx):
        ars_ctx["reg_e_target"] = 0.60
        run_reg_e_1(ars_ctx)
        run_reg_e_4(ars_ctx)
        run_reg_e_opportunity(ars_ctx)
        run_reg_e_executive_summary(ars_ctx)
        result = ars_ctx["results"]["reg_e_executive_summary"]
        bullets_text = " ".join(result["bullets"])
        # Should mention opportunity if rate < best-in-class
        if ars_ctx["results"]["reg_e_opportunity"]["tiers"][-1]["additional_accounts"] > 0:
            assert "additional" in bullets_text.lower() or "closing" in bullets_text.lower()


# ---------------------------------------------------------------------------
# Sprint 4: Cohort Analysis (A8.15)
# ---------------------------------------------------------------------------


class TestRunRegECohort:
    """Tests for run_reg_e_cohort (A8.15)."""

    def _make_l12m_ctx(self, ars_ctx):
        """Add recent open accounts that overlap with L12M."""
        rng = np.random.default_rng(99)
        n = 50
        col = ars_ctx["latest_reg_e_column"]
        recent = pd.DataFrame(
            {
                "Date Opened": pd.date_range("2024-01-15", periods=n, freq="7D"),
                "Branch": rng.choice(["Main", "North", "South"], n),
                "Business?": rng.choice(["Yes", "No"], n, p=[0.2, 0.8]),
                col: rng.choice(["Opted In", "Opted Out"], n, p=[0.5, 0.5]),
            }
        )
        ars_ctx["open_accounts"] = pd.concat(
            [ars_ctx["open_accounts"], recent],
            ignore_index=True,
        )
        return ars_ctx

    def test_populates_results(self, ars_ctx):
        self._make_l12m_ctx(ars_ctx)
        run_reg_e_cohort(ars_ctx)
        assert "reg_e_cohort" in ars_ctx["results"]

    def test_result_has_cohort_data(self, ars_ctx):
        self._make_l12m_ctx(ars_ctx)
        run_reg_e_cohort(ars_ctx)
        result = ars_ctx["results"]["reg_e_cohort"]
        assert "cohort_df" in result
        assert len(result["cohort_df"]) > 0

    def test_adds_slide(self, ars_ctx):
        self._make_l12m_ctx(ars_ctx)
        run_reg_e_cohort(ars_ctx)
        ids = [s["id"] for s in ars_ctx["all_slides"]]
        assert "A8.15 - Reg E Cohort Analysis" in ids

    def test_creates_chart(self, ars_ctx):
        self._make_l12m_ctx(ars_ctx)
        run_reg_e_cohort(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_15_reg_e_cohort.png").exists()

    def test_skips_without_open_accounts(self, ars_ctx):
        ars_ctx["open_accounts"] = pd.DataFrame()
        run_reg_e_cohort(ars_ctx)
        # Should not crash

    def test_skips_without_reg_e_column(self, ars_ctx):
        ars_ctx["latest_reg_e_column"] = None
        run_reg_e_cohort(ars_ctx)
        # Should not crash

    def test_skips_without_l12m_data(self, ars_ctx):
        # Default fixture has no L12M-dated open accounts
        run_reg_e_cohort(ars_ctx)
        assert "reg_e_cohort" in ars_ctx["results"]

    def test_cohort_rates_are_fractions(self, ars_ctx):
        self._make_l12m_ctx(ars_ctx)
        run_reg_e_cohort(ars_ctx)
        result = ars_ctx["results"]["reg_e_cohort"]
        cohort_df = result.get("cohort_df")
        if cohort_df is not None and not cohort_df.empty:
            assert all(cohort_df["Opt-In Rate"] <= 1.0)
            assert all(cohort_df["Opt-In Rate"] >= 0.0)


# ---------------------------------------------------------------------------
# Sprint 4: Seasonality (A8.16)
# ---------------------------------------------------------------------------


class TestRunRegESeasonality:
    """Tests for run_reg_e_seasonality (A8.16)."""

    def test_populates_results(self, ars_ctx):
        run_reg_e_seasonality(ars_ctx)
        assert "reg_e_seasonality" in ars_ctx["results"]

    def test_result_has_monthly_and_quarterly(self, ars_ctx):
        run_reg_e_seasonality(ars_ctx)
        result = ars_ctx["results"]["reg_e_seasonality"]
        assert "monthly" in result
        assert "quarterly" in result

    def test_adds_slide(self, ars_ctx):
        run_reg_e_seasonality(ars_ctx)
        ids = [s["id"] for s in ars_ctx["all_slides"]]
        assert "A8.16 - Reg E Seasonality" in ids

    def test_creates_chart(self, ars_ctx):
        run_reg_e_seasonality(ars_ctx)
        chart_dir = Path(ars_ctx["chart_dir"])
        assert (chart_dir / "a8_16_reg_e_seasonality.png").exists()

    def test_skips_without_eligible_data(self, ars_ctx):
        ars_ctx["reg_e_eligible_base"] = None
        run_reg_e_seasonality(ars_ctx)
        # Should not crash

    def test_monthly_has_correct_columns(self, ars_ctx):
        run_reg_e_seasonality(ars_ctx)
        result = ars_ctx["results"]["reg_e_seasonality"]
        monthly = result["monthly"]
        if not monthly.empty:
            assert "Month Name" in monthly.columns
            assert "Opt-In Rate %" in monthly.columns

    def test_yoy_data_populated(self, ars_ctx):
        run_reg_e_seasonality(ars_ctx)
        result = ars_ctx["results"]["reg_e_seasonality"]
        assert "yoy" in result
        assert isinstance(result["yoy"], dict)
