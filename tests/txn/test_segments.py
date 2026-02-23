"""Tests for txn_analysis.segments -- ODD-based account segment extraction."""

from __future__ import annotations

import pandas as pd

from txn_analysis.segments import (
    RESPONSE_SEGMENTS,
    SegmentFilter,
    build_segment_filters,
    extract_ics_accounts,
    extract_responder_accounts,
)


def _make_odd(
    accts: list[str],
    resp_values: dict[str, list[str]] | None = None,
    ics_values: list[str] | None = None,
) -> pd.DataFrame:
    """Build a synthetic ODD DataFrame for testing."""
    data: dict[str, list] = {"Acct Number": accts}
    if resp_values:
        for col, vals in resp_values.items():
            data[col] = vals
    if ics_values is not None:
        data["ICS Account"] = ics_values
    return pd.DataFrame(data)


class TestExtractResponderAccounts:
    def test_basic_responders(self):
        odd = _make_odd(
            ["1001", "1002", "1003"],
            resp_values={"Aug25 Resp": ["NU 5+", "", "TH-10"]},
        )
        result = extract_responder_accounts(odd)
        assert result == {"1001", "1003"}

    def test_no_resp_columns(self):
        odd = _make_odd(["1001", "1002"])
        result = extract_responder_accounts(odd)
        assert result == set()

    def test_no_acct_number_column(self):
        odd = pd.DataFrame({"Aug25 Resp": ["NU 5+", "TH-10"]})
        result = extract_responder_accounts(odd)
        assert result == set()

    def test_multiple_resp_columns(self):
        odd = _make_odd(
            ["1001", "1002", "1003", "1004"],
            resp_values={
                "Jan24 Resp": ["", "TH-15", "", ""],
                "Aug25 Resp": ["NU 5+", "", "", ""],
            },
        )
        result = extract_responder_accounts(odd)
        assert result == {"1001", "1002"}

    def test_no_responders_found(self):
        odd = _make_odd(
            ["1001", "1002"],
            resp_values={"Aug25 Resp": ["", "Other"]},
        )
        result = extract_responder_accounts(odd)
        assert result == set()

    def test_nan_acct_numbers_excluded(self):
        odd = pd.DataFrame({
            "Acct Number": ["1001", None, "1003"],
            "Jan24 Resp": ["NU 5+", "TH-10", "TH-20"],
        })
        result = extract_responder_accounts(odd)
        assert "1001" in result
        assert "1003" in result
        assert len(result) == 2

    def test_all_segment_codes_recognized(self):
        codes = list(RESPONSE_SEGMENTS)
        odd = _make_odd(
            [str(i) for i in range(len(codes))],
            resp_values={"Dec25 Resp": codes},
        )
        result = extract_responder_accounts(odd)
        assert len(result) == len(codes)


class TestExtractICSAccounts:
    def test_basic_ics(self):
        odd = _make_odd(
            ["1001", "1002", "1003"],
            ics_values=["Yes", "No", "Yes"],
        )
        result = extract_ics_accounts(odd)
        assert result == {"1001", "1003"}

    def test_case_insensitive(self):
        odd = _make_odd(
            ["1001", "1002", "1003"],
            ics_values=["yes", "YES", "no"],
        )
        result = extract_ics_accounts(odd)
        assert result == {"1001", "1002"}

    def test_no_ics_column(self):
        odd = _make_odd(["1001", "1002"])
        result = extract_ics_accounts(odd)
        assert result == set()

    def test_no_acct_number_column(self):
        odd = pd.DataFrame({"ICS Account": ["Yes", "No"]})
        result = extract_ics_accounts(odd)
        assert result == set()

    def test_alias_columns(self):
        for alias in ("ICS Accounts", "Ics Account", "ICS_Account"):
            odd = pd.DataFrame({
                "Acct Number": ["1001", "1002"],
                alias: ["Yes", "No"],
            })
            result = extract_ics_accounts(odd)
            assert result == {"1001"}, f"Failed for alias: {alias}"

    def test_whitespace_handling(self):
        odd = _make_odd(
            ["1001", "1002"],
            ics_values=["  Yes  ", " No "],
        )
        result = extract_ics_accounts(odd)
        assert result == {"1001"}


class TestSegmentFilter:
    def test_filter_transactions(self):
        seg = SegmentFilter(
            name="test", label="Test", account_numbers=frozenset({"1001", "1003"})
        )
        txn_df = pd.DataFrame({
            "primary_account_num": [1001, 1002, 1003, 1004],
            "amount": [100, 200, 300, 400],
        })
        filtered = seg.filter_transactions(txn_df)
        assert len(filtered) == 2
        assert set(filtered["primary_account_num"]) == {1001, 1003}

    def test_filter_empty_result(self):
        seg = SegmentFilter(
            name="test", label="Test", account_numbers=frozenset({"9999"})
        )
        txn_df = pd.DataFrame({
            "primary_account_num": [1001, 1002],
            "amount": [100, 200],
        })
        filtered = seg.filter_transactions(txn_df)
        assert len(filtered) == 0


class TestBuildSegmentFilters:
    def test_both_segments(self):
        odd = _make_odd(
            ["1001", "1002", "1003"],
            resp_values={"Aug25 Resp": ["NU 5+", "", ""]},
            ics_values=["No", "Yes", "No"],
        )
        filters = build_segment_filters(odd, ars_responders=True, ics_accounts=True)
        assert len(filters) == 2
        names = {f.name for f in filters}
        assert names == {"ars_responders", "ics_accounts"}

    def test_no_odd(self):
        filters = build_segment_filters(None, ars_responders=True, ics_accounts=True)
        assert filters == []

    def test_disabled_by_default(self):
        odd = _make_odd(
            ["1001"],
            resp_values={"Aug25 Resp": ["NU 5+"]},
            ics_values=["Yes"],
        )
        filters = build_segment_filters(odd)
        assert filters == []

    def test_empty_segments_excluded(self):
        odd = _make_odd(
            ["1001", "1002"],
            resp_values={"Aug25 Resp": ["", ""]},
        )
        filters = build_segment_filters(odd, ars_responders=True)
        assert filters == []

    def test_only_ars(self):
        odd = _make_odd(
            ["1001", "1002"],
            resp_values={"Aug25 Resp": ["NU 5+", ""]},
        )
        filters = build_segment_filters(odd, ars_responders=True, ics_accounts=False)
        assert len(filters) == 1
        assert filters[0].name == "ars_responders"

    def test_only_ics(self):
        odd = _make_odd(
            ["1001", "1002"],
            ics_values=["Yes", "No"],
        )
        filters = build_segment_filters(odd, ars_responders=False, ics_accounts=True)
        assert len(filters) == 1
        assert filters[0].name == "ics_accounts"
