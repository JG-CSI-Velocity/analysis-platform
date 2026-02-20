"""Tests for entity normalizer."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.referral.normalizer import (
    SUFFIXES,
    _extract_surname,
    _normalize_name,
    normalize_entities,
)
from ics_toolkit.settings import ReferralSettings


@pytest.fixture
def settings():
    return ReferralSettings()


class TestNormalizeEntities:
    def test_adds_canonical_columns(self, sample_referral_df, settings):
        result = normalize_entities(sample_referral_df, settings)
        for col in [
            "Referrer",
            "New Account",
            "Staff",
            "Branch Code",
            "Branch Label",
            "Referrer Surname",
            "Account Surname",
        ]:
            assert col in result.columns, f"Missing: {col}"

    def test_preserves_original_columns(self, sample_referral_df, settings):
        result = normalize_entities(sample_referral_df, settings)
        assert "Referrer Name" in result.columns
        assert "Account Holder" in result.columns

    def test_referrer_is_uppercase(self, sample_referral_df, settings):
        result = normalize_entities(sample_referral_df, settings)
        for val in result["Referrer"]:
            assert val == val.upper()

    def test_null_referrer_becomes_unknown(self, settings):
        df = pd.DataFrame(
            {
                "Referrer Name": [None, "  ", "JOHN"],
                "Issue Date": ["2025-01-01"] * 3,
                "Referral Code": ["X"] * 3,
                "Purchase Manager": ["S"] * 3,
                "Branch": ["1"] * 3,
                "Account Holder": ["A"] * 3,
                "MRDB Account Hash": ["H1", "H2", "H3"],
                "Cert ID": ["C1", "C2", "C3"],
            }
        )
        result = normalize_entities(df, settings)
        assert result["Referrer"].iloc[0] == "UNKNOWN"
        assert result["Referrer"].iloc[2] == "JOHN"

    def test_null_staff_becomes_unassigned(self, settings):
        df = pd.DataFrame(
            {
                "Referrer Name": ["JOHN"],
                "Issue Date": ["2025-01-01"],
                "Referral Code": ["X"],
                "Purchase Manager": [None],
                "Branch": ["1"],
                "Account Holder": ["A"],
                "MRDB Account Hash": ["H1"],
                "Cert ID": ["C1"],
            }
        )
        result = normalize_entities(df, settings)
        assert result["Staff"].iloc[0] == "UNASSIGNED"

    def test_branch_mapping(self):
        settings = ReferralSettings(branch_mapping={"001": "Main Branch", "002": "West"})
        df = pd.DataFrame(
            {
                "Referrer Name": ["A", "B"],
                "Issue Date": ["2025-01-01"] * 2,
                "Referral Code": ["X"] * 2,
                "Purchase Manager": ["S"] * 2,
                "Branch": ["001", "003"],
                "Account Holder": ["N1", "N2"],
                "MRDB Account Hash": ["H1", "H2"],
                "Cert ID": ["C1", "C2"],
            }
        )
        result = normalize_entities(df, settings)
        assert result["Branch Label"].iloc[0] == "Main Branch"
        assert result["Branch Label"].iloc[1] == "003"

    def test_name_aliases(self):
        settings = ReferralSettings(name_aliases={"J SMITH": "JOHN SMITH"})
        df = pd.DataFrame(
            {
                "Referrer Name": ["j smith", "JOHN SMITH"],
                "Issue Date": ["2025-01-01"] * 2,
                "Referral Code": ["X"] * 2,
                "Purchase Manager": ["S"] * 2,
                "Branch": ["1"] * 2,
                "Account Holder": ["A", "B"],
                "MRDB Account Hash": ["H1", "H2"],
                "Cert ID": ["C1", "C2"],
            }
        )
        result = normalize_entities(df, settings)
        assert result["Referrer"].iloc[0] == "JOHN SMITH"
        assert result["Referrer"].iloc[1] == "JOHN SMITH"


class TestNormalizeName:
    def test_strips_and_uppercases(self):
        series = pd.Series(["  john smith  ", "Jane Doe"])
        result = _normalize_name(series, {}, "UNKNOWN")
        assert result.iloc[0] == "JOHN SMITH"
        assert result.iloc[1] == "JANE DOE"

    def test_collapses_whitespace(self):
        series = pd.Series(["JOHN    SMITH"])
        result = _normalize_name(series, {}, "UNKNOWN")
        assert result.iloc[0] == "JOHN SMITH"

    def test_null_to_sentinel(self):
        series = pd.Series([None, ""])
        result = _normalize_name(series, {}, "UNKNOWN")
        assert result.iloc[0] == "UNKNOWN"
        assert result.iloc[1] == "UNKNOWN"


class TestExtractSurname:
    def test_standard_two_word_name(self):
        result = _extract_surname(pd.Series(["JOHN SMITH"]))
        assert result.iloc[0] == "SMITH"

    def test_single_word_name(self):
        result = _extract_surname(pd.Series(["MADONNA"]))
        assert result.iloc[0] == "MADONNA"

    def test_skips_jr_suffix(self):
        result = _extract_surname(pd.Series(["JOHN SMITH JR"]))
        assert result.iloc[0] == "SMITH"

    def test_skips_sr_suffix(self):
        result = _extract_surname(pd.Series(["MARY JONES SR"]))
        assert result.iloc[0] == "JONES"

    def test_skips_roman_numeral_suffix(self):
        result = _extract_surname(pd.Series(["WILLIAM GATES III"]))
        assert result.iloc[0] == "GATES"

    def test_two_word_with_suffix_only_has_two_parts(self):
        # "SMITH JR" -> only 2 parts, last is suffix but no preceding surname
        result = _extract_surname(pd.Series(["SMITH JR"]))
        assert result.iloc[0] == "JR"  # Can't skip suffix when only 2 parts

    def test_suffixes_constant(self):
        assert "JR" in SUFFIXES
        assert "SR" in SUFFIXES
        assert "III" in SUFFIXES
