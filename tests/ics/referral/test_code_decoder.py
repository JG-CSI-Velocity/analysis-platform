"""Tests for referral code decoder."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.referral.code_decoder import _classify_channel, decode_referral_codes
from ics_toolkit.settings import ReferralSettings


@pytest.fixture
def settings():
    return ReferralSettings()


class TestClassifyChannel:
    def test_null_is_manual(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel(None, prefixes, settings.code_prefix_map) == "MANUAL"

    def test_empty_string_is_manual(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("", prefixes, settings.code_prefix_map) == "MANUAL"

    def test_none_string_is_manual(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("None", prefixes, settings.code_prefix_map) == "MANUAL"

    def test_branch_prefix_150a(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("150A001", prefixes, settings.code_prefix_map) == "BRANCH_STANDARD"

    def test_branch_prefix_120a(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("120A002", prefixes, settings.code_prefix_map) == "BRANCH_STANDARD"

    def test_digital_prefix_pc(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("PC100", prefixes, settings.code_prefix_map) == "DIGITAL_PROCESS"

    def test_email_keyword(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("EMAIL_Q1", prefixes, settings.code_prefix_map) == "EMAIL"

    def test_unknown_code_is_other(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("UNKNOWN_XYZ", prefixes, settings.code_prefix_map) == "OTHER"

    def test_case_insensitive(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert _classify_channel("150a001", prefixes, settings.code_prefix_map) == "BRANCH_STANDARD"
        assert _classify_channel("pc200", prefixes, settings.code_prefix_map) == "DIGITAL_PROCESS"

    def test_whitespace_stripped(self, settings):
        prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
        assert (
            _classify_channel("  150A001  ", prefixes, settings.code_prefix_map)
            == "BRANCH_STANDARD"
        )


class TestDecodeReferralCodes:
    def test_adds_three_columns(self, sample_referral_df, settings):
        result = decode_referral_codes(sample_referral_df, settings)
        assert "Referral Channel" in result.columns
        assert "Referral Type" in result.columns
        assert "Referral Reliability" in result.columns

    def test_no_nulls_in_channel(self, sample_referral_df, settings):
        result = decode_referral_codes(sample_referral_df, settings)
        assert result["Referral Channel"].notna().all()

    def test_type_values(self, sample_referral_df, settings):
        result = decode_referral_codes(sample_referral_df, settings)
        valid_types = {"Standard", "Manual", "Exception"}
        assert set(result["Referral Type"].unique()) <= valid_types

    def test_reliability_values(self, sample_referral_df, settings):
        result = decode_referral_codes(sample_referral_df, settings)
        valid_rel = {"High", "Medium", "Low"}
        assert set(result["Referral Reliability"].unique()) <= valid_rel

    def test_custom_prefix_map(self, sample_referral_df):
        custom = ReferralSettings(code_prefix_map={"CUSTOM": "CUSTOM_CHANNEL"})
        df = sample_referral_df.copy()
        df.loc[0, "Referral Code"] = "CUSTOM_001"
        result = decode_referral_codes(df, custom)
        assert result.loc[0, "Referral Channel"] == "CUSTOM_CHANNEL"

    def test_all_null_codes(self, settings):
        df = pd.DataFrame(
            {
                "Referral Code": [None, None, None],
            }
        )
        result = decode_referral_codes(df, settings)
        assert (result["Referral Channel"] == "MANUAL").all()
        assert (result["Referral Type"] == "Manual").all()
        assert (result["Referral Reliability"] == "Medium").all()
