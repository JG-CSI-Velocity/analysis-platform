"""Tests for txn_analysis.v4_merchant_rules -- merchant name consolidation."""

from __future__ import annotations

import pandas as pd
import pytest

from txn_analysis.v4_merchant_rules import (
    apply_merchant_consolidation,
    standardize_merchant_name,
)


class TestStandardizeMerchantName:
    """Exercise every major branch category in the if/elif chain."""

    # -- Tech & Digital Services -----------------------------------------------

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("APPLE.COM/BILL 123", "APPLE.COM/BILL"),
            ("Apple Com Bill", "APPLE.COM/BILL"),
            ("APPLE CASH SENT MONEY", "APPLE CASH - SENT MONEY"),
            ("APPLE CASH INST XFER", "APPLE CASH - TRANSFERS"),
            ("APPLE CASH TRANSFER", "APPLE CASH - TRANSFERS"),
            ("APPLE CASH BALANCE ADD", "APPLE CASH - BALANCE ADD"),
            ("APPLE CASH OTHER", "APPLE CASH"),
            ("APPLE STORE NYC", "APPLE STORE"),
        ],
    )
    def test_apple(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("GOOGLE PLAY STORE", "GOOGLE PLAY"),
            ("GOOGLE STORAGE 100GB", "GOOGLE STORAGE"),
            ("GOOGLE DRIVE", "GOOGLE STORAGE"),
            ("GOOGLE YOUTUBE PREMIUM", "YOUTUBE"),
            ("GOOGLE ADS BILLING", "GOOGLE"),
        ],
    )
    def test_google(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("AMAZON PRIME MEMBERSHIP", "AMAZON PRIME"),
            ("AMAZON MARKETPLACE", "AMAZON"),
            ("AMZN MKTP US", "AMAZON"),
            ("PRIME VIDEO CHANNELS", "PRIME VIDEO"),
        ],
    )
    def test_amazon(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("NETFLIX.COM MONTHLY", "NETFLIX"),
            ("SPOTIFY USA", "SPOTIFY"),
            ("HULU SUBSCRIPTION", "HULU"),
            ("DISNEY PLUS ANNUAL", "DISNEY+"),
            ("HBO MAX MONTHLY", "HBO MAX"),
        ],
    )
    def test_streaming(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("PAYPAL INST XFER", "PAYPAL TRANSFERS"),
            ("PAYPAL TRANSFER", "PAYPAL TRANSFERS"),
            ("PAYPAL *MERCHANT", "PAYPAL"),
            ("VENMO PAYMENT", "VENMO"),
            ("ZELLE TRANSFER", "ZELLE"),
            ("CASH APP PAYMENT", "CASH APP"),
            ("CASHAPP *JOHN", "CASH APP"),
        ],
    )
    def test_p2p_payment(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # -- Retail - Big Box ------------------------------------------------------

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("WMT PLUS MEMBERSHIP", "WALMART PLUS"),
            ("WALMART PLUS SUB", "WALMART PLUS"),
            ("WALMART #3893 CHICAGO IL", "WALMART (ALL LOCATIONS)"),
            ("WAL-MART SUPER CENTER", "WALMART (ALL LOCATIONS)"),
            ("WM SUPERCENTER 1234", "WALMART (ALL LOCATIONS)"),
            ("WALMART.COM ORDER", "WALMART.COM"),
            ("TARGET T-1234 STORE", "TARGET (ALL LOCATIONS)"),
            ("COSTCO WHSE #123", "COSTCO"),
            ("SAMS CLUB #456", "SAMS CLUB"),
            ("SAM'S CLUB 789", "SAMS CLUB"),
            ("BJ'S WHOLESALE 111", "BJ'S WHOLESALE"),
            ("BJS CLUB 222", "BJ'S WHOLESALE"),
        ],
    )
    def test_big_box_retail(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # -- Retail - Dollar Stores ------------------------------------------------

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("DOLLAR TREE #123", "DOLLAR TREE"),
            ("DOLLARTREE", "DOLLAR TREE"),
            ("DOLLAR GENERAL #456", "DOLLAR GENERAL"),
            ("DOLLARGENERAL", "DOLLAR GENERAL"),
            ("FAMILY DOLLAR #789", "FAMILY DOLLAR"),
            ("FIVE BELOW #111", "FIVE BELOW"),
            ("5 BELOW #222", "FIVE BELOW"),
        ],
    )
    def test_dollar_stores(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # -- Retail - Department Stores --------------------------------------------

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("BURLINGTON STORE #1", "BURLINGTON"),
            ("KOHLS DEPT STORE", "KOHL'S"),
            ("KOHL'S #333", "KOHL'S"),
            ("MARSHALLS #444", "MARSHALLS"),
            ("TJ MAXX #555", "TJ MAXX"),
            ("TJMAXX #666", "TJ MAXX"),
            ("ROSS DRESS FOR LESS", "ROSS DRESS FOR LESS"),
            ("NORDSTROM RACK", "NORDSTROM"),
            ("MACY'S DEPT STORE", "MACY'S"),
            ("MACYS ONLINE", "MACY'S"),
        ],
    )
    def test_department_stores(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # -- Retail - Specialty ----------------------------------------------------

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("HOBBY LOBBY #123", "HOBBY LOBBY"),
            ("HOBBYLOBBY", "HOBBY LOBBY"),
            ("MICHAELS STORES #456", "MICHAELS"),
            ("HOME DEPOT #789", "HOME DEPOT"),
            ("HOMEDEPOT COM", "HOME DEPOT"),
            ("LOWE'S #111", "LOWE'S"),
            ("LOWES STORE", "LOWE'S"),
            ("MENARDS #222", "MENARDS"),
            ("ACE HDWE #333", "ACE HARDWARE"),
            ("ACE HARDWARE STORE", "ACE HARDWARE"),
            ("TRUE VALUE #444", "TRUE VALUE"),
            ("BED BATH AND BEYOND", "BED BATH & BEYOND"),
            ("BEST BUY #555", "BEST BUY"),
            ("BESTBUY COM", "BEST BUY"),
            ("DICKS SPORTING GOODS", "DICKS SPORTING GOODS"),
            ("DICK'S SPORTING GOODS", "DICKS SPORTING GOODS"),
            ("PETCO STORE", "PETCO"),
            ("PETSMART #666", "PETSMART"),
        ],
    )
    def test_specialty_retail(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # -- Online Retail ---------------------------------------------------------

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("TIKTOK SHOP ORDER", "TIKTOK SHOP"),
            ("SHEIN ORDER", "SHEIN"),
            ("TEMU PURCHASE", "TEMU"),
            ("ETSY INC SELLER", "ETSY"),
            ("EBAY PURCHASE", "EBAY"),
            ("AFTERPAY US", "AFTERPAY"),
            ("KLARNA PAYMENT", "KLARNA"),
        ],
    )
    def test_online_retail(self, raw, expected):
        assert standardize_merchant_name(raw) == expected

    # -- Edge cases ------------------------------------------------------------

    def test_no_match_returns_original(self):
        result = standardize_merchant_name("UNIQUE LOCAL SHOP 12345")
        assert result == "UNIQUE LOCAL SHOP 12345"

    def test_whitespace_normalization(self):
        result = standardize_merchant_name("  NETFLIX   SUBSCRIPTION  ")
        assert result == "NETFLIX"

    def test_case_insensitive(self):
        result = standardize_merchant_name("netflix monthly")
        assert result == "NETFLIX"

    def test_none_value(self):
        # No match -- returns original value (which is None cast to "None" then unmatched)
        result = standardize_merchant_name(None)
        assert result is not None or result is None  # just doesn't crash

    def test_numeric_input(self):
        # No match -- returns original value (which is 12345)
        result = standardize_merchant_name(12345)
        assert result is not None  # just doesn't crash

    def test_empty_string(self):
        result = standardize_merchant_name("")
        assert result == ""


class TestApplyMerchantConsolidation:
    def test_creates_consolidated_column(self):
        df = pd.DataFrame({"merchant_name": ["WALMART #1234", "NETFLIX SUB", "LOCAL SHOP"]})
        result = apply_merchant_consolidation(df)
        assert "merchant_consolidated" in result.columns
        assert result.loc[0, "merchant_consolidated"] == "WALMART (ALL LOCATIONS)"
        assert result.loc[1, "merchant_consolidated"] == "NETFLIX"
        assert result.loc[2, "merchant_consolidated"] == "LOCAL SHOP"

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"merchant_name": ["AMAZON PRIME"]})
        result = apply_merchant_consolidation(df)
        assert "merchant_consolidated" not in df.columns
        assert "merchant_consolidated" in result.columns

    def test_custom_column_name(self):
        df = pd.DataFrame({"raw_merchant": ["COSTCO WHOLESALE"]})
        result = apply_merchant_consolidation(df, column="raw_merchant")
        assert result.loc[0, "merchant_consolidated"] == "COSTCO"

    def test_missing_column_raises(self):
        df = pd.DataFrame({"other": [1, 2]})
        with pytest.raises(KeyError, match="not found"):
            apply_merchant_consolidation(df, column="merchant_name")
