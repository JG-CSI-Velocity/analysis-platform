"""Tests for ars_analysis.mailer_common."""

import pandas as pd

from ars_analysis.mailer_common import (
    MAILED_SEGMENTS,
    RESPONSE_SEGMENTS,
    SPEND_PATTERN,
    SWIPE_PATTERN,
    TH_SEGMENTS,
    build_mailed_mask,
    build_responder_mask,
    discover_pairs,
    parse_month,
    safe,
)


class TestConstants:
    def test_response_segments(self):
        assert "NU 5+" in RESPONSE_SEGMENTS
        assert len(RESPONSE_SEGMENTS) == 5

    def test_mailed_segments(self):
        assert "NU" in MAILED_SEGMENTS
        assert "TH-10" in MAILED_SEGMENTS

    def test_th_segments(self):
        assert all(s.startswith("TH-") for s in TH_SEGMENTS)


class TestPatterns:
    def test_spend_pattern_match(self):
        assert SPEND_PATTERN.match("Jan25 Spend")
        assert SPEND_PATTERN.match("Aug24 Spend")

    def test_spend_pattern_no_match(self):
        assert not SPEND_PATTERN.match("Total Spend")
        assert not SPEND_PATTERN.match("jan25 Spend")

    def test_swipe_pattern_match(self):
        assert SWIPE_PATTERN.match("Feb25 Swipes")

    def test_swipe_pattern_no_match(self):
        assert not SWIPE_PATTERN.match("Total Swipes")


class TestParseMonth:
    def test_valid_month(self):
        result = parse_month("Aug25 Mail")
        assert result.month == 8
        assert result.year == 2025

    def test_invalid(self):
        result = parse_month("Invalid")
        assert pd.isna(result)


class TestDiscoverPairs:
    def test_discovers_pairs(self):
        ctx = {
            "data": pd.DataFrame(
                {
                    "Acct": [1, 2],
                    "Jan25 Mail": ["NU", "TH-10"],
                    "Jan25 Resp": ["NU 5+", None],
                    "Feb25 Mail": ["NU", None],
                    "Feb25 Resp": ["NU 5+", None],
                }
            ),
            "client_id": "9999",
        }
        pairs = discover_pairs(ctx)
        assert len(pairs) == 2
        assert pairs[0][0] == "Jan25"
        assert pairs[1][0] == "Feb25"

    def test_caches_result(self):
        cached = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        ctx = {"mailer_pairs": cached}
        result = discover_pairs(ctx)
        assert result is cached

    def test_no_mail_cols(self):
        ctx = {
            "data": pd.DataFrame({"Acct": [1]}),
            "client_id": "",
        }
        pairs = discover_pairs(ctx)
        assert pairs == []


class TestBuildMasks:
    def test_responder_mask(self):
        data = pd.DataFrame(
            {
                "Jan25 Resp": ["NU 5+", "NU 1-4", None],
            }
        )
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        mask = build_responder_mask(data, pairs)
        assert mask.tolist() == [True, False, False]

    def test_mailed_mask(self):
        data = pd.DataFrame(
            {
                "Jan25 Mail": ["NU", "TH-10", None],
            }
        )
        pairs = [("Jan25", "Jan25 Resp", "Jan25 Mail")]
        mask = build_mailed_mask(data, pairs)
        assert mask.tolist() == [True, True, False]


class TestSafe:
    def test_success(self):
        ctx = {"_progress_callback": None}
        result = safe(lambda c: {**c, "done": True}, ctx, "test")
        assert result["done"] is True

    def test_failure(self, capsys):
        ctx = {"_progress_callback": None}
        result = safe(lambda c: 1 / 0, ctx, "div_zero")
        assert result is ctx
        assert "div_zero failed" in capsys.readouterr().out
