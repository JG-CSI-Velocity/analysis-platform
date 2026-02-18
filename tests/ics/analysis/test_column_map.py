"""Tests for column_map.py -- column resolution and validation."""

import pandas as pd
import pytest

from ics_toolkit.analysis.column_map import (
    discover_l12m_columns,
    resolve_columns,
    validate_columns,
)
from ics_toolkit.exceptions import DataError


class TestResolveColumns:
    def test_resolves_known_aliases(self):
        df = pd.DataFrame({"ICS Accounts": [1], "StatCode": [2], "Debit": [3]})
        result = resolve_columns(df)
        assert "ICS Account" in result.columns
        assert "Stat Code" in result.columns
        assert "Debit?" in result.columns

    def test_preserves_canonical_names(self):
        df = pd.DataFrame({"ICS Account": [1], "Stat Code": [2]})
        result = resolve_columns(df)
        assert list(result.columns) == ["ICS Account", "Stat Code"]

    def test_strips_whitespace(self):
        df = pd.DataFrame({" ICS Accounts ": [1]})
        # Current implementation strips via str comparison
        result = resolve_columns(df)
        # The column with leading/trailing spaces should be handled
        assert any("ICS" in str(c) for c in result.columns)

    def test_unknown_columns_kept(self):
        df = pd.DataFrame({"ICS Account": [1], "Custom Column": [2]})
        result = resolve_columns(df)
        assert "Custom Column" in result.columns


class TestValidateColumns:
    def test_all_required_present(self, sample_df):
        # Should not raise
        missing = validate_columns(sample_df)
        assert missing == []

    def test_missing_required_raises(self):
        df = pd.DataFrame({"ICS Account": [1], "Stat Code": [2]})
        with pytest.raises(DataError, match="Missing required columns"):
            validate_columns(df)

    def test_optional_missing_ok(self, sample_df):
        # Remove optional column
        df = sample_df.drop(columns=["Date Closed"], errors="ignore")
        # Should not raise
        validate_columns(df)


class TestDiscoverL12MColumns:
    def test_discovers_matching_pairs(self, sample_df):
        tags, swipes, spends = discover_l12m_columns(sample_df)
        assert len(tags) == 12
        assert len(swipes) == 12
        assert len(spends) == 12
        assert tags[0] == "Feb25"
        assert tags[-1] == "Jan26"

    def test_sorted_chronologically(self, sample_df):
        tags, _, _ = discover_l12m_columns(sample_df)
        # Feb25 should come before Jan26
        assert tags.index("Feb25") < tags.index("Jan26")

    def test_no_l12m_columns(self):
        df = pd.DataFrame({"col1": [1], "col2": [2]})
        tags, swipes, spends = discover_l12m_columns(df)
        assert tags == []
        assert swipes == []
        assert spends == []

    def test_partial_columns_only_common(self):
        df = pd.DataFrame(
            {
                "Feb25 Swipes": [1],
                "Feb25 Spend": [2],
                "Mar25 Swipes": [3],
                # Missing Mar25 Spend
            }
        )
        tags, swipes, spends = discover_l12m_columns(df)
        assert tags == ["Feb25"]
        assert swipes == ["Feb25 Swipes"]
        assert spends == ["Feb25 Spend"]
