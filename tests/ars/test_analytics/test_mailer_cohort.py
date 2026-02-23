"""Tests for mailer cohort trajectory analysis (A16 series)."""

from __future__ import annotations

import pandas as pd

from ars_analysis.analytics.mailer._helpers import discover_pairs
from ars_analysis.analytics.mailer.cohort import (
    ResponderCohort,
    _compute_slopes,
    _find_first_response_month,
    _find_first_response_segment,
    _month_offset,
    build_cohort_trajectory,
)

# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestFindFirstResponseMonth:
    def test_finds_first_month(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        row = cohort_mailer_ctx.data.iloc[0]  # NU 5+ in Apr24
        result = _find_first_response_month(row, pairs)
        assert result == "Apr24"

    def test_non_responder_returns_none(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        row = cohort_mailer_ctx.data.iloc[15]  # NU non-responder
        result = _find_first_response_month(row, pairs)
        assert result is None

    def test_not_mailed_returns_none(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        row = cohort_mailer_ctx.data.iloc[45]  # Not mailed
        result = _find_first_response_month(row, pairs)
        assert result is None


class TestFindFirstResponseSegment:
    def test_nu_responder(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        row = cohort_mailer_ctx.data.iloc[0]
        result = _find_first_response_segment(row, pairs)
        assert result == "NU 5+"

    def test_th_responder(self, cohort_mailer_ctx):
        pairs = discover_pairs(cohort_mailer_ctx)
        row = cohort_mailer_ctx.data.iloc[25]  # TH-10 in Apr24
        result = _find_first_response_segment(row, pairs)
        assert result == "TH-10"


class TestMonthOffset:
    def test_same_month(self):
        ts = pd.Timestamp("2024-04-01")
        assert _month_offset(ts, ts) == 0

    def test_positive_offset(self):
        metric = pd.Timestamp("2024-07-01")
        anchor = pd.Timestamp("2024-04-01")
        assert _month_offset(metric, anchor) == 3

    def test_negative_offset(self):
        metric = pd.Timestamp("2024-02-01")
        anchor = pd.Timestamp("2024-04-01")
        assert _month_offset(metric, anchor) == -2


# ---------------------------------------------------------------------------
# Trajectory build tests
# ---------------------------------------------------------------------------


class TestBuildCohortTrajectory:
    def test_spend_trajectory_has_groups(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        assert not traj.empty
        assert set(traj.columns) == {"offset", "group", "avg_value", "n_accounts"}
        groups = set(traj["group"])
        assert "Responders" in groups
        assert "Non-Responders" in groups

    def test_swipe_trajectory_has_groups(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Swipes")
        assert not traj.empty
        groups = set(traj["group"])
        assert "Responders" in groups

    def test_segment_trajectory_has_segments(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend", by_segment=True)
        assert not traj.empty
        groups = set(traj["group"])
        assert "NU 5+" in groups
        assert "Non-Responders" in groups

    def test_responders_trend_up_after_m0(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        resp = traj[traj["group"] == "Responders"].sort_values("offset")
        post = resp[resp["offset"] > 0]["avg_value"].values
        # Fixture data has responders trending up after response
        if len(post) >= 2:
            assert post[-1] > post[0], "Responders should trend up post-response"

    def test_non_responders_trend_down(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        non_resp = traj[traj["group"] == "Non-Responders"].sort_values("offset")
        vals = non_resp["avg_value"].values
        if len(vals) >= 2:
            assert vals[-1] < vals[0], "Non-responders should trend down"

    def test_empty_on_no_pairs(self, cohort_mailer_ctx):
        # Remove mail columns to simulate no pairs
        cohort_mailer_ctx.data = cohort_mailer_ctx.data.drop(
            columns=["Apr24 Mail", "Apr24 Resp", "May24 Mail", "May24 Resp"]
        )
        cohort_mailer_ctx.results.pop("_mailer_pairs", None)
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        assert traj.empty

    def test_empty_on_no_metric_cols(self, cohort_mailer_ctx):
        # Remove spend columns
        spend_cols = [c for c in cohort_mailer_ctx.data.columns if "Spend" in c]
        swipe_cols = [c for c in cohort_mailer_ctx.data.columns if "Swipe" in c]
        cohort_mailer_ctx.data = cohort_mailer_ctx.data.drop(
            columns=spend_cols + swipe_cols
        )
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        assert traj.empty


class TestComputeSlopes:
    def test_slopes_computed(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        pre, post = _compute_slopes(traj, "Responders")
        # Pre should be negative or near-zero, post should be positive
        assert isinstance(pre, float)
        assert isinstance(post, float)

    def test_slopes_missing_group(self, cohort_mailer_ctx):
        traj = build_cohort_trajectory(cohort_mailer_ctx, "Spend")
        pre, post = _compute_slopes(traj, "NonExistent")
        assert pre == 0.0
        assert post == 0.0


# ---------------------------------------------------------------------------
# Module integration tests (chart output)
# ---------------------------------------------------------------------------


class TestResponderCohortModule:
    def test_produces_slides(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        assert len(results) >= 4  # A16.1-A16.5 minimum (need spend+swipes)
        assert all(r.success for r in results)

    def test_a16_1_spend_trajectory(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_1 = [r for r in results if r.slide_id == "A16.1"]
        assert len(a16_1) == 1
        assert a16_1[0].chart_path is not None
        assert a16_1[0].chart_path.exists()

    def test_a16_2_swipe_trajectory(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_2 = [r for r in results if r.slide_id == "A16.2"]
        assert len(a16_2) == 1
        assert a16_2[0].chart_path.exists()

    def test_a16_3_segment_spend(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_3 = [r for r in results if r.slide_id == "A16.3"]
        assert len(a16_3) == 1
        assert a16_3[0].chart_path.exists()

    def test_a16_4_segment_swipes(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_4 = [r for r in results if r.slide_id == "A16.4"]
        assert len(a16_4) == 1
        assert a16_4[0].chart_path.exists()

    def test_a16_5_direction_change(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_5 = [r for r in results if r.slide_id == "A16.5"]
        assert len(a16_5) == 1
        assert a16_5[0].chart_path.exists()

    def test_a16_6_present_with_8_months(self, cohort_mailer_ctx):
        """A16.6 should appear when we have 8 metric months."""
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_6 = [r for r in results if r.slide_id == "A16.6"]
        assert len(a16_6) == 1
        assert a16_6[0].chart_path.exists()

    def test_a16_6_skipped_few_months(self, mailer_ctx):
        """A16.6 should be skipped when fewer than 8 metric months."""
        module = ResponderCohort()
        results = module.run(mailer_ctx)
        a16_6 = [r for r in results if r.slide_id == "A16.6"]
        assert len(a16_6) == 0

    def test_no_pairs_returns_failure(self, cohort_mailer_ctx):
        cohort_mailer_ctx.data = cohort_mailer_ctx.data.drop(
            columns=["Apr24 Mail", "Apr24 Resp", "May24 Mail", "May24 Resp"]
        )
        cohort_mailer_ctx.results.pop("_mailer_pairs", None)
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        assert len(results) == 1
        assert not results[0].success

    def test_notes_contain_insight(self, cohort_mailer_ctx):
        module = ResponderCohort()
        results = module.run(cohort_mailer_ctx)
        a16_1 = [r for r in results if r.slide_id == "A16.1"][0]
        assert "Responders" in a16_1.notes
