"""Tests for cumulative reach analysis (A17 series)."""

from __future__ import annotations

from ars_analysis.analytics.mailer._helpers import discover_pairs
from ars_analysis.analytics.mailer.reach import (
    CumulativeReach,
    _cumulative_reach,
    _organic_activation,
)

# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestCumulativeReach:
    def test_builds_per_month_data(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _cumulative_reach(cohort_mailer_ctx.data, pairs)
        assert len(result) == 2  # Apr24, May24
        assert result[0]["cum_mailed"] > 0
        assert result[1]["cum_mailed"] >= result[0]["cum_mailed"]

    def test_cumulative_grows_monotonically(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _cumulative_reach(cohort_mailer_ctx.data, pairs)
        for i in range(1, len(result)):
            assert result[i]["cum_mailed"] >= result[i - 1]["cum_mailed"]
            assert result[i]["cum_responded"] >= result[i - 1]["cum_responded"]

    def test_new_mailed_is_incremental(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _cumulative_reach(cohort_mailer_ctx.data, pairs)
        # Second month should have fewer "new" since many were already mailed
        if len(result) >= 2:
            assert result[1]["new_mailed"] <= result[0]["new_mailed"]

    def test_responded_subset_of_mailed(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _cumulative_reach(cohort_mailer_ctx.data, pairs)
        for r in result:
            assert r["cum_responded"] <= r["cum_mailed"]


class TestOrganicActivation:
    def test_identifies_organic(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _organic_activation(cohort_mailer_ctx.data, pairs)
        # Some accounts have Debit?=Yes but were never mailed (rows 40-59 in fixture)
        assert result["organic"] > 0
        assert result["total_debit"] > 0

    def test_categories_sum_to_total(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _organic_activation(cohort_mailer_ctx.data, pairs)
        assert (
            result["organic"] + result["mailed_resp"] + result["mailed_non_resp"]
            == result["total_debit"]
        )

    def test_no_debit_column_returns_zeros(self, cohort_mailer_ctx):
        cohort_mailer_ctx.data = cohort_mailer_ctx.data.drop(columns=["Debit?"])
        pairs = discover_pairs(cohort_mailer_ctx)
        result = _organic_activation(cohort_mailer_ctx.data, pairs)
        assert result["organic"] == 0
        assert result["total_debit"] == 0


# ---------------------------------------------------------------------------
# Module integration tests
# ---------------------------------------------------------------------------


class TestCumulativeReachModule:
    def test_produces_slides(self, cohort_mailer_ctx):
        module = CumulativeReach()
        results = module.run(cohort_mailer_ctx)
        assert len(results) >= 2  # A17.1, A17.2 at minimum
        assert all(r.success for r in results)

    def test_a17_1_cumulative_reach(self, cohort_mailer_ctx):
        module = CumulativeReach()
        results = module.run(cohort_mailer_ctx)
        a17_1 = [r for r in results if r.slide_id == "A17.1"]
        assert len(a17_1) == 1
        assert a17_1[0].chart_path.exists()

    def test_a17_2_penetration_rate(self, cohort_mailer_ctx):
        module = CumulativeReach()
        results = module.run(cohort_mailer_ctx)
        a17_2 = [r for r in results if r.slide_id == "A17.2"]
        assert len(a17_2) == 1
        assert a17_2[0].chart_path.exists()
        assert "Penetration" in a17_2[0].notes

    def test_a17_3_organic_activation(self, cohort_mailer_ctx):
        module = CumulativeReach()
        results = module.run(cohort_mailer_ctx)
        a17_3 = [r for r in results if r.slide_id == "A17.3"]
        assert len(a17_3) == 1
        assert a17_3[0].chart_path.exists()

    def test_stores_reach_results(self, cohort_mailer_ctx):
        module = CumulativeReach()
        module.run(cohort_mailer_ctx)
        assert "reach_cumulative" in cohort_mailer_ctx.results
        rc = cohort_mailer_ctx.results["reach_cumulative"]
        assert rc["cum_mailed"] > 0

    def test_no_pairs_returns_failure(self, cohort_mailer_ctx):
        cohort_mailer_ctx.data = cohort_mailer_ctx.data.drop(
            columns=["Apr24 Mail", "Apr24 Resp", "May24 Mail", "May24 Resp"]
        )
        cohort_mailer_ctx.results.pop("_mailer_pairs", None)
        module = CumulativeReach()
        results = module.run(cohort_mailer_ctx)
        assert len(results) == 1
        assert not results[0].success

    def test_notes_contain_counts(self, cohort_mailer_ctx):
        module = CumulativeReach()
        results = module.run(cohort_mailer_ctx)
        a17_1 = [r for r in results if r.slide_id == "A17.1"][0]
        assert "mailed" in a17_1.notes.lower()
