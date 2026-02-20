"""Tests for referral analysis registry and run_all_referral_analyses."""

from __future__ import annotations

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses import (
    OVERVIEW_ANALYSIS,
    REFERRAL_ANALYSIS_REGISTRY,
    run_all_referral_analyses,
)


class TestReferralAnalysisRegistry:
    """Tests for the referral analysis registry."""

    def test_registry_has_seven_analyses(self):
        assert len(REFERRAL_ANALYSIS_REGISTRY) == 7

    def test_registry_entries_are_tuples(self):
        for entry in REFERRAL_ANALYSIS_REGISTRY:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            name, func = entry
            assert isinstance(name, str)
            assert callable(func)

    def test_overview_analysis_is_separate(self):
        name, func = OVERVIEW_ANALYSIS
        assert name == "Overview KPIs"
        assert callable(func)

    def test_registry_names_unique(self):
        names = [name for name, _ in REFERRAL_ANALYSIS_REGISTRY]
        assert len(names) == len(set(names))


class TestRunAllReferralAnalyses:
    """Tests for run_all_referral_analyses."""

    def test_returns_list_of_results(self, referral_context):
        results = run_all_referral_analyses(referral_context)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_returns_eight_results(self, referral_context):
        """7 registry + 1 overview = 8 total."""
        results = run_all_referral_analyses(referral_context)
        assert len(results) == 8

    def test_last_result_is_overview(self, referral_context):
        results = run_all_referral_analyses(referral_context)
        assert results[-1].name == "Overview KPIs"

    def test_progress_callback_called(self, referral_context):
        calls = []

        def on_progress(current, total, name):
            calls.append((current, total, name))

        run_all_referral_analyses(referral_context, on_progress=on_progress)
        # 7 registry + 1 overview = 8 progress calls
        assert len(calls) == 8

    def test_no_errors_on_valid_data(self, referral_context):
        results = run_all_referral_analyses(referral_context)
        for r in results:
            assert r.error is None, f"{r.name} had error: {r.error}"

    def test_empty_context_no_crash(self, empty_context):
        results = run_all_referral_analyses(empty_context)
        assert len(results) == 8
        for r in results:
            assert r.error is None, f"{r.name} had error: {r.error}"
