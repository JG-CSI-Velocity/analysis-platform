"""Tests for referral column map."""

from ics_toolkit.referral.column_map import COLUMN_ALIASES, REQUIRED_COLUMNS


class TestRequiredColumns:
    """Tests for the required columns list."""

    def test_has_eight_columns(self):
        assert len(REQUIRED_COLUMNS) == 8

    def test_contains_expected_columns(self):
        expected = {
            "Referrer Name",
            "Issue Date",
            "Referral Code",
            "Purchase Manager",
            "Branch",
            "Account Holder",
            "MRDB Account Hash",
            "Cert ID",
        }
        assert set(REQUIRED_COLUMNS) == expected


class TestColumnAliases:
    """Tests for column alias mappings."""

    def test_all_aliases_map_to_required_columns(self):
        for alias, canonical in COLUMN_ALIASES.items():
            assert canonical in REQUIRED_COLUMNS, (
                f"Alias '{alias}' maps to unknown column '{canonical}'"
            )

    def test_all_required_columns_have_at_least_one_alias(self):
        aliased = set(COLUMN_ALIASES.values())
        for col in REQUIRED_COLUMNS:
            assert col in aliased, f"Required column '{col}' has no alias"

    def test_aliases_are_lowercase(self):
        for alias in COLUMN_ALIASES:
            assert alias == alias.lower(), f"Alias '{alias}' is not lowercase"
