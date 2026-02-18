"""Tests for txn_analysis.competitor_patterns."""

from __future__ import annotations

from txn_analysis.competitor_patterns import ALL_COMPETITOR_PATTERNS, COMPETITOR_MERCHANTS


class TestCompetitorMerchants:
    def test_six_categories(self):
        assert set(COMPETITOR_MERCHANTS.keys()) == {
            "big_nationals",
            "regionals",
            "credit_unions",
            "digital_banks",
            "wallets_p2p",
            "bnpl",
        }

    def test_big_nationals_non_empty(self):
        assert len(COMPETITOR_MERCHANTS["big_nationals"]) >= 10

    def test_values_are_tuples(self):
        for cat, patterns in COMPETITOR_MERCHANTS.items():
            assert isinstance(patterns, tuple), f"{cat} values should be tuples"

    def test_no_empty_patterns(self):
        for cat, patterns in COMPETITOR_MERCHANTS.items():
            for p in patterns:
                assert p.strip(), f"Empty pattern in {cat}"

    def test_all_patterns_flattened(self):
        total = sum(len(v) for v in COMPETITOR_MERCHANTS.values())
        assert len(ALL_COMPETITOR_PATTERNS) == total

    def test_known_competitors_present(self):
        all_upper = [p.upper() for p in ALL_COMPETITOR_PATTERNS]
        assert "CHASE" in all_upper
        assert "WELLS FARGO" in all_upper
        assert "VENMO" in all_upper
        assert "KLARNA" in all_upper
        assert "CHIME" in all_upper
