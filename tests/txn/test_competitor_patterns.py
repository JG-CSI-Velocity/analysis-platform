"""Tests for txn_analysis.competitor_patterns -- 3-tier matching."""

from __future__ import annotations

from txn_analysis.competitor_patterns import (
    ALL_COMPETITOR_PATTERNS,
    COMPETITOR_MERCHANTS,
    FALSE_POSITIVES,
    FINANCIAL_MCC_CODES,
    MATCH_TIERS,
    MatchResult,
    classify_merchant,
    is_false_positive,
)


class TestCompetitorMerchants:
    def test_seven_categories(self):
        assert set(COMPETITOR_MERCHANTS.keys()) == {
            "big_nationals",
            "regionals",
            "credit_unions",
            "digital_banks",
            "wallets_p2p",
            "bnpl",
            "alt_finance",
        }

    def test_each_category_has_valid_tier_keys(self):
        for cat, tiers in COMPETITOR_MERCHANTS.items():
            assert isinstance(tiers, dict), f"{cat} should be a dict"
            for tier in tiers:
                assert tier in MATCH_TIERS, f"Unknown tier '{tier}' in {cat}"

    def test_values_are_tuples(self):
        for cat, tiers in COMPETITOR_MERCHANTS.items():
            for tier_name, patterns in tiers.items():
                assert isinstance(patterns, tuple), f"{cat}.{tier_name} should be tuple"

    def test_no_empty_patterns(self):
        for cat, tiers in COMPETITOR_MERCHANTS.items():
            for tier_name, patterns in tiers.items():
                for p in patterns:
                    assert p.strip(), f"Empty pattern in {cat}.{tier_name}"

    def test_all_patterns_flattened(self):
        total = sum(
            len(patterns) for tiers in COMPETITOR_MERCHANTS.values() for patterns in tiers.values()
        )
        assert len(ALL_COMPETITOR_PATTERNS) == total

    def test_known_competitors_present(self):
        all_upper = [p.upper() for p in ALL_COMPETITOR_PATTERNS]
        assert "CHASE" in all_upper
        assert "WELLS FARGO" in all_upper
        assert "VENMO" in all_upper
        assert "KLARNA" in all_upper
        assert "CHIME" in all_upper

    def test_big_nationals_has_minimum_patterns(self):
        bn = COMPETITOR_MERCHANTS["big_nationals"]
        total = sum(len(v) for v in bn.values())
        assert total >= 10

    def test_alt_finance_category_exists(self):
        assert "alt_finance" in COMPETITOR_MERCHANTS
        af = COMPETITOR_MERCHANTS["alt_finance"]
        total = sum(len(v) for v in af.values())
        assert total >= 3


class TestClassifyMerchant:
    def test_exact_match(self):
        result = classify_merchant("CHASE")
        assert result == MatchResult("big_nationals", "exact", "CHASE")

    def test_starts_with_match(self):
        result = classify_merchant("BANK OF AMERICA NA 12345")
        assert result.category == "big_nationals"
        assert result.tier == "starts_with"
        assert result.pattern == "BANK OF AMERICA"

    def test_contains_match(self):
        result = classify_merchant("PAYMENT TO VENMO USER")
        assert result.category == "wallets_p2p"
        assert result.tier in ("exact", "starts_with", "contains")

    def test_no_match(self):
        result = classify_merchant("WALMART STORE 1234")
        assert result == MatchResult(None, None, None)

    def test_exact_prioritized_over_starts_with(self):
        # KEYBANK is in both exact and starts_with for big_nationals
        result = classify_merchant("KEYBANK")
        assert result.tier == "exact"

    def test_starts_with_prioritized_over_contains(self):
        # "ALLY BANK" is starts_with in digital_banks
        result = classify_merchant("ALLY BANK DEPOSIT 123")
        assert result.tier == "starts_with"

    def test_digital_bank_contains(self):
        result = classify_merchant("PURCHASE AT SYNCHRONY STORE")
        assert result.category == "digital_banks"
        assert result.tier == "contains"
        assert result.pattern == "SYNCHRONY"

    def test_bnpl_detection(self):
        result = classify_merchant("KLARNA")
        assert result.category == "bnpl"

    def test_alt_finance_detection(self):
        result = classify_merchant("MONEYLION ADVANCE")
        assert result.category == "alt_finance"
        assert result.tier == "starts_with"

    def test_whitespace_stripped(self):
        result = classify_merchant("  CHASE  ")
        assert result.category == "big_nationals"


class TestFalsePositives:
    def test_is_tuple(self):
        assert isinstance(FALSE_POSITIVES, tuple)

    def test_known_false_positives(self):
        assert "TOWING" in FALSE_POSITIVES
        assert "CHASE OUTDOORS" in FALSE_POSITIVES
        assert "CURRENT ELECTRIC" in FALSE_POSITIVES

    def test_is_false_positive_matches(self):
        assert is_false_positive("BOB'S TOWING SERVICE")
        assert is_false_positive("CHASE OUTDOORS LLC")

    def test_is_false_positive_rejects_valid(self):
        assert not is_false_positive("CHASE BANK NA")
        assert not is_false_positive("ALLY BANK")


class TestFinancialMccCodes:
    def test_is_tuple(self):
        assert isinstance(FINANCIAL_MCC_CODES, tuple)

    def test_has_core_codes(self):
        assert "6011" in FINANCIAL_MCC_CODES
        assert "6012" in FINANCIAL_MCC_CODES

    def test_all_are_digit_strings(self):
        for code in FINANCIAL_MCC_CODES:
            assert isinstance(code, str)
            assert code.isdigit()
