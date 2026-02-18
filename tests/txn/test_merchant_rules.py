"""Tests for txn_analysis.merchant_rules."""

from __future__ import annotations

import pytest

from txn_analysis.merchant_rules import MERCHANT_RULES, MerchantRule, standardize_merchant_name


class TestMerchantRule:
    def test_frozen(self):
        rule = MerchantRule(required=("FOO",), canonical="BAR")
        with pytest.raises(Exception):
            rule.canonical = "BAZ"  # type: ignore[misc]

    def test_rules_non_empty(self):
        assert len(MERCHANT_RULES) > 100


class TestStandardizeMerchantName:
    # Tech & Digital
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("APPLE.COM/BILL", "APPLE.COM/BILL"),
            ("APPLE COM BILL", "APPLE.COM/BILL"),
            ("APPLE CASH SENT MONEY", "APPLE CASH - SENT MONEY"),
            ("APPLE CASH INST XFER", "APPLE CASH - TRANSFERS"),
            ("APPLE CASH BALANCE ADD", "APPLE CASH - BALANCE ADD"),
            ("APPLE STORE #123", "APPLE STORE"),
            ("GOOGLE PLAY", "GOOGLE PLAY"),
            ("GOOGLE STORAGE", "GOOGLE STORAGE"),
            ("GOOGLE DRIVE", "GOOGLE STORAGE"),
            ("GOOGLE YOUTUBE", "YOUTUBE"),
            ("GOOGLE SERVICES", "GOOGLE"),
        ],
    )
    def test_tech(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Amazon
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("AMAZON PRIME", "AMAZON PRIME"),
            ("AMAZON.COM AMZN", "AMAZON"),
            ("AMZN Mktp US", "AMAZON"),
        ],
    )
    def test_amazon(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Streaming
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("NETFLIX.COM", "NETFLIX"),
            ("SPOTIFY USA", "SPOTIFY"),
            ("HULU PLUS", "HULU"),
            ("DISNEY PLUS", "DISNEY+"),
        ],
    )
    def test_streaming(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Retail
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("WALMART.COM", "WALMART.COM"),
            ("WAL-MART #3893", "WALMART (ALL LOCATIONS)"),
            ("WM SUPERCENTER #456", "WALMART (ALL LOCATIONS)"),
            ("TARGET T-1234", "TARGET (ALL LOCATIONS)"),
            ("COSTCO WHSE #123", "COSTCO"),
            ("HOME DEPOT #4567", "HOME DEPOT"),
            ("LOWES #1234", "LOWE'S"),
            ("BEST BUY 00123", "BEST BUY"),
        ],
    )
    def test_retail(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Grocers
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("JEWEL OSCO #123", "JEWEL-OSCO (ALL LOCATIONS)"),
            ("MEIJER #456", "MEIJER (ALL LOCATIONS)"),
            ("PUBLIX #789", "PUBLIX"),
            ("ALDI 12345", "ALDI"),
            ("TRADER JOE'S #100", "TRADER JOE'S"),
        ],
    )
    def test_grocers(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Gas / Convenience
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("SPEEDWAY 01234", "SPEEDWAY"),
            ("SHELL OIL 12345", "SHELL"),
            ("7-ELEVEN #789", "7-ELEVEN"),
        ],
    )
    def test_gas(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Restaurants
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("MCDONALDS F3928", "MCDONALD'S"),
            ("CHIPOTLE ONLINE", "CHIPOTLE"),
            ("STARBUCKS STORE 1234", "STARBUCKS"),
            ("DUNKIN #7890", "DUNKIN"),
            ("DOORDASH*MCDONALDS", "DOORDASH"),
            ("UBER EATS", "UBER EATS"),
            ("UBER TRIP", "UBER"),
            ("PANERA BREAD 123", "PANERA BREAD"),
            ("TACO BELL 456", "TACO BELL"),
            ("BURGER KING 789", "BURGER KING"),
        ],
    )
    def test_restaurants(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # P2P / Fintech
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("PAYPAL *PURCHASE", "PAYPAL"),
            ("PAYPAL TRANSFER TO", "PAYPAL TRANSFERS"),
            ("VENMO PAYMENT", "VENMO"),
            ("CASH APP*JOHN", "CASH APP"),
            ("ZELLE PAYMENT", "ZELLE"),
        ],
    )
    def test_p2p(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Financial services
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("CHASE BANK PAYMENT", "CHASE"),
            ("WELLS FARGO PAYMENT", "WELLS FARGO"),
            ("CAPITAL ONE PAYMENT", "CAPITAL ONE"),
            ("AMEX EPAYMENT", "AMERICAN EXPRESS"),
            ("DISCOVER CARD PAYMENT", "DISCOVER"),
            ("SYNCHRONY BANK PAYMENT", "SYNCHRONY"),
            ("CHIME TRANSFER", "CHIME"),
            ("ROCKET MORTGAGE", "ROCKET MORTGAGE"),
            ("NAVIENT PAYMENT", "NAVIENT"),
            ("NELNET PAYMENT", "NELNET"),
            ("SOFI LENDING", "SOFI"),
        ],
    )
    def test_financial(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Telecom
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("AT&T BILL PAYMENT", "AT&T"),
            ("TMOBILE AUTOPAY", "T-MOBILE"),
            ("COMCAST XFINITY", "COMCAST/XFINITY"),
            ("VERIZON WIRELESS", "VERIZON WIRELESS"),
        ],
    )
    def test_telecom(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Insurance
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("STATE FARM INS", "STATE FARM"),
            ("GEICO INSURANCE", "GEICO"),
        ],
    )
    def test_insurance(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # No match -> return original
    def test_no_match_returns_original(self):
        assert standardize_merchant_name("RANDOM SHOP 123") == "RANDOM SHOP 123"

    # Case insensitive
    def test_case_insensitive(self):
        assert standardize_merchant_name("netflix.com") == "NETFLIX"

    # Startswith filter
    def test_startswith_shell(self):
        # "SHELL" alone (not starting with SHELL) should NOT match via startswith rule
        # but will match via SHELL+OIL or SHELL+SERVICE rules
        assert standardize_merchant_name("SHELLFISH RESTAURANT") == "SHELLFISH RESTAURANT"
        assert standardize_merchant_name("SHELL GAS") == "SHELL"

    # BNPL
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("KLARNA*PURCHASE", "KLARNA"),
            ("AFFIRM*PURCHASE", "AFFIRM"),
        ],
    )
    def test_bnpl(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # Government
    def test_government(self):
        assert standardize_merchant_name("TOWN OF SPRINGFIELD") == "MUNICIPAL PAYMENTS (TOWNS)"
        assert standardize_merchant_name("CITY OF CHICAGO") == "MUNICIPAL PAYMENTS (CITIES)"
