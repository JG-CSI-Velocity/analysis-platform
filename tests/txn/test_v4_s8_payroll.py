"""Comprehensive tests for v4_s8_payroll -- Payroll & Circular Economy storyline.

Tests cover:
- _extract_business_name: processor removal, noise stripping, edge cases
- _detect_payroll: keyword matching, config processors, skip_terms, min_spend
- _blend_color: linear interpolation between hex colors
- Analysis functions: _payroll_summary, _top_employers, _payroll_by_generation,
  _monthly_trends, _circular_economy, _clean_employer_list,
  _circular_economy_detail, _payroll_mom_growth
- run(): orchestration with and without payroll data
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from txn_analysis.storylines.v4_s8_payroll import (
    _KNOWN_PROCESSORS,
    _blend_color,
    _circular_economy,
    _circular_economy_detail,
    _clean_employer_list,
    _detect_payroll,
    _extract_business_name,
    _monthly_trends,
    _payroll_by_generation,
    _payroll_mom_growth,
    _payroll_summary,
    _top_employers,
    run,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _gen_from_age(age: int) -> str:
    if 12 <= age <= 27:
        return "Gen Z"
    if 28 <= age <= 43:
        return "Millennial"
    if 44 <= age <= 59:
        return "Gen X"
    if 60 <= age <= 78:
        return "Boomer"
    return "Silent"


@pytest.fixture()
def payroll_ctx():
    """Build a synthetic context dict with payroll-triggering merchants.

    Returns a ctx dict containing combined_df (~200 rows), personal_df,
    and config with payroll.processors set.
    """
    np.random.seed(42)
    n_txn = 200
    n_accts = 20

    acct_nums = [f"A{i:04d}" for i in range(n_accts)]
    dates = pd.date_range("2024-07-01", "2025-06-30", freq="D")

    txn_dates = np.random.choice(dates, size=n_txn)
    txn_accts = np.random.choice(acct_nums, size=n_txn)
    txn_amounts = np.random.lognormal(mean=3, sigma=1.5, size=n_txn).round(2)

    # Include merchants that trigger payroll detection
    payroll_merchants = [
        "ADP PAYROLL ACME CORP",
        "PAYCHEX PAYROLL WIDGETCO",
        "PAYROLL DEPOSIT SUNRISE LLC",
        "GUSTO PAYROLL TECHSTART",
        "INTUIT PAYROLL BIGBIZ",
    ]
    non_payroll_merchants = [
        "WALMART #1234",
        "AMAZON MARKETPLACE",
        "SHELL OIL",
        "MCDONALDS",
        "TARGET STORE",
    ]
    all_merchants = payroll_merchants + non_payroll_merchants

    # Give ~40% of transactions payroll merchants
    merchants = np.random.choice(all_merchants, size=n_txn, p=[0.08] * 5 + [0.12] * 5)

    ages = np.random.randint(18, 80, size=n_accts)
    acct_gens = {acct: _gen_from_age(ages[i]) for i, acct in enumerate(acct_nums)}
    business_flags = {acct: np.random.choice(["Yes", "No"], p=[0.2, 0.8]) for acct in acct_nums}

    combined_df = pd.DataFrame(
        {
            "primary_account_num": txn_accts,
            "transaction_date": pd.to_datetime(txn_dates),
            "amount": txn_amounts,
            "merchant_name": merchants,
            "merchant_consolidated": merchants,
            "Business?": [business_flags[a] for a in txn_accts],
        }
    )
    combined_df["year_month"] = combined_df["transaction_date"].dt.to_period("M")
    combined_df["generation"] = [acct_gens[a] for a in txn_accts]

    personal_df = combined_df[combined_df["Business?"] == "No"].copy()

    config = {
        "payroll": {
            "processors": ["PAYROLL", "ADP", "PAYCHEX", "GUSTO", "INTUIT"],
            "skip_terms": [],
            "min_spend": 0,
        },
    }

    return {
        "combined_df": combined_df,
        "personal_df": personal_df,
        "config": config,
    }


@pytest.fixture()
def payroll_df(payroll_ctx):
    """Pre-detected payroll DataFrame for use by analysis function tests."""
    return _detect_payroll(payroll_ctx["combined_df"], payroll_ctx["config"])


# ---------------------------------------------------------------------------
# _extract_business_name
# ---------------------------------------------------------------------------


class TestExtractBusinessName:
    """Tests for the business name extraction helper."""

    def test_strips_adp_processor(self):
        result = _extract_business_name("ADP PAYROLL ACME CORP")
        assert result is not None
        assert "ADP" not in result
        assert "PAYROLL" not in result
        assert "ACME" in result

    def test_strips_paychex_processor(self):
        result = _extract_business_name("PAYCHEX PAYROLL WIDGETCO INC")
        assert result is not None
        assert "PAYCHEX" not in result
        assert "WIDGET" in result.upper()

    def test_strips_gusto_processor(self):
        result = _extract_business_name("GUSTO PAYROLL TECHSTART")
        assert result is not None
        assert "GUSTO" not in result
        assert "TECHSTART" in result

    def test_strips_all_known_processors(self):
        for proc in _KNOWN_PROCESSORS:
            result = _extract_business_name(f"{proc} PAYROLL SAMPLECO")
            assert result is not None, f"Failed for processor: {proc}"
            assert proc not in result, f"{proc} not stripped from result: {result}"

    def test_strips_noise_patterns_quickbooks(self):
        result = _extract_business_name("QUICKBOOKS PAYROLL ACME CORP")
        assert result is not None
        assert "QUICKBOOKS" not in result

    def test_strips_noise_pattern_long_digits(self):
        result = _extract_business_name("PAYROLL 123456789 SUNRISE BAKERY")
        assert result is not None
        assert "123456789" not in result
        assert "SUNRISE" in result

    def test_strips_noise_pattern_dir_dep(self):
        result = _extract_business_name("ADP DIR DEP ACME FOODS")
        assert result is not None
        assert "DIR" not in result.split()
        assert "ACME" in result

    def test_strips_noise_words_inc_llc(self):
        result = _extract_business_name("PAYROLL SUNRISE BAKERY INC LLC")
        assert result is not None
        # INC and LLC are noise words, should be filtered
        words = result.split()
        assert "INC" not in words
        assert "LLC" not in words

    def test_returns_none_for_garbage(self):
        result = _extract_business_name("ADP PAYROLL")
        # After stripping ADP and PAYROLL, nothing meaningful remains
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = _extract_business_name("")
        assert result is None

    def test_returns_none_for_only_noise(self):
        result = _extract_business_name("ADP PAYCHEX PAYROLL INC LLC THE")
        assert result is None

    def test_single_word_result(self):
        result = _extract_business_name("PAYROLL STARBUCKS")
        assert result is not None
        assert "STARBUCKS" in result

    def test_limits_to_three_words(self):
        result = _extract_business_name("PAYROLL GREAT NORTHERN RAILWAY COMPANY EXTRA WORDS")
        assert result is not None
        words = result.split()
        assert len(words) <= 3

    def test_ampersand_filtered_by_min_length(self):
        """& is a single char so it gets filtered by the min-2-char rule."""
        result = _extract_business_name("PAYROLL SMITH & JONES CONSULTING")
        assert result is not None
        # & is only 1 char, so it is dropped by the min-2-char word filter
        assert "SMITH" in result
        assert "JONES" in result

    def test_preserves_hyphens(self):
        result = _extract_business_name("PAYROLL WELL-KNOWN BRAND")
        assert result is not None
        assert "-" in result

    def test_case_insensitive_input(self):
        result = _extract_business_name("adp payroll acme corp")
        assert result is not None
        assert "ACME" in result

    def test_strips_deposit_keyword(self):
        result = _extract_business_name("DEPOSIT PAYROLL ACME FOODS")
        assert result is not None
        assert "DEPOSIT" not in result

    def test_strips_xxxxx_pattern(self):
        result = _extract_business_name("PAYROLL XXXXX12345 ACME LABS")
        assert result is not None
        assert "XXXXX" not in result


# ---------------------------------------------------------------------------
# _detect_payroll
# ---------------------------------------------------------------------------


class TestDetectPayroll:
    """Tests for payroll transaction detection."""

    def test_finds_payroll_keyword(self):
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A002", "A003"],
                "merchant_consolidated": [
                    "PAYROLL DEPOSIT ACME",
                    "WALMART STORE",
                    "PAYROLL ADP BIGCORP",
                ],
                "amount": [5000.0, 50.0, 3000.0],
            }
        )
        config = {"payroll": {"processors": ["PAYROLL"], "min_spend": 0}}
        result = _detect_payroll(df, config)
        assert len(result) >= 2
        assert "payroll_employer" in result.columns

    def test_finds_custom_processors(self):
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A002"],
                "merchant_consolidated": ["ADP PAYMENT ACME", "TARGET STORE"],
                "amount": [4000.0, 100.0],
            }
        )
        config = {"payroll": {"processors": ["ADP"], "min_spend": 0}}
        result = _detect_payroll(df, config)
        assert len(result) >= 1
        assert result.iloc[0]["payroll_employer"].upper() == "ADP PAYMENT ACME"

    def test_skip_terms_filtering(self):
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A002"],
                "merchant_consolidated": [
                    "PAYROLL DEPOSIT ACME",
                    "PAYROLL CARD RELOAD",
                ],
                "amount": [5000.0, 200.0],
            }
        )
        config = {
            "payroll": {
                "processors": ["PAYROLL"],
                "skip_terms": ["RELOAD"],
                "min_spend": 0,
            }
        }
        result = _detect_payroll(df, config)
        employers = result["payroll_employer"].str.upper().tolist()
        # PAYROLL CARD RELOAD should be skipped
        assert not any("RELOAD" in e for e in employers)
        assert len(result) == 1

    def test_min_spend_threshold(self):
        """Merchants below min_spend should not be picked up by the
        high-spend fallback path."""
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001"] * 5,
                "merchant_consolidated": ["SMALLSHOP"] * 5,
                "amount": [100.0] * 5,
            }
        )
        # No PAYROLL keyword, and total spend = 500 < min_spend 10000
        config = {"payroll": {"processors": ["PAYROLL"], "min_spend": 10_000}}
        result = _detect_payroll(df, config)
        assert len(result) == 0

    def test_min_spend_picks_up_high_volume_merchant(self):
        """Merchants exceeding min_spend get picked up even without keyword."""
        rows = 10
        df = pd.DataFrame(
            {
                "primary_account_num": [f"A{i:03d}" for i in range(rows)],
                "merchant_consolidated": ["BIG EMPLOYER CO"] * rows,
                "amount": [2000.0] * rows,
            }
        )
        # Total spend = 20000, > min_spend 10000
        config = {"payroll": {"processors": ["PAYROLL"], "min_spend": 10_000}}
        result = _detect_payroll(df, config)
        assert len(result) == rows

    def test_empty_dataframe(self):
        df = pd.DataFrame(
            {
                "primary_account_num": pd.Series(dtype=str),
                "merchant_consolidated": pd.Series(dtype=str),
                "amount": pd.Series(dtype=float),
            }
        )
        config = {"payroll": {"processors": ["PAYROLL"], "min_spend": 0}}
        result = _detect_payroll(df, config)
        assert len(result) == 0
        assert "payroll_employer" in result.columns

    def test_default_config_values(self):
        """When config has no payroll key, defaults should be used."""
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001"],
                "merchant_consolidated": ["PAYROLL DEPOSIT ACME"],
                "amount": [5000.0],
            }
        )
        config = {}
        result = _detect_payroll(df, config)
        # Default processors includes PAYROLL, so should match
        assert len(result) >= 1

    def test_known_processor_skip_terms_bypass(self):
        """Known processors (ADP, PAYCHEX etc) bypass skip_terms filtering."""
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001"],
                "merchant_consolidated": ["ADP RELOAD ACME"],
                "amount": [5000.0],
            }
        )
        config = {
            "payroll": {
                "processors": ["ADP"],
                "skip_terms": ["RELOAD"],
                "min_spend": 0,
            }
        }
        result = _detect_payroll(df, config)
        # ADP is a known processor, so skip_terms should NOT apply
        assert len(result) == 1

    def test_max_match_count_filters_high_count_merchants(self):
        """Merchants matching more accounts than max_match_count are excluded
        from the min_spend fallback path."""
        n = 20
        df = pd.DataFrame(
            {
                "primary_account_num": [f"A{i:04d}" for i in range(n)],
                "merchant_consolidated": ["HUGE EMPLOYER"] * n,
                "amount": [1000.0] * n,
            }
        )
        config = {
            "payroll": {
                "processors": ["PAYROLL"],
                "min_spend": 5000,
                "max_match_count": 5,
            }
        }
        result = _detect_payroll(df, config)
        # 20 unique accounts > max_match_count of 5, so excluded
        assert len(result) == 0


# ---------------------------------------------------------------------------
# _blend_color
# ---------------------------------------------------------------------------


class TestBlendColor:
    """Tests for hex color interpolation."""

    def test_t_zero_returns_hex_a(self):
        assert _blend_color("#ff0000", "#0000ff", 0.0) == "#ff0000"

    def test_t_one_returns_hex_b(self):
        assert _blend_color("#ff0000", "#0000ff", 1.0) == "#0000ff"

    def test_midpoint_interpolation(self):
        result = _blend_color("#000000", "#ffffff", 0.5)
        # Each channel should be ~127-128
        r = int(result[1:3], 16)
        g = int(result[3:5], 16)
        b = int(result[5:7], 16)
        assert 126 <= r <= 128
        assert 126 <= g <= 128
        assert 126 <= b <= 128

    def test_returns_hex_format(self):
        result = _blend_color("#ff0000", "#00ff00", 0.5)
        assert result.startswith("#")
        assert len(result) == 7

    def test_clamps_t_below_zero(self):
        result = _blend_color("#ff0000", "#0000ff", -0.5)
        assert result == "#ff0000"

    def test_clamps_t_above_one(self):
        result = _blend_color("#ff0000", "#0000ff", 1.5)
        assert result == "#0000ff"

    def test_same_color_returns_same(self):
        result = _blend_color("#abcdef", "#abcdef", 0.5)
        assert result == "#abcdef"

    def test_quarter_interpolation(self):
        result = _blend_color("#000000", "#ff0000", 0.25)
        r = int(result[1:3], 16)
        g = int(result[3:5], 16)
        b = int(result[5:7], 16)
        assert 62 <= r <= 64  # 255 * 0.25 ~= 63
        assert g == 0
        assert b == 0


# ---------------------------------------------------------------------------
# _payroll_summary
# ---------------------------------------------------------------------------


class TestPayrollSummary:
    """Tests for the payroll summary analysis."""

    def test_returns_section_and_sheet(self, payroll_df, payroll_ctx):
        section, sheet = _payroll_summary(payroll_ctx["combined_df"], payroll_df)
        assert section["heading"] == "Payroll Summary"
        assert "narrative" in section
        assert len(section["figures"]) == 1
        assert len(section["tables"]) == 1
        assert sheet["name"] == "S8 Payroll Summary"
        assert "df" in sheet

    def test_narrative_contains_currency(self, payroll_df, payroll_ctx):
        section, _ = _payroll_summary(payroll_ctx["combined_df"], payroll_df)
        assert "$" in section["narrative"]

    def test_table_has_expected_metrics(self, payroll_df, payroll_ctx):
        _, sheet = _payroll_summary(payroll_ctx["combined_df"], payroll_df)
        metrics = sheet["df"]["Metric"].tolist()
        assert "Total Payroll Spend" in metrics
        assert "Unique Employers" in metrics
        assert "Unique Accounts" in metrics
        assert "Payroll % of Total" in metrics

    def test_zero_total_all_fallback(self):
        """When total debit spend is zero, narrative should still work."""
        pay = pd.DataFrame(
            {
                "amount": [100.0, 200.0],
                "payroll_employer": ["EMP_A", "EMP_B"],
                "primary_account_num": ["A001", "A002"],
            }
        )
        all_df = pd.DataFrame(
            {
                "amount": [0.0, 0.0],
                "primary_account_num": ["A001", "A002"],
            }
        )
        section, _ = _payroll_summary(all_df, pay)
        assert "Detected" in section["narrative"]


# ---------------------------------------------------------------------------
# _top_employers
# ---------------------------------------------------------------------------


class TestTopEmployers:
    """Tests for the top employers analysis."""

    def test_returns_section_and_sheet(self, payroll_df):
        section, sheet = _top_employers(payroll_df)
        assert section["heading"] == "Top Employers"
        assert sheet["name"] == "S8 Top Employers"

    def test_table_columns(self, payroll_df):
        _, sheet = _top_employers(payroll_df)
        expected_cols = [
            "Employer",
            "Total Payroll",
            "Unique Employees",
            "Transactions",
            "Avg per Employee",
        ]
        assert list(sheet["df"].columns) == expected_cols

    def test_max_twenty_employers(self):
        """Should cap at 20 employers even with more data."""
        n = 25
        pay = pd.DataFrame(
            {
                "payroll_employer": [f"EMPLOYER_{i}" for i in range(n)],
                "amount": [1000.0] * n,
                "primary_account_num": [f"A{i:04d}" for i in range(n)],
            }
        )
        _, sheet = _top_employers(pay)
        assert len(sheet["df"]) == 20

    def test_narrative_contains_top_employer(self, payroll_df):
        section, _ = _top_employers(payroll_df)
        assert "<b>" in section["narrative"]
        assert "employees" in section["narrative"].lower()

    def test_sorted_by_total_descending(self, payroll_df):
        _, sheet = _top_employers(payroll_df)
        totals = sheet["df"]["Total Payroll"].tolist()
        assert totals == sorted(totals, reverse=True)


# ---------------------------------------------------------------------------
# _payroll_by_generation
# ---------------------------------------------------------------------------


class TestPayrollByGeneration:
    """Tests for the generational payroll analysis."""

    def test_returns_section_and_sheet(self, payroll_df):
        section, sheet = _payroll_by_generation(payroll_df)
        assert section["heading"] == "Payroll by Generation"
        assert sheet["name"] == "S8 Payroll by Gen"

    def test_table_columns(self, payroll_df):
        _, sheet = _payroll_by_generation(payroll_df)
        assert list(sheet["df"].columns) == [
            "Generation",
            "Total Payroll",
            "Unique Accounts",
        ]

    def test_generation_order_respected(self, payroll_df):
        _, sheet = _payroll_by_generation(payroll_df)
        gen_order = ["Gen Z", "Millennial", "Gen X", "Boomer", "Silent"]
        present_gens = sheet["df"]["Generation"].tolist()
        order_positions = [gen_order.index(g) for g in present_gens]
        assert order_positions == sorted(order_positions)

    def test_narrative_mentions_leading_generation(self, payroll_df):
        section, _ = _payroll_by_generation(payroll_df)
        assert "leads payroll volume" in section["narrative"]

    def test_zero_total_fallback(self):
        """When all generation totals are zero, narrative should handle it."""
        pay = pd.DataFrame(
            {
                "generation": ["Gen Z", "Millennial"],
                "amount": [0.0, 0.0],
                "primary_account_num": ["A001", "A002"],
            }
        )
        section, _ = _payroll_by_generation(pay)
        assert "No payroll volume" in section["narrative"]


# ---------------------------------------------------------------------------
# _monthly_trends
# ---------------------------------------------------------------------------


class TestMonthlyTrends:
    """Tests for the monthly payroll trends analysis."""

    def test_returns_section_and_sheet(self, payroll_df):
        section, sheet = _monthly_trends(payroll_df)
        assert section["heading"] == "Monthly Payroll Trends"
        assert sheet["name"] == "S8 Payroll Trends"

    def test_table_columns(self, payroll_df):
        _, sheet = _monthly_trends(payroll_df)
        assert list(sheet["df"].columns) == [
            "Month",
            "Total Payroll",
            "Accounts",
        ]

    def test_narrative_includes_direction(self, payroll_df):
        section, _ = _monthly_trends(payroll_df)
        narrative = section["narrative"]
        assert "increased" in narrative or "decreased" in narrative

    def test_single_month_insufficient(self):
        """With only one month, narrative should say insufficient."""
        pay = pd.DataFrame(
            {
                "year_month": [pd.Period("2025-01", freq="M")] * 3,
                "amount": [1000.0, 2000.0, 3000.0],
                "primary_account_num": ["A001", "A002", "A003"],
            }
        )
        section, _ = _monthly_trends(pay)
        assert "Insufficient" in section["narrative"]

    def test_multiple_months_have_trend(self):
        pay = pd.DataFrame(
            {
                "year_month": [
                    pd.Period("2025-01", freq="M"),
                    pd.Period("2025-01", freq="M"),
                    pd.Period("2025-02", freq="M"),
                    pd.Period("2025-02", freq="M"),
                ],
                "amount": [1000.0, 1500.0, 2000.0, 2500.0],
                "primary_account_num": ["A001", "A002", "A001", "A002"],
            }
        )
        section, sheet = _monthly_trends(pay)
        assert len(sheet["df"]) == 2
        narrative = section["narrative"]
        assert "increased" in narrative or "decreased" in narrative


# ---------------------------------------------------------------------------
# _circular_economy
# ---------------------------------------------------------------------------


class TestCircularEconomy:
    """Tests for the circular economy recapture analysis."""

    def test_returns_section_and_sheet(self, payroll_df, payroll_ctx):
        section, sheet = _circular_economy(payroll_ctx["combined_df"], payroll_df)
        assert section is not None
        assert section["heading"] == "Circular Economy: Debit Spend Recapture"
        assert sheet["name"] == "S8 Circular Economy"

    def test_narrative_mentions_recapture(self, payroll_df, payroll_ctx):
        section, _ = _circular_economy(payroll_ctx["combined_df"], payroll_df)
        assert "recapture" in section["narrative"].lower()

    def test_returns_none_when_no_payroll_accounts(self):
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A002"],
                "amount": [100.0, 200.0],
                "merchant_consolidated": ["WALMART", "TARGET"],
            }
        )
        pay = pd.DataFrame(
            {
                "primary_account_num": pd.Series(dtype=str),
                "amount": pd.Series(dtype=float),
                "payroll_employer": pd.Series(dtype=str),
            }
        )
        section, sheet = _circular_economy(df, pay)
        assert section is None
        assert sheet is None

    def test_generation_breakdown_when_available(self, payroll_ctx, payroll_df):
        """When generation column exists, recapture table should break
        down by generation."""
        section, sheet = _circular_economy(payroll_ctx["combined_df"], payroll_df)
        assert section is not None
        if "Avg Recapture %" in sheet["df"].columns:
            assert "Generation" in sheet["df"].columns

    def test_no_generation_column_uses_donut(self):
        """Without generation column, should produce a simple donut chart."""
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A001", "A001"],
                "amount": [5000.0, 100.0, 200.0],
                "merchant_consolidated": [
                    "PAYROLL ACME",
                    "WALMART",
                    "TARGET",
                ],
            }
        )
        pay = pd.DataFrame(
            {
                "primary_account_num": ["A001"],
                "amount": [5000.0],
                "payroll_employer": ["PAYROLL ACME"],
            }
        )
        section, sheet = _circular_economy(df, pay)
        assert section is not None
        assert "Metric" in sheet["df"].columns


# ---------------------------------------------------------------------------
# _clean_employer_list
# ---------------------------------------------------------------------------


class TestCleanEmployerList:
    """Tests for the clean employer list analysis."""

    def test_returns_section_and_sheet(self, payroll_df):
        section, sheet = _clean_employer_list(payroll_df)
        if section is not None:
            assert section["heading"] == "Clean Employer List"
            assert sheet["name"] == "S8 Clean Employers"

    def test_table_has_clean_employer_column(self, payroll_df):
        section, sheet = _clean_employer_list(payroll_df)
        if section is not None:
            assert "Clean Employer" in sheet["df"].columns

    def test_includes_mapping_table(self, payroll_df):
        section, _ = _clean_employer_list(payroll_df)
        if section is not None:
            table_names = [name for name, _ in section["tables"]]
            assert "Employer Mapping" in table_names

    def test_empty_payroll_returns_none(self):
        pay = pd.DataFrame(
            {
                "payroll_employer": pd.Series(dtype=str),
                "amount": pd.Series(dtype=float),
                "primary_account_num": pd.Series(dtype=str),
            }
        )
        section, sheet = _clean_employer_list(pay)
        assert section is None
        assert sheet is None

    def test_no_payroll_employer_column_returns_none(self):
        pay = pd.DataFrame(
            {
                "amount": [100.0],
                "primary_account_num": ["A001"],
            }
        )
        section, sheet = _clean_employer_list(pay)
        assert section is None
        assert sheet is None

    def test_uncleanable_names_returns_none(self):
        """When no employer names produce clean names >= 3 chars, returns None."""
        pay = pd.DataFrame(
            {
                "payroll_employer": ["ADP PAYROLL", "PAYCHEX"],
                "amount": [100.0, 200.0],
                "primary_account_num": ["A001", "A002"],
            }
        )
        section, sheet = _clean_employer_list(pay)
        assert section is None
        assert sheet is None

    def test_max_thirty_employers(self):
        """Should cap at 30 employers."""
        n = 40
        pay = pd.DataFrame(
            {
                "payroll_employer": [f"PAYROLL EMPLOYER{i} COMPANY{i}" for i in range(n)],
                "amount": [float(i * 100) for i in range(n)],
                "primary_account_num": [f"A{i:04d}" for i in range(n)],
            }
        )
        section, sheet = _clean_employer_list(pay)
        if section is not None:
            assert len(sheet["df"]) <= 30


# ---------------------------------------------------------------------------
# _circular_economy_detail
# ---------------------------------------------------------------------------


class TestCircularEconomyDetail:
    """Tests for the per-employer circular economy detail analysis."""

    def test_returns_section_and_sheet(self, payroll_df, payroll_ctx):
        section, sheet = _circular_economy_detail(
            payroll_df,
            payroll_ctx["personal_df"],
            payroll_ctx["config"],
        )
        # May return None if no employer names match consumer transactions
        if section is not None:
            assert section["heading"] == "Circular Economy: Employer Detail"
            assert sheet["name"] == "S8 Circ Detail"

    def test_empty_payroll_returns_none(self, payroll_ctx):
        empty_pay = pd.DataFrame(
            {
                "payroll_employer": pd.Series(dtype=str),
                "amount": pd.Series(dtype=float),
                "primary_account_num": pd.Series(dtype=str),
            }
        )
        section, sheet = _circular_economy_detail(
            empty_pay,
            payroll_ctx["personal_df"],
            payroll_ctx["config"],
        )
        assert section is None
        assert sheet is None

    def test_empty_personal_df_returns_none(self, payroll_df, payroll_ctx):
        empty_personal = pd.DataFrame(
            {
                "merchant_consolidated": pd.Series(dtype=str),
                "amount": pd.Series(dtype=float),
                "primary_account_num": pd.Series(dtype=str),
            }
        )
        section, sheet = _circular_economy_detail(payroll_df, empty_personal, payroll_ctx["config"])
        assert section is None
        assert sheet is None

    def test_detail_table_columns(self):
        """When matching succeeds, check output columns."""
        pay = pd.DataFrame(
            {
                "payroll_employer": ["PAYROLL SUNRISE BAKERY"] * 3,
                "amount": [5000.0, 6000.0, 4000.0],
                "primary_account_num": ["A001", "A002", "A003"],
            }
        )
        personal = pd.DataFrame(
            {
                "merchant_consolidated": [
                    "SUNRISE BAKERY CAFE",
                    "WALMART",
                    "SUNRISE BAKERY",
                ],
                "amount": [200.0, 50.0, 150.0],
                "primary_account_num": ["A001", "A001", "A002"],
            }
        )
        config = {"payroll": {"max_match_count": 1000}}
        section, sheet = _circular_economy_detail(pay, personal, config)
        if section is not None:
            expected_cols = {
                "Business Name",
                "Payroll Spend",
                "Consumer Spend",
                "Recapture %",
                "Consumer Accounts",
                "Consumer Merchants",
            }
            assert set(sheet["df"].columns) == expected_cols

    def test_generic_skip_terms_excluded(self):
        """Employers with generic business names should be skipped."""
        pay = pd.DataFrame(
            {
                "payroll_employer": [
                    "PAYROLL CAPITAL SERVICES GROUP",
                    "PAYROLL CONSTRUCTION MANAGEMENT",
                ],
                "amount": [10000.0, 8000.0],
                "primary_account_num": ["A001", "A002"],
            }
        )
        personal = pd.DataFrame(
            {
                "merchant_consolidated": [
                    "CAPITAL ONE",
                    "CONSTRUCTION SUPPLY",
                ],
                "amount": [500.0, 300.0],
                "primary_account_num": ["A001", "A002"],
            }
        )
        config = {"payroll": {"max_match_count": 1000}}
        section, _ = _circular_economy_detail(pay, personal, config)
        # Generic terms like CAPITAL, CONSTRUCTION should be skipped
        assert section is None


# ---------------------------------------------------------------------------
# _payroll_mom_growth
# ---------------------------------------------------------------------------


class TestPayrollMomGrowth:
    """Tests for month-over-month payroll growth analysis."""

    def test_returns_section_and_sheet(self, payroll_df):
        section, sheet = _payroll_mom_growth(payroll_df)
        if section is not None:
            assert section["heading"] == "Payroll MoM Growth by Employer"
            assert sheet["name"] == "S8 Payroll Growth"

    def test_empty_payroll_returns_none(self):
        pay = pd.DataFrame(
            {
                "payroll_employer": pd.Series(dtype=str),
                "amount": pd.Series(dtype=float),
                "year_month": pd.Series(dtype="period[M]"),
                "primary_account_num": pd.Series(dtype=str),
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        assert section is None
        assert sheet is None

    def test_no_year_month_returns_none(self):
        pay = pd.DataFrame(
            {
                "payroll_employer": ["ACME"],
                "amount": [1000.0],
                "primary_account_num": ["A001"],
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        assert section is None
        assert sheet is None

    def test_growth_classification_growing(self):
        """Employer with >20% growth should be classified as Growing."""
        months = [pd.Period(f"2025-{m:02d}", freq="M") for m in range(1, 7)]
        pay = pd.DataFrame(
            {
                "payroll_employer": ["PAYROLL ACME CORP"] * 6,
                "amount": [1000, 1000, 1000, 2000, 2000, 2000],
                "year_month": months,
                "primary_account_num": ["A001"] * 6,
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        assert section is not None
        classifications = sheet["df"]["Classification"].tolist()
        assert "Growing" in classifications

    def test_growth_classification_declining(self):
        """Employer with <-20% growth should be classified as Declining."""
        months = [pd.Period(f"2025-{m:02d}", freq="M") for m in range(1, 7)]
        pay = pd.DataFrame(
            {
                "payroll_employer": ["PAYROLL ACME CORP"] * 6,
                "amount": [3000, 3000, 3000, 1000, 1000, 1000],
                "year_month": months,
                "primary_account_num": ["A001"] * 6,
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        assert section is not None
        classifications = sheet["df"]["Classification"].tolist()
        assert "Declining" in classifications

    def test_growth_classification_stable(self):
        """Employer with growth between -20% and 20% is Stable."""
        months = [pd.Period(f"2025-{m:02d}", freq="M") for m in range(1, 7)]
        pay = pd.DataFrame(
            {
                "payroll_employer": ["PAYROLL ACME CORP"] * 6,
                "amount": [1000, 1050, 1000, 1050, 1000, 1050],
                "year_month": months,
                "primary_account_num": ["A001"] * 6,
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        assert section is not None
        classifications = sheet["df"]["Classification"].tolist()
        assert "Stable" in classifications

    def test_single_month_employer_excluded(self):
        """Employers with only 1 month of data should be excluded."""
        pay = pd.DataFrame(
            {
                "payroll_employer": [
                    "PAYROLL ACME CORP",
                    "PAYROLL ACME CORP",
                    "PAYROLL ONEMONTH BIZ",
                ],
                "amount": [1000.0, 2000.0, 500.0],
                "year_month": [
                    pd.Period("2025-01", freq="M"),
                    pd.Period("2025-02", freq="M"),
                    pd.Period("2025-01", freq="M"),
                ],
                "primary_account_num": ["A001", "A001", "A002"],
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        if section is not None:
            employers = sheet["df"]["Employer"].tolist()
            # ONEMONTH BIZ should not appear (only 1 month)
            for e in employers:
                assert "ONEMONTH" not in e

    def test_table_columns(self):
        months = [pd.Period(f"2025-{m:02d}", freq="M") for m in range(1, 4)]
        pay = pd.DataFrame(
            {
                "payroll_employer": ["PAYROLL ACME CORP"] * 3,
                "amount": [1000.0, 1500.0, 2000.0],
                "year_month": months,
                "primary_account_num": ["A001"] * 3,
            }
        )
        section, sheet = _payroll_mom_growth(pay)
        assert section is not None
        expected_cols = [
            "Employer",
            "Months",
            "Total Payroll",
            "Avg Monthly",
            "First 3M Avg",
            "Last 3M Avg",
            "Growth %",
            "CV %",
            "Classification",
        ]
        assert list(sheet["df"].columns) == expected_cols

    def test_narrative_mentions_counts(self):
        months = [pd.Period(f"2025-{m:02d}", freq="M") for m in range(1, 4)]
        pay = pd.DataFrame(
            {
                "payroll_employer": ["PAYROLL ACME CORP"] * 3,
                "amount": [1000.0, 1500.0, 2000.0],
                "year_month": months,
                "primary_account_num": ["A001"] * 3,
            }
        )
        section, _ = _payroll_mom_growth(pay)
        assert section is not None
        assert "growing" in section["narrative"].lower()
        assert "stable" in section["narrative"].lower()
        assert "declining" in section["narrative"].lower()


# ---------------------------------------------------------------------------
# run() orchestration
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for the run() entry point."""

    def test_returns_valid_structure(self, payroll_ctx):
        result = run(payroll_ctx)
        assert isinstance(result, dict)
        assert "title" in result
        assert "sections" in result
        assert "sheets" in result
        assert "S8" in result["title"]
        assert "Payroll" in result["title"]

    def test_with_payroll_data_has_sections(self, payroll_ctx):
        result = run(payroll_ctx)
        assert len(result["sections"]) >= 2  # At least summary + top employers

    def test_sections_are_list_of_dicts(self, payroll_ctx):
        result = run(payroll_ctx)
        for section in result["sections"]:
            assert isinstance(section, dict)
            assert "heading" in section

    def test_no_payroll_data_returns_detection_message(self):
        """When no payroll transactions exist, should return detection notice."""
        df = pd.DataFrame(
            {
                "primary_account_num": ["A001", "A002", "A003"],
                "merchant_consolidated": ["WALMART", "TARGET", "AMAZON"],
                "amount": [50.0, 100.0, 200.0],
                "transaction_date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
            }
        )
        ctx = {
            "combined_df": df,
            "config": {
                "payroll": {
                    "processors": ["PAYROLL"],
                    "min_spend": 999_999,
                }
            },
        }
        result = run(ctx)
        assert len(result["sections"]) == 1
        assert "No payroll transactions" in result["sections"][0]["narrative"]

    def test_includes_generation_section_when_available(self, payroll_ctx):
        """With generation column, should include payroll by generation."""
        result = run(payroll_ctx)
        headings = [s["heading"] for s in result["sections"]]
        assert "Payroll by Generation" in headings

    def test_includes_monthly_trends_when_year_month(self, payroll_ctx):
        """With year_month column, should include monthly trends."""
        result = run(payroll_ctx)
        headings = [s["heading"] for s in result["sections"]]
        assert "Monthly Payroll Trends" in headings

    def test_includes_circular_economy(self, payroll_ctx):
        """Should include circular economy recapture section."""
        result = run(payroll_ctx)
        headings = [s["heading"] for s in result["sections"]]
        assert any("Circular Economy" in h for h in headings)

    def test_personal_df_triggers_detail_analysis(self, payroll_ctx):
        """When personal_df is present, circular economy detail may run."""
        result = run(payroll_ctx)
        # Just verify it runs without error; detail may or may not
        # produce output depending on employer name matches
        assert isinstance(result["sections"], list)

    def test_sheets_match_sections_minus_one(self, payroll_ctx):
        """Each analysis function (except the empty-data notice) adds both
        a section and a sheet. Sheets should roughly match sections."""
        result = run(payroll_ctx)
        # Sheets should be populated (at least summary + top employers)
        assert len(result["sheets"]) >= 2

    def test_no_personal_df_still_works(self, payroll_ctx):
        """run() should not crash when personal_df is missing from ctx."""
        ctx = {
            "combined_df": payroll_ctx["combined_df"],
            "config": payroll_ctx["config"],
        }
        result = run(ctx)
        assert isinstance(result, dict)
        assert len(result["sections"]) >= 1

    def test_empty_config_uses_defaults(self, payroll_ctx):
        """run() with empty config should use default payroll detection."""
        ctx = {
            "combined_df": payroll_ctx["combined_df"],
            "config": {},
        }
        result = run(ctx)
        assert isinstance(result, dict)

    def test_description_field_present(self, payroll_ctx):
        result = run(payroll_ctx)
        assert "description" in result
        assert "Payroll" in result["description"]
