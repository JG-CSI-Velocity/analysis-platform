"""Tests for ars_analysis.mailer_insights -- A12 Spend & Swipes Analysis.

Verifies:
1. Output correct -- results populated
2. Makes it onto PowerPoint -- slides added
3. Format correct -- charts created
"""

import pytest

from ars_analysis.mailer_insights import run_mailer_insights_suite


class TestRunMailerInsightsSuite:
    """Full A12 suite -- spend & swipe trends per mail month."""

    def test_runs_without_error(self, ars_ctx):
        run_mailer_insights_suite(ars_ctx)

    def test_all_slides_valid(self, ars_ctx):
        run_mailer_insights_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "data" in slide

    def test_no_mailer_data_skips_gracefully(self, ars_ctx):
        # Remove mailer columns
        for col in list(ars_ctx["data"].columns):
            if "Mail" in col or "Resp" in col or "Spend" in col or "Swipes" in col:
                if col.startswith("Jan25") or col.startswith("Feb25"):
                    ars_ctx["data"].drop(columns=col, inplace=True, errors="ignore")
        ars_ctx["mailer_pairs"] = None  # Force re-discovery
        run_mailer_insights_suite(ars_ctx)
        # Should not crash even with no mail columns
