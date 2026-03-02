"""Tests for A15 ladder analysis -- classify_responder, analyze_ladder, enriched inside numbers."""

import pandas as pd

from ars_analysis.analytics.mailer._helpers import (
    analyze_ladder,
    classify_responder,
    compute_inside_numbers,
)
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext

# ---------------------------------------------------------------------------
# classify_responder
# ---------------------------------------------------------------------------


class TestClassifyResponder:
    """classify_responder determines First/Repeat and Up/Same/Down."""

    def test_first_responder_no_prior(self):
        result = classify_responder("TH-10", [])
        assert result["include"] is True
        assert result["type"] == "First"
        assert result["movement"] is None

    def test_first_responder_only_failed_priors(self):
        result = classify_responder("NU 5+", ["NU 1-4", None, "NU 1-4"])
        assert result["include"] is True
        assert result["type"] == "First"

    def test_repeat_same_tier(self):
        result = classify_responder("TH-15", ["TH-15"])
        assert result["include"] is True
        assert result["type"] == "Repeat"
        assert result["movement"] == "Same"

    def test_repeat_moved_up(self):
        result = classify_responder("TH-20", ["TH-10", "TH-15"])
        assert result["include"] is True
        assert result["type"] == "Repeat"
        assert result["movement"] == "Up"

    def test_repeat_moved_down(self):
        result = classify_responder("TH-10", ["TH-25", "TH-20"])
        assert result["include"] is True
        assert result["type"] == "Repeat"
        assert result["movement"] == "Down"

    def test_nu14_not_included(self):
        result = classify_responder("NU 1-4", ["TH-10"])
        assert result["include"] is False

    def test_none_current_not_included(self):
        result = classify_responder(None, ["TH-10"])
        assert result["include"] is False

    def test_empty_string_not_included(self):
        result = classify_responder("", ["TH-10"])
        assert result["include"] is False

    def test_most_recent_prior_used(self):
        # TH-25 (score 6) is most recent; current TH-15 (4) -> Down
        result = classify_responder("TH-15", ["TH-10", "TH-25"])
        assert result["movement"] == "Down"


# ---------------------------------------------------------------------------
# analyze_ladder
# ---------------------------------------------------------------------------


def _make_ladder_df():
    """DataFrame with 3 months of mailer data for ladder analysis."""
    return pd.DataFrame(
        {
            "Apr24 Mail": ["NU"] * 5 + ["TH-10"] * 3 + ["TH-15"] * 2,
            "Apr24 Resp": ["NU 5+", "NU 5+", "NU 1-4", None, None, "TH-10", None, None, "TH-15", None],
            "May24 Mail": ["NU"] * 5 + ["TH-10"] * 3 + ["TH-15"] * 2,
            "May24 Resp": ["NU 5+", "TH-10", None, None, None, "TH-10", "TH-10", None, None, "TH-15"],
            "Jun24 Mail": ["NU"] * 5 + ["TH-10"] * 3 + ["TH-15"] * 2,
            "Jun24 Resp": ["TH-15", None, None, "NU 5+", None, "TH-10", None, None, "TH-15", None],
        }
    )


def _make_pairs():
    return [
        ("Apr24", "Apr24 Resp", "Apr24 Mail"),
        ("May24", "May24 Resp", "May24 Mail"),
        ("Jun24", "Jun24 Resp", "Jun24 Mail"),
    ]


class TestAnalyzeLadder:
    """analyze_ladder aggregates first/repeat and movement stats."""

    def test_first_month_returns_none(self):
        data = _make_ladder_df()
        pairs = _make_pairs()
        assert analyze_ladder(data, pairs, 0) is None

    def test_second_month_has_results(self):
        data = _make_ladder_df()
        pairs = _make_pairs()
        result = analyze_ladder(data, pairs, 1)
        assert result is not None
        assert result["total_successful"] > 0

    def test_first_and_repeat_counts(self):
        data = _make_ladder_df()
        pairs = _make_pairs()
        result = analyze_ladder(data, pairs, 1)
        # May24 responders: NU 5+ (row 0, prior NU 5+ -> Repeat Same),
        # TH-10 (row 1, prior NU 5+ -> Repeat Up),
        # TH-10 (row 5, prior TH-10 -> Repeat Same),
        # TH-10 (row 6, no prior -> First),
        # TH-15 (row 9, no prior -> First)
        assert result["first_count"] + result["repeat_count"] == result["total_successful"]

    def test_movement_counts_sum(self):
        data = _make_ladder_df()
        pairs = _make_pairs()
        result = analyze_ladder(data, pairs, 2)
        repeat = result["repeat_count"]
        movements = result["movement_up"] + result["movement_same"] + result["movement_down"]
        assert movements == repeat

    def test_distribution_populated(self):
        data = _make_ladder_df()
        pairs = _make_pairs()
        result = analyze_ladder(data, pairs, 1)
        assert sum(result["distribution"].values()) == result["total_successful"]


# ---------------------------------------------------------------------------
# compute_inside_numbers (enriched)
# ---------------------------------------------------------------------------


def _make_inside_ctx(tmp_path):
    """Minimal context for compute_inside_numbers tests."""
    paths = OutputPaths(
        base_dir=tmp_path,
        charts_dir=tmp_path / "charts",
        excel_dir=tmp_path,
        pptx_dir=tmp_path,
    )
    df = pd.DataFrame(
        {
            "Apr24 Mail": ["NU"] * 10,
            "Apr24 Resp": ["NU 5+"] * 6 + [None] * 4,
            "Date Opened": pd.to_datetime(["2023-06-01"] * 6 + ["2020-01-01"] * 4),
            "DOB": pd.to_datetime(["1975-03-15"] * 4 + ["1995-06-20"] * 2 + ["1980-01-01"] * 4),
        }
    )
    ctx = PipelineContext(
        client=ClientInfo(
            client_id="9999",
            client_name="Test CU",
            month="2024.04",
        ),
        paths=paths,
        data=df,
    )
    return ctx, df


class TestComputeInsideNumbersEnriched:
    """compute_inside_numbers returns enriched metrics with ladder and MoM."""

    def test_without_ladder_has_base_metrics(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        metrics = compute_inside_numbers(ctx, df, "Apr24 Resp")
        # Should have at least account age and DOB metrics
        assert len(metrics) >= 2

    def test_with_ladder_has_first_time_metric(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        ladder = {
            "first_count": 3,
            "repeat_count": 3,
            "movement_up": 1,
            "movement_same": 1,
            "movement_down": 1,
            "total_successful": 6,
        }
        metrics = compute_inside_numbers(ctx, df, "Apr24 Resp", ladder=ladder)
        descs = [d for _, d in metrics]
        assert any("First-time" in d for d in descs)

    def test_with_ladder_has_movement_metric(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        ladder = {
            "first_count": 2,
            "repeat_count": 4,
            "movement_up": 2,
            "movement_same": 1,
            "movement_down": 1,
            "total_successful": 6,
        }
        metrics = compute_inside_numbers(ctx, df, "Apr24 Resp", ladder=ladder)
        descs = [d for _, d in metrics]
        assert any("moved up" in d for d in descs)

    def test_mom_delta_positive(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        metrics = compute_inside_numbers(
            ctx, df, "Apr24 Resp", prev_rate=50.0, current_rate=60.0
        )
        # Should have a "+10.0pp" metric
        pcts = [p for p, _ in metrics]
        assert any("+" in p and "pp" in p for p in pcts)

    def test_mom_delta_negative(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        metrics = compute_inside_numbers(
            ctx, df, "Apr24 Resp", prev_rate=60.0, current_rate=50.0
        )
        pcts = [p for p, _ in metrics]
        assert any("-" in p and "pp" in p for p in pcts)

    def test_no_mom_without_prev_rate(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        metrics = compute_inside_numbers(ctx, df, "Apr24 Resp")
        pcts = [p for p, _ in metrics]
        assert not any("pp" in p for p in pcts)

    def test_dob_dominant_bucket(self, tmp_path):
        ctx, df = _make_inside_ctx(tmp_path)
        metrics = compute_inside_numbers(ctx, df, "Apr24 Resp")
        descs = [d for _, d in metrics]
        assert any("aged" in d for d in descs)


# ---------------------------------------------------------------------------
# _ladder_slides (integration via mailer_ctx fixture)
# ---------------------------------------------------------------------------


class TestLadderSlides:
    """_ladder_slides produces AnalysisResult per month from 2nd month onward."""

    def test_ladder_slides_with_mailer_ctx(self, mailer_ctx):
        from ars_analysis.analytics.mailer.response import _ladder_slides

        results = _ladder_slides(mailer_ctx)
        # mailer_ctx has 2 months (Apr24, May24), so 1 ladder slide (May24)
        assert len(results) >= 1

    def test_ladder_slide_id_format(self, mailer_ctx):
        from ars_analysis.analytics.mailer.response import _ladder_slides

        results = _ladder_slides(mailer_ctx)
        for r in results:
            assert r.slide_id.startswith("A15.")

    def test_ladder_slide_has_chart(self, mailer_ctx):
        from ars_analysis.analytics.mailer.response import _ladder_slides

        results = _ladder_slides(mailer_ctx)
        for r in results:
            assert r.chart_path is not None
            assert r.chart_path.exists()

    def test_ladder_slide_headline_is_conclusion(self, mailer_ctx):
        from ars_analysis.analytics.mailer.response import _ladder_slides

        results = _ladder_slides(mailer_ctx)
        for r in results:
            # Headline should contain responder count (conclusion, not label)
            assert "responders" in r.title.lower()
