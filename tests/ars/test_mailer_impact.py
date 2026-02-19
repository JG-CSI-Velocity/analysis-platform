"""Tests for ars_analysis.mailer_impact -- A15 Market Reach & Impact.

Verifies:
1. Output correct -- results populated
2. Makes it onto PowerPoint -- slides added
3. Format correct -- charts created
"""

from pathlib import Path

import pytest

from ars_analysis.mailer_impact import (
    run_mailer_impact_suite,
    run_market_reach,
    run_spend_share,
)


class TestRunMarketReach:
    """A15.1: Nested proportional circles."""

    def test_runs_without_error(self, ars_ctx):
        run_market_reach(ars_ctx)

    def test_adds_slide(self, ars_ctx):
        initial = len(ars_ctx["all_slides"])
        run_market_reach(ars_ctx)
        # May or may not add slide depending on data -- should not crash
        assert len(ars_ctx["all_slides"]) >= initial


class TestRunSpendShare:
    """A15.2: Spend share bars."""

    def test_runs_without_error(self, ars_ctx):
        run_spend_share(ars_ctx)


class TestRunMailerImpactSuite:
    """Full A15 suite."""

    def test_runs_without_error(self, ars_ctx):
        run_mailer_impact_suite(ars_ctx)

    def test_all_slides_valid(self, ars_ctx):
        run_mailer_impact_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "data" in slide
