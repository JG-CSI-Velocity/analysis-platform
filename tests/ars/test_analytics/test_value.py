"""Tests for the Value analysis module (A11.1 + A11.2)."""


from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.analytics.value.analysis import ValueAnalysis, _find_col

# ---------------------------------------------------------------------------
# Column discovery helper
# ---------------------------------------------------------------------------

class TestFindCol:
    """_find_col() discovers spend/items columns by keyword."""

    def test_finds_exact_match(self, value_df):
        assert _find_col(value_df, "spend") == "L12M Spend"

    def test_finds_items(self, value_df):
        assert _find_col(value_df, "items") == "L12M Items"

    def test_returns_none_missing(self, value_df):
        assert _find_col(value_df, "nonexistent") is None


# ---------------------------------------------------------------------------
# Module attributes
# ---------------------------------------------------------------------------

class TestModuleAttributes:
    """ValueAnalysis has correct class attributes."""

    def test_module_id(self):
        m = ValueAnalysis()
        assert m.module_id == "value.analysis"

    def test_section(self):
        m = ValueAnalysis()
        assert m.section == "value"

    def test_display_name(self):
        assert ValueAnalysis.display_name

    def test_required_columns(self):
        m = ValueAnalysis()
        assert "Debit?" in m.required_columns
        assert "Business?" in m.required_columns


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    """validate() checks prerequisites."""

    def test_passes_with_valid_data(self, value_ctx):
        errors = ValueAnalysis().validate(value_ctx)
        assert errors == []

    def test_fails_without_data(self, value_ctx):
        value_ctx.data = None
        errors = ValueAnalysis().validate(value_ctx)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Full run
# ---------------------------------------------------------------------------

class TestValueAnalysis:
    """ValueAnalysis.run() produces A11.1 and A11.2."""

    def test_run_returns_results(self, value_ctx):
        results = ValueAnalysis().run(value_ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)
        assert len(results) == 2

    def test_slide_ids(self, value_ctx):
        results = ValueAnalysis().run(value_ctx)
        ids = {r.slide_id for r in results}
        assert ids == {"A11.1", "A11.2"}

    def test_all_success(self, value_ctx):
        results = ValueAnalysis().run(value_ctx)
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"

    def test_charts_generated(self, value_ctx):
        results = ValueAnalysis().run(value_ctx)
        for r in results:
            assert r.chart_path is not None, f"{r.slide_id} missing chart"
            assert r.chart_path.exists()

    def test_excel_data(self, value_ctx):
        results = ValueAnalysis().run(value_ctx)
        for r in results:
            assert r.excel_data is not None
            assert "Comparison" in r.excel_data

    def test_stores_value_1(self, value_ctx):
        ValueAnalysis().run(value_ctx)
        v1 = value_ctx.results.get("value_1", {})
        assert "delta" in v1
        assert "accts_with" in v1
        assert "accts_without" in v1
        assert v1["accts_with"] > 0
        assert v1["accts_without"] > 0

    def test_stores_value_2(self, value_ctx):
        ValueAnalysis().run(value_ctx)
        v2 = value_ctx.results.get("value_2", {})
        assert "delta" in v2
        assert "accts_with" in v2
        assert "accts_without" in v2

    def test_delta_calculation(self, value_ctx):
        """Revenue per account should differ between with/without debit."""
        ValueAnalysis().run(value_ctx)
        v1 = value_ctx.results["value_1"]
        assert v1["rev_per_with"] != v1["rev_per_without"]

    def test_potential_values(self, value_ctx):
        """Potential values should be calculated."""
        ValueAnalysis().run(value_ctx)
        v1 = value_ctx.results["value_1"]
        assert "pot_hist" in v1
        assert "pot_l12m" in v1
        assert "pot_100" in v1

    def test_notes_contain_delta(self, value_ctx):
        results = ValueAnalysis().run(value_ctx)
        for r in results:
            assert "revenue per account" in r.notes.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestValueEdgeCases:
    """Edge case handling."""

    def test_no_personal_accounts(self, value_ctx):
        """Should return failure for A11.1 if no personal accounts."""
        value_ctx.subsets.eligible_personal = None
        results = ValueAnalysis().run(value_ctx)
        a11_1 = [r for r in results if r.slide_id == "A11.1"][0]
        assert not a11_1.success

    def test_no_reg_e_column(self, value_ctx):
        """A11.2 should fail gracefully if no Reg E column."""
        value_ctx.client.reg_e_column = ""
        value_ctx.client.reg_e_opt_in = []
        results = ValueAnalysis().run(value_ctx)
        a11_2 = [r for r in results if r.slide_id == "A11.2"][0]
        assert not a11_2.success

    def test_zero_fees(self, value_ctx):
        """With zero fees, revenue is zero but no crash."""
        value_ctx.client.nsf_od_fee = 0.0
        value_ctx.client.ic_rate = 0.0
        results = ValueAnalysis().run(value_ctx)
        assert len(results) == 2
        for r in results:
            assert r.success, f"{r.slide_id} failed: {r.error}"
