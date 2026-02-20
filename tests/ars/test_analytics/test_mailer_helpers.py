"""Tests for mailer shared helpers."""

import pandas as pd

from ars_analysis.analytics.mailer._helpers import (
    AGE_SEGMENTS,
    MAILED_SEGMENTS,
    RESPONSE_SEGMENTS,
    SEGMENT_COLORS,
    SPEND_PATTERN,
    SWIPE_PATTERN,
    TH_SEGMENTS,
    VALID_RESPONSES,
    analyze_month,
    build_mailed_mask,
    build_responder_mask,
    discover_metric_cols,
    discover_pairs,
    format_title,
    parse_month,
)

# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


class TestConstants:
    """Segment constants have expected values."""

    def test_response_segments_count(self):
        assert len(RESPONSE_SEGMENTS) == 5

    def test_mailed_segments_count(self):
        assert len(MAILED_SEGMENTS) == 5

    def test_th_segments_subset_of_mailed(self):
        assert all(s in MAILED_SEGMENTS for s in TH_SEGMENTS)

    def test_valid_responses_keys(self):
        assert set(VALID_RESPONSES.keys()) == set(MAILED_SEGMENTS)

    def test_segment_colors_has_all(self):
        for s in RESPONSE_SEGMENTS:
            assert s in SEGMENT_COLORS

    def test_spend_pattern(self):
        assert SPEND_PATTERN.match("Apr24 Spend")
        assert not SPEND_PATTERN.match("Total Spend")

    def test_swipe_pattern(self):
        assert SWIPE_PATTERN.match("May24 Swipes")
        assert not SWIPE_PATTERN.match("24May Swipes")

    def test_age_segments_count(self):
        assert len(AGE_SEGMENTS) == 5


# ---------------------------------------------------------------------------
# parse_month
# ---------------------------------------------------------------------------


class TestParseMonth:
    """parse_month extracts datetime from column names."""

    def test_mail_column(self):
        ts = parse_month("Aug25 Mail")
        assert ts.year == 2025
        assert ts.month == 8

    def test_spend_column(self):
        ts = parse_month("Apr24 Spend")
        assert ts.year == 2024
        assert ts.month == 4

    def test_bare_month(self):
        ts = parse_month("Jan23")
        assert ts.year == 2023
        assert ts.month == 1

    def test_invalid_returns_nat(self):
        assert pd.isna(parse_month("nonsense"))


# ---------------------------------------------------------------------------
# format_title
# ---------------------------------------------------------------------------


class TestFormatTitle:
    """format_title converts MmmYY to full month name."""

    def test_aug25(self):
        assert format_title("Aug25") == "August 2025"

    def test_jan23(self):
        assert format_title("Jan23") == "January 2023"

    def test_invalid_passthrough(self):
        assert format_title("nonsense") == "nonsense"


# ---------------------------------------------------------------------------
# discover_pairs
# ---------------------------------------------------------------------------


class TestDiscoverPairs:
    """discover_pairs finds Mail/Resp column pairs."""

    def test_finds_two_pairs(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        assert len(pairs) == 2

    def test_pair_structure(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        for month, resp_col, mail_col in pairs:
            assert "Mail" in mail_col
            assert "Resp" in resp_col
            assert month in mail_col

    def test_sorted_chronologically(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        months = [m for m, _, _ in pairs]
        assert months == ["Apr24", "May24"]

    def test_caches_result(self, mailer_ctx):
        pairs1 = discover_pairs(mailer_ctx)
        pairs2 = discover_pairs(mailer_ctx)
        assert pairs1 is pairs2

    def test_empty_without_data(self, mailer_ctx):
        mailer_ctx.data = None
        assert discover_pairs(mailer_ctx) == []


# ---------------------------------------------------------------------------
# discover_metric_cols
# ---------------------------------------------------------------------------


class TestDiscoverMetricCols:
    """discover_metric_cols finds Spend/Swipes columns."""

    def test_finds_spend_cols(self, mailer_ctx):
        spend, _ = discover_metric_cols(mailer_ctx)
        assert len(spend) == 4  # Feb24, Mar24, Apr24, May24

    def test_finds_swipe_cols(self, mailer_ctx):
        _, swipes = discover_metric_cols(mailer_ctx)
        assert len(swipes) == 4

    def test_sorted_chronologically(self, mailer_ctx):
        spend, _ = discover_metric_cols(mailer_ctx)
        assert "Feb24" in spend[0]
        assert "May24" in spend[-1]


# ---------------------------------------------------------------------------
# Mask builders
# ---------------------------------------------------------------------------


class TestMaskBuilders:
    """build_responder_mask and build_mailed_mask work correctly."""

    def test_responder_mask(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        mask = build_responder_mask(mailer_ctx.data, pairs)
        assert mask.sum() > 0
        assert mask.sum() < len(mailer_ctx.data)

    def test_mailed_mask(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        mask = build_mailed_mask(mailer_ctx.data, pairs)
        assert mask.sum() > 0


# ---------------------------------------------------------------------------
# analyze_month
# ---------------------------------------------------------------------------


class TestAnalyzeMonth:
    """analyze_month computes per-segment response stats."""

    def test_returns_tuple(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        month, resp_col, mail_col = pairs[0]
        seg, total_m, total_r, rate = analyze_month(
            mailer_ctx.data,
            resp_col,
            mail_col,
        )
        assert isinstance(seg, dict)
        assert total_m > 0
        assert total_r > 0
        assert 0 < rate < 100

    def test_segments_present(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        _, resp_col, mail_col = pairs[0]
        seg, _, _, _ = analyze_month(mailer_ctx.data, resp_col, mail_col)
        assert "NU 5+" in seg
        assert "TH-10" in seg

    def test_apr24_counts(self, mailer_ctx):
        pairs = discover_pairs(mailer_ctx)
        _, resp_col, mail_col = pairs[0]  # Apr24
        seg, total_m, total_r, _ = analyze_month(
            mailer_ctx.data,
            resp_col,
            mail_col,
        )
        # Apr24: NU 8, TH-10 5, TH-15 3 = 16 responders out of 40 mailed
        assert total_r == 16
        assert total_m == 40
        assert seg["NU 5+"]["responders"] == 8
