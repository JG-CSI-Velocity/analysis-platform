"""Tests for txn_analysis.financial_patterns."""

from __future__ import annotations

from txn_analysis.financial_patterns import ALL_FINANCIAL_PATTERNS, FINANCIAL_SERVICES_PATTERNS


class TestFinancialServicesPatterns:
    def test_nine_categories(self):
        assert len(FINANCIAL_SERVICES_PATTERNS) == 9

    def test_expected_categories(self):
        expected = {
            "Auto Loans",
            "Investment/Brokerage",
            "Treasury/Bonds",
            "Mortgage/HELOC",
            "Personal Loans",
            "Credit Cards",
            "Student Loans",
            "Business Loans",
            "Other Banks",
        }
        assert set(FINANCIAL_SERVICES_PATTERNS.keys()) == expected

    def test_values_are_tuples(self):
        for cat, patterns in FINANCIAL_SERVICES_PATTERNS.items():
            assert isinstance(patterns, tuple), f"{cat} values should be tuples"

    def test_no_empty_patterns(self):
        for cat, patterns in FINANCIAL_SERVICES_PATTERNS.items():
            for p in patterns:
                assert p.strip(), f"Empty pattern in {cat}"

    def test_all_patterns_flattened(self):
        total = sum(len(v) for v in FINANCIAL_SERVICES_PATTERNS.values())
        assert len(ALL_FINANCIAL_PATTERNS) == total

    def test_known_patterns_present(self):
        all_upper = [p.upper() for p in ALL_FINANCIAL_PATTERNS]
        assert "ROCKET MORTGAGE" in all_upper
        assert "FIDELITY INVESTMENTS" in all_upper
        assert "SBA LOAN PAYMENT" in all_upper
        assert "NAVIENT PAYMENT" in all_upper

    def test_auto_loans_has_major_brands(self):
        auto = [p.upper() for p in FINANCIAL_SERVICES_PATTERNS["Auto Loans"]]
        assert any("TOYOTA" in p for p in auto)
        assert any("FORD" in p for p in auto)
        assert any("GM" in p for p in auto)
