"""Tests for network inference."""

from __future__ import annotations

import pandas as pd
import pytest

from ics_toolkit.referral.network import infer_networks
from ics_toolkit.referral.normalizer import normalize_entities
from ics_toolkit.settings import ReferralSettings


@pytest.fixture
def settings():
    return ReferralSettings()


@pytest.fixture
def normalized_df(sample_referral_df, settings):
    return normalize_entities(sample_referral_df, settings)


class TestInferNetworks:
    def test_adds_network_columns(self, normalized_df):
        result = infer_networks(normalized_df)
        assert "Network ID" in result.columns
        assert "Network Size" in result.columns

    def test_network_id_format(self, normalized_df):
        result = infer_networks(normalized_df)
        for nid in result["Network ID"].dropna():
            assert ":" in nid, f"Network ID should contain ':' separator, got: {nid}"

    def test_network_size_positive(self, normalized_df):
        result = infer_networks(normalized_df)
        assert (result["Network Size"] > 0).all()

    def test_same_referrer_same_surname_grouped(self):
        df = pd.DataFrame(
            {
                "Referrer": ["JOHN SMITH", "JOHN SMITH"],
                "Account Surname": ["JONES", "JONES"],
                "MRDB Account Hash": ["H1", "H2"],
            }
        )
        result = infer_networks(df)
        assert result["Network ID"].nunique() == 1
        assert result["Network Size"].iloc[0] == 2

    def test_different_surnames_separate_networks(self):
        df = pd.DataFrame(
            {
                "Referrer": ["JOHN SMITH", "JOHN SMITH"],
                "Account Surname": ["JONES", "BROWN"],
                "MRDB Account Hash": ["H1", "H2"],
            }
        )
        result = infer_networks(df)
        assert result["Network ID"].nunique() == 2

    def test_preserves_row_count(self, normalized_df):
        result = infer_networks(normalized_df)
        assert len(result) == len(normalized_df)

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["Referrer", "Account Surname", "MRDB Account Hash"])
        result = infer_networks(df)
        assert len(result) == 0
        assert "Network ID" in result.columns
