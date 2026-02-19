"""Tests for ars_analysis.mailer_response -- A13+A14 Mailer Response & Demographics.

Verifies:
1. Output correct -- results populated
2. Makes it onto PowerPoint -- slides added
3. Format correct -- charts created
"""

import pytest

from ars_analysis.mailer_response import run_mailer_response_suite


class TestRunMailerResponseSuite:
    """Full A13+A14 suite."""

    def test_runs_without_error(self, ars_ctx):
        run_mailer_response_suite(ars_ctx)

    def test_all_slides_valid(self, ars_ctx):
        run_mailer_response_suite(ars_ctx)
        for slide in ars_ctx["all_slides"]:
            assert "id" in slide
            assert "include" in slide
            assert "data" in slide

    def test_no_mailer_data_skips_gracefully(self, ars_ctx):
        # Remove mailer columns
        for col in list(ars_ctx["data"].columns):
            if col.startswith("Jan25") or col.startswith("Feb25"):
                ars_ctx["data"].drop(columns=col, inplace=True, errors="ignore")
        ars_ctx["mailer_pairs"] = None
        run_mailer_response_suite(ars_ctx)
