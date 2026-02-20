"""Comprehensive tests for v4_s7_campaigns (Storyline 7: Campaign Effectiveness).

Tests cover:
- Helper functions: _parse_month, _next_month, _month_sort_key, _rate,
  _has_campaign_data, _detect_cols, _detect_spend_swipe_cols, _classify_responders
- All 13 analysis functions (happy path + missing column graceful returns)
- The run() orchestrator (no data, campaign data, empty DataFrame)
- The _add() helper for section/sheet assembly
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from txn_analysis.storylines.v4_s7_campaigns import (
    _add,
    _before_after_trends,
    _biz_personal_campaigns,
    _campaign_overview,
    _classify_responders,
    _detect_cols,
    _detect_spend_swipe_cols,
    _has_campaign_data,
    _month_sort_key,
    _monthly_tracking,
    _next_month,
    _offer_lift,
    _offer_txn_detail,
    _parse_month,
    _per_offer_response,
    _rate,
    _response_by_age_tenure,
    _response_by_balance_tier,
    _response_by_generation,
    _segmentation_performance,
    _spend_lift,
    _txn_size_buckets,
    run,
)

# ---------------------------------------------------------------------------
# Shared Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def campaign_odd() -> pd.DataFrame:
    """Build a realistic ODD DataFrame with all campaign-related columns.

    Contains 30 rows with a mix of responders and non-responders across
    3 campaign months (Jan25, Feb25, Mar25) plus 4 months of spend/swipe
    time series (Jan25-Apr25). Segmentation column provided for Mar25.
    """
    np.random.seed(42)
    n = 30

    # Basic account columns
    data = {
        "Acct Number": [f"A{i:04d}" for i in range(n)],
        "# of Offers": np.random.choice([0, 1, 2, 3], size=n, p=[0.1, 0.4, 0.3, 0.2]),
        "# of Responses": np.zeros(n, dtype=int),
        "Total Spend": np.random.uniform(200, 5000, size=n).round(2),
        "generation": np.random.choice(
            ["Gen Z", "Millennial", "Gen X", "Boomer"],
            size=n,
            p=[0.2, 0.3, 0.3, 0.2],
        ),
        "balance_tier": np.random.choice(
            ["Low", "Medium", "High", "Very High"],
            size=n,
            p=[0.15, 0.35, 0.35, 0.15],
        ),
        "Business?": np.random.choice(["Yes", "No"], size=n, p=[0.3, 0.7]),
        "Account Holder Age": np.random.randint(20, 75, size=n),
        "tenure_years": np.random.uniform(0.5, 20, size=n).round(1),
    }

    # Set ~40% as responders (# of Responses > 0)
    resp_mask = np.random.random(n) < 0.4
    data["# of Responses"] = np.where(resp_mask, np.random.randint(1, 4, size=n), 0)

    # Campaign mail/resp columns: offer name if mailed, NaN if not
    for month in ["Jan25", "Feb25", "Mar25"]:
        mail_vals = []
        for _ in range(n):
            if np.random.random() < 0.7:
                mail_vals.append("OfferB" if np.random.random() < 0.3 else "OfferA")
            else:
                mail_vals.append(np.nan)
        data[f"{month} Mail"] = mail_vals

        # ~30% of mailed respond
        resp_vals = []
        for m in mail_vals:
            if pd.notna(m):
                resp_vals.append(1 if np.random.random() < 0.3 else np.nan)
            else:
                resp_vals.append(np.nan)
        data[f"{month} Resp"] = resp_vals

    # Segmentation column for Mar25
    seg_vals = []
    for m in data["Mar25 Mail"]:
        if pd.notna(m):
            seg_vals.append(np.random.choice(["Premium", "Standard", "Growth"]))
        else:
            seg_vals.append(np.nan)
    data["Mar25 Segmentation"] = seg_vals

    # Spend/Swipe time series (Jan25 through Apr25)
    for month in ["Jan25", "Feb25", "Mar25", "Apr25"]:
        data[f"{month} Spend"] = np.random.uniform(50, 3000, size=n).round(2)
        data[f"{month} Swipes"] = np.random.randint(1, 50, size=n)

    return pd.DataFrame(data)


@pytest.fixture()
def empty_odd() -> pd.DataFrame:
    """Completely empty DataFrame for graceful-return tests."""
    return pd.DataFrame()


@pytest.fixture()
def no_campaign_odd() -> pd.DataFrame:
    """DataFrame without campaign columns (no # of Offers, no MmmYY Mail)."""
    return pd.DataFrame(
        {
            "Acct Number": ["A0001", "A0002"],
            "Total Spend": [100.0, 200.0],
        }
    )


# ===========================================================================
# Helper Function Tests
# ===========================================================================


class TestParseMonth:
    def test_standard_month(self):
        assert _parse_month("Jan25") == (1, 2025)

    def test_december(self):
        assert _parse_month("Dec24") == (12, 2024)

    def test_mid_year(self):
        assert _parse_month("Jul30") == (7, 2030)

    def test_all_months(self):
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        for i, m in enumerate(months, start=1):
            label = f"{m}25"
            month_num, year = _parse_month(label)
            assert month_num == i
            assert year == 2025


class TestMonthSortKey:
    def test_same_year_ordering(self):
        labels = ["Mar25", "Jan25", "Feb25"]
        sorted_labels = sorted(labels, key=_month_sort_key)
        assert sorted_labels == ["Jan25", "Feb25", "Mar25"]

    def test_cross_year_ordering(self):
        labels = ["Feb26", "Dec25", "Jan26"]
        sorted_labels = sorted(labels, key=_month_sort_key)
        assert sorted_labels == ["Dec25", "Jan26", "Feb26"]


class TestNextMonth:
    def test_standard_increment(self):
        assert _next_month("Jan25") == "Feb25"

    def test_mid_year(self):
        assert _next_month("Jun25") == "Jul25"

    def test_year_rollover(self):
        assert _next_month("Dec25") == "Jan26"

    def test_november_to_december(self):
        assert _next_month("Nov25") == "Dec25"

    def test_february_to_march(self):
        assert _next_month("Feb25") == "Mar25"


class TestRate:
    def test_normal_calculation(self):
        assert _rate(10, 100) == 10.0

    def test_zero_denominator(self):
        assert _rate(5, 0) == 0.0

    def test_full_rate(self):
        assert _rate(100, 100) == 100.0

    def test_rounding(self):
        # 1/3 * 100 = 33.333... -> 33.3
        assert _rate(1, 3) == 33.3

    def test_zero_numerator(self):
        assert _rate(0, 50) == 0.0


class TestHasCampaignData:
    def test_none_input(self):
        assert _has_campaign_data(None) is False

    def test_empty_dataframe(self):
        assert _has_campaign_data(pd.DataFrame()) is False

    def test_with_offers_column(self):
        df = pd.DataFrame({"# of Offers": [1, 2, 3]})
        assert _has_campaign_data(df) is True

    def test_with_mail_column(self):
        df = pd.DataFrame({"Jan25 Mail": [1, 0, 1]})
        assert _has_campaign_data(df) is True

    def test_without_campaign_columns(self, no_campaign_odd):
        assert _has_campaign_data(no_campaign_odd) is False

    def test_with_both_offers_and_mail(self, campaign_odd):
        assert _has_campaign_data(campaign_odd) is True


class TestDetectCols:
    def test_finds_mail_resp_seg(self, campaign_odd):
        mail, resp, seg = _detect_cols(campaign_odd)
        assert len(mail) == 3
        assert "Jan25 Mail" in mail
        assert "Feb25 Mail" in mail
        assert "Mar25 Mail" in mail
        assert len(resp) == 3
        assert "Jan25 Resp" in resp
        assert len(seg) == 1
        assert "Mar25 Segmentation" in seg

    def test_no_campaign_cols(self, no_campaign_odd):
        mail, resp, seg = _detect_cols(no_campaign_odd)
        assert mail == []
        assert resp == []
        assert seg == []

    def test_sorted_order(self, campaign_odd):
        mail, resp, seg = _detect_cols(campaign_odd)
        assert mail == sorted(mail)
        assert resp == sorted(resp)


class TestDetectSpendSwipeCols:
    def test_finds_common_months(self, campaign_odd):
        months = _detect_spend_swipe_cols(campaign_odd)
        # Jan25, Feb25, Mar25, Apr25 all have both Spend and Swipes
        assert len(months) == 4
        assert "Jan25" in months
        assert "Apr25" in months

    def test_empty_df(self, empty_odd):
        assert _detect_spend_swipe_cols(empty_odd) == []

    def test_spend_only_no_swipes(self):
        df = pd.DataFrame({"Jan25 Spend": [100], "Feb25 Spend": [200]})
        assert _detect_spend_swipe_cols(df) == []

    def test_sorted_chronologically(self, campaign_odd):
        months = _detect_spend_swipe_cols(campaign_odd)
        assert months == sorted(months, key=_month_sort_key)


class TestClassifyResponders:
    def test_standard_classification(self):
        df = pd.DataFrame(
            {
                "Jan25 Mail": ["OfferA", "OfferA", "OfferA"],
                "Jan25 Resp": [1, np.nan, 1],
            }
        )
        resp, non_resp = _classify_responders(df, "Jan25 Resp", "OfferA")
        assert len(resp) == 2
        assert len(non_resp) == 1

    def test_nu_offer_excludes_nu_1_to_4(self):
        df = pd.DataFrame(
            {
                "Jan25 Mail": ["NU Offer", "NU Offer", "NU Offer", "NU Offer"],
                "Jan25 Resp": ["NU 1", "NU 5", "NU 2", np.nan],
            }
        )
        resp, non_resp = _classify_responders(df, "Jan25 Resp", "NU Offer")
        # NU 5 is a real response; NU 1 and NU 2 are not; NaN is not
        assert len(resp) == 1  # NU 5
        assert len(non_resp) == 3

    def test_all_responders(self):
        df = pd.DataFrame(
            {
                "resp_col": [1, 1, 1],
            }
        )
        resp, non_resp = _classify_responders(df, "resp_col", "OfferA")
        assert len(resp) == 3
        assert len(non_resp) == 0

    def test_all_non_responders(self):
        df = pd.DataFrame(
            {
                "resp_col": [np.nan, np.nan],
            }
        )
        resp, non_resp = _classify_responders(df, "resp_col", "OfferA")
        assert len(resp) == 0
        assert len(non_resp) == 2


# ===========================================================================
# Analysis Function Tests
# ===========================================================================


def _assert_analysis_result(result):
    """Verify the standard (DataFrame, Figure, str) return tuple."""
    df, fig, narr = result
    assert isinstance(df, pd.DataFrame)
    assert isinstance(fig, go.Figure)
    assert isinstance(narr, str)
    return df, fig, narr


def _assert_empty_result(result):
    """Verify an analysis returns the empty-graceful triple."""
    df, fig, narr = _assert_analysis_result(result)
    assert df.empty
    assert narr == ""
    return df, fig, narr


class TestCampaignOverview:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_campaign_overview(campaign_odd))
        assert not df.empty
        assert len(df) == 5
        metrics = df["Metric"].tolist()
        assert "Total Accounts" in metrics
        assert "Accounts Mailed" in metrics
        assert "Responders" in metrics
        assert "Non-Responders" in metrics
        assert "Response Rate (%)" in metrics
        assert "response rate" in narr.lower()

    def test_no_offers_column(self):
        """Without # of Offers, all accounts are treated as mailed."""
        df_input = pd.DataFrame(
            {
                "# of Responses": [1, 0, 1, 0, 0, 0],
            }
        )
        df, fig, narr = _assert_analysis_result(_campaign_overview(df_input))
        assert not df.empty
        total_row = df[df["Metric"] == "Total Accounts"]["Value"].iloc[0]
        assert total_row == 6

    def test_no_responses_column(self):
        """Without # of Responses, all resp_mask is False."""
        df_input = pd.DataFrame(
            {
                "# of Offers": [1, 1, 1, 0],
            }
        )
        df, fig, narr = _assert_analysis_result(_campaign_overview(df_input))
        # Responders should be 0
        resp_val = df[df["Metric"] == "Responders"]["Value"].iloc[0]
        assert resp_val == 0


class TestResponseByGeneration:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_response_by_generation(campaign_odd))
        assert not df.empty
        assert "Generation" in df.columns
        assert "Response Rate (%)" in df.columns
        assert narr != ""

    def test_missing_columns(self):
        df_input = pd.DataFrame({"some_col": [1, 2, 3]})
        _assert_empty_result(_response_by_generation(df_input))

    def test_no_offers_above_zero(self):
        df_input = pd.DataFrame(
            {
                "generation": ["Gen Z"] * 10,
                "# of Offers": [0] * 10,
                "# of Responses": [0] * 10,
            }
        )
        _assert_empty_result(_response_by_generation(df_input))

    def test_min_group_filter(self):
        """Groups with fewer than 5 accounts should be filtered out."""
        df_input = pd.DataFrame(
            {
                "generation": ["Gen Z"] * 3 + ["Millennial"] * 10,
                "# of Offers": [1] * 13,
                "# of Responses": [1] * 3 + [1] * 5 + [0] * 5,
            }
        )
        df, fig, narr = _assert_analysis_result(_response_by_generation(df_input))
        # Gen Z has only 3 -- should be filtered
        assert "Gen Z" not in df["Generation"].values
        assert "Millennial" in df["Generation"].values


class TestSpendLift:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_spend_lift(campaign_odd))
        assert not df.empty
        assert "Group" in df.columns
        assert "Avg Spend" in df.columns
        assert "lift" in narr.lower()

    def test_missing_total_spend(self):
        df_input = pd.DataFrame({"# of Responses": [1, 0]})
        _assert_empty_result(_spend_lift(df_input))

    def test_missing_responses(self):
        df_input = pd.DataFrame({"Total Spend": [100, 200]})
        _assert_empty_result(_spend_lift(df_input))

    def test_with_response_grouping(self):
        """When 'Response Grouping' column exists, combined output includes it."""
        df_input = pd.DataFrame(
            {
                "Total Spend": [500, 100, 300, 200, 600, 150],
                "# of Responses": [1, 0, 2, 0, 1, 0],
                "Response Grouping": ["GroupA", "GroupB", "GroupA", "GroupB", "GroupA", "GroupB"],
            }
        )
        df, fig, narr = _assert_analysis_result(_spend_lift(df_input))
        # Should have Responder + Non-Responder + GroupA + GroupB
        assert len(df) == 4


class TestMonthlyTracking:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_monthly_tracking(campaign_odd))
        assert not df.empty
        assert "Month" in df.columns
        assert "Mailed" in df.columns
        assert "Response Rate (%)" in df.columns
        assert "3 months" in narr or "months" in narr.lower()

    def test_no_mail_cols(self, no_campaign_odd):
        _assert_empty_result(_monthly_tracking(no_campaign_odd))

    def test_mail_with_binary_values(self):
        """Test when mail columns contain 0/1 instead of offer names."""
        df_input = pd.DataFrame(
            {
                "Jan25 Mail": [1, 0, 1, 1, 0, 1, 0, 1],
                "Jan25 Resp": [1, 0, 0, 1, 0, 0, 0, 1],
            }
        )
        df, fig, narr = _assert_analysis_result(_monthly_tracking(df_input))
        assert len(df) == 1
        assert df.iloc[0]["Month"] == "Jan25"


class TestSegmentationPerformance:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_segmentation_performance(campaign_odd))
        # Should have segments if enough data in Mar25 Segmentation
        assert isinstance(df, pd.DataFrame)
        assert isinstance(narr, str)

    def test_no_seg_columns(self, no_campaign_odd):
        _assert_empty_result(_segmentation_performance(no_campaign_odd))

    def test_with_rich_segmentation(self):
        """Build a DataFrame with enough data per segment to pass _MIN_GROUP."""
        n = 30
        np.random.seed(99)
        segs = np.random.choice(["Premium", "Standard"], size=n)
        df_input = pd.DataFrame(
            {
                "Mar25 Segmentation": segs,
                "Mar25 Resp": np.where(np.random.random(n) < 0.4, 1, np.nan),
                "Total Spend": np.random.uniform(100, 1000, n),
            }
        )
        df, fig, narr = _assert_analysis_result(_segmentation_performance(df_input))
        assert not df.empty
        assert "Segment" in df.columns
        assert "Response Rate (%)" in df.columns


class TestResponseByBalanceTier:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_response_by_balance_tier(campaign_odd))
        assert not df.empty
        assert "Balance Tier" in df.columns
        assert "Response Rate (%)" in df.columns
        assert narr != ""

    def test_missing_balance_tier(self):
        df_input = pd.DataFrame({"# of Responses": [1, 0]})
        _assert_empty_result(_response_by_balance_tier(df_input))

    def test_missing_responses_col(self):
        df_input = pd.DataFrame({"balance_tier": ["Low", "High"]})
        _assert_empty_result(_response_by_balance_tier(df_input))

    def test_no_offered_accounts(self):
        """When all # of Offers are 0, result is empty."""
        df_input = pd.DataFrame(
            {
                "balance_tier": ["Low"] * 6,
                "# of Responses": [0] * 6,
                "# of Offers": [0] * 6,
            }
        )
        _assert_empty_result(_response_by_balance_tier(df_input))


class TestPerOfferResponse:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_per_offer_response(campaign_odd))
        # Should have per-offer aggregated data
        assert isinstance(df, pd.DataFrame)

    def test_no_mail_cols(self, no_campaign_odd):
        _assert_empty_result(_per_offer_response(no_campaign_odd))

    def test_with_known_offers(self):
        """Build explicit offers to verify aggregation."""
        n = 20
        np.random.seed(123)
        offers = np.random.choice(["OfferA", "OfferB"], size=n)
        df_input = pd.DataFrame(
            {
                "Jan25 Mail": offers,
                "Jan25 Resp": np.where(np.random.random(n) < 0.5, 1, np.nan),
            }
        )
        df, fig, narr = _assert_analysis_result(_per_offer_response(df_input))
        assert not df.empty
        assert "Offer Type" in df.columns
        assert "Response Rate (%)" in df.columns


class TestOfferLift:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_offer_lift(campaign_odd))
        # May or may not have data depending on whether resp/non_resp are both non-empty
        assert isinstance(df, pd.DataFrame)

    def test_no_mail_or_spend_cols(self, no_campaign_odd):
        _assert_empty_result(_offer_lift(no_campaign_odd))

    def test_with_sufficient_data(self):
        """Build enough data with both responders and non-responders per offer."""
        np.random.seed(44)
        n = 30
        offers = np.random.choice(["OfferA", "OfferB"], size=n)
        resp = []
        for o in offers:
            resp.append(1 if np.random.random() < 0.4 else np.nan)
        df_input = pd.DataFrame(
            {
                "Jan25 Mail": offers,
                "Jan25 Resp": resp,
                "Jan25 Spend": np.random.uniform(100, 500, n),
                "Jan25 Swipes": np.random.randint(1, 30, n),
                "Feb25 Spend": np.random.uniform(100, 500, n),
                "Feb25 Swipes": np.random.randint(1, 30, n),
            }
        )
        df, fig, narr = _assert_analysis_result(_offer_lift(df_input))
        assert not df.empty
        assert "Campaign" in df.columns
        assert "Spend Lift (%)" in df.columns


class TestBeforeAfterTrends:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_before_after_trends(campaign_odd))
        # Will have data if the latest campaign month is in the spend/swipe months
        assert isinstance(df, pd.DataFrame)

    def test_no_mail_cols(self, no_campaign_odd):
        _assert_empty_result(_before_after_trends(no_campaign_odd))

    def test_insufficient_months(self):
        """Need at least 4 spend/swipe months."""
        df_input = pd.DataFrame(
            {
                "Jan25 Mail": ["OfferA", "OfferA"],
                "Jan25 Resp": [1, np.nan],
                "Jan25 Spend": [100, 200],
                "Jan25 Swipes": [5, 10],
            }
        )
        _assert_empty_result(_before_after_trends(df_input))

    def test_with_full_window(self):
        """Build a proper before/after dataset."""
        np.random.seed(77)
        n = 20
        all_months = ["Jan25", "Feb25", "Mar25", "Apr25", "May25", "Jun25"]
        data = {
            "Mar25 Mail": np.random.choice(["OfferA", np.nan], size=n, p=[0.8, 0.2]),
            "Mar25 Resp": [np.nan] * n,
        }
        # Set some responders
        for i in range(n):
            if pd.notna(data["Mar25 Mail"][i]) and np.random.random() < 0.4:
                data["Mar25 Resp"][i] = 1

        for m in all_months:
            data[f"{m} Spend"] = np.random.uniform(100, 1000, n).round(2)
            data[f"{m} Swipes"] = np.random.randint(1, 30, n)

        df_input = pd.DataFrame(data)
        df, fig, narr = _assert_analysis_result(_before_after_trends(df_input))
        assert not df.empty
        assert "Month" in df.columns
        assert "Responder Avg Spend" in df.columns


class TestTxnSizeBuckets:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_txn_size_buckets(campaign_odd))
        assert isinstance(df, pd.DataFrame)

    def test_no_mail_cols(self, no_campaign_odd):
        _assert_empty_result(_txn_size_buckets(no_campaign_odd))

    def test_with_proper_data(self):
        """Build data where resp and non-resp both have spend/swipe data."""
        np.random.seed(55)
        n = 20
        offers = ["OfferA"] * n
        resp = [1 if i < 8 else np.nan for i in range(n)]
        df_input = pd.DataFrame(
            {
                "Mar25 Mail": offers,
                "Mar25 Resp": resp,
                "Mar25 Spend": np.random.uniform(100, 1000, n),
                "Mar25 Swipes": np.random.randint(1, 30, n),
                "Apr25 Spend": np.random.uniform(100, 1000, n),
                "Apr25 Swipes": np.random.randint(1, 30, n),
            }
        )
        df, fig, narr = _assert_analysis_result(_txn_size_buckets(df_input))
        assert not df.empty
        assert "Amount Range" in df.columns
        assert "Difference (pp)" in df.columns


class TestOfferTxnDetail:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_offer_txn_detail(campaign_odd))
        assert isinstance(df, pd.DataFrame)

    def test_no_data(self, no_campaign_odd):
        _assert_empty_result(_offer_txn_detail(no_campaign_odd))

    def test_with_offer_data(self):
        """Explicit test with known responders and non-responders per offer."""
        np.random.seed(66)
        n = 24
        offers = ["OfferA"] * 12 + ["OfferB"] * 12
        resp = [1 if i % 3 == 0 else np.nan for i in range(n)]
        df_input = pd.DataFrame(
            {
                "Jan25 Mail": offers,
                "Jan25 Resp": resp,
                "Jan25 Spend": np.random.uniform(100, 500, n),
                "Jan25 Swipes": np.random.randint(1, 20, n),
                "Feb25 Spend": np.random.uniform(100, 500, n),
                "Feb25 Swipes": np.random.randint(1, 20, n),
            }
        )
        df, fig, narr = _assert_analysis_result(_offer_txn_detail(df_input))
        assert not df.empty
        assert "Offer Type" in df.columns
        assert "Resp Avg Txn ($)" in df.columns
        assert "swipes" in narr.lower()


class TestBizPersonalCampaigns:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_biz_personal_campaigns(campaign_odd))
        assert not df.empty
        assert "Account Type" in df.columns
        assert "Response Rate (%)" in df.columns

    def test_missing_business_col(self):
        df_input = pd.DataFrame(
            {
                "# of Offers": [1, 2],
                "# of Responses": [1, 0],
            }
        )
        _assert_empty_result(_biz_personal_campaigns(df_input))

    def test_missing_offers_col(self):
        df_input = pd.DataFrame(
            {
                "Business?": ["Yes", "No"],
                "# of Responses": [1, 0],
            }
        )
        _assert_empty_result(_biz_personal_campaigns(df_input))

    def test_no_offers_above_zero(self):
        df_input = pd.DataFrame(
            {
                "Business?": ["Yes"] * 6 + ["No"] * 6,
                "# of Offers": [0] * 12,
                "# of Responses": [0] * 12,
            }
        )
        _assert_empty_result(_biz_personal_campaigns(df_input))

    def test_maps_yes_no_to_labels(self, campaign_odd):
        df, _, _ = _biz_personal_campaigns(campaign_odd)
        if not df.empty:
            types = df["Account Type"].tolist()
            # Should have "Business" and/or "Personal" instead of "Yes"/"No"
            for t in types:
                assert t in ("Business", "Personal")


class TestResponseByAgeTenure:
    def test_happy_path(self, campaign_odd):
        df, fig, narr = _assert_analysis_result(_response_by_age_tenure(campaign_odd))
        assert not df.empty
        assert "Dimension" in df.columns
        assert "Bucket" in df.columns
        assert "Response Rate (%)" in df.columns
        assert narr != ""

    def test_missing_offers(self):
        df_input = pd.DataFrame(
            {
                "Account Holder Age": [30, 40, 50],
                "# of Responses": [1, 0, 1],
            }
        )
        _assert_empty_result(_response_by_age_tenure(df_input))

    def test_no_offered_accounts(self):
        df_input = pd.DataFrame(
            {
                "# of Offers": [0] * 10,
                "# of Responses": [0] * 10,
                "Account Holder Age": list(range(20, 30)),
            }
        )
        _assert_empty_result(_response_by_age_tenure(df_input))

    def test_age_buckets_present(self, campaign_odd):
        df, _, _ = _response_by_age_tenure(campaign_odd)
        if not df.empty:
            age_rows = df[df["Dimension"] == "Age"]
            if not age_rows.empty:
                # Buckets should be from the defined labels
                valid_buckets = {"18-25", "26-35", "36-45", "46-55", "56-65", "65+"}
                for bucket in age_rows["Bucket"]:
                    assert bucket in valid_buckets

    def test_tenure_buckets_present(self, campaign_odd):
        df, _, _ = _response_by_age_tenure(campaign_odd)
        if not df.empty:
            tenure_rows = df[df["Dimension"] == "Tenure"]
            if not tenure_rows.empty:
                valid_buckets = {"< 1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"}
                for bucket in tenure_rows["Bucket"]:
                    assert bucket in valid_buckets


# ===========================================================================
# _add Helper Tests
# ===========================================================================


class TestAdd:
    def test_appends_when_data_present(self):
        sections, sheets = [], []
        df = pd.DataFrame({"A": [1, 2, 3]})
        fig = go.Figure()
        _add(sections, sheets, "Test Heading", df, fig, "narrative", "Sheet1")
        assert len(sections) == 1
        assert sections[0]["heading"] == "Test Heading"
        assert sections[0]["narrative"] == "narrative"
        assert len(sheets) == 1
        assert sheets[0]["name"] == "Sheet1"

    def test_skips_when_empty(self):
        sections, sheets = [], []
        df = pd.DataFrame()
        fig = go.Figure()
        _add(sections, sheets, "Empty Heading", df, fig, "narrative", "Sheet1")
        assert len(sections) == 0
        assert len(sheets) == 0

    def test_passes_col_spec(self):
        sections, sheets = [], []
        df = pd.DataFrame({"X": [1]})
        fig = go.Figure()
        _add(
            sections,
            sheets,
            "Heading",
            df,
            fig,
            "n",
            "S1",
            currency_cols=["Spend"],
            pct_cols=["Rate"],
        )
        assert sheets[0]["currency_cols"] == ["Spend"]
        assert sheets[0]["pct_cols"] == ["Rate"]


# ===========================================================================
# run() Orchestrator Tests
# ===========================================================================


class TestRun:
    def test_no_campaign_data_returns_message(self, no_campaign_odd):
        result = run({"odd_df": no_campaign_odd})
        assert "title" in result
        assert "S7" in result["title"]
        assert "No campaign data" in result["description"] or any(
            "No campaign data" in s.get("narrative", "") for s in result["sections"]
        )
        assert result["sheets"] == []

    def test_none_odd_df(self):
        result = run({"odd_df": None})
        assert "title" in result
        assert result["sheets"] == []
        assert len(result["sections"]) == 1

    def test_empty_odd_df(self, empty_odd):
        result = run({"odd_df": empty_odd})
        assert "title" in result
        assert result["sheets"] == []

    def test_missing_odd_key(self):
        result = run({})
        assert "title" in result
        assert result["sheets"] == []

    def test_with_campaign_data(self, campaign_odd):
        result = run({"odd_df": campaign_odd})
        assert "title" in result
        assert "S7" in result["title"]
        assert isinstance(result["sections"], list)
        assert isinstance(result["sheets"], list)
        # At minimum, campaign overview should always be present
        assert len(result["sections"]) >= 1
        assert len(result["sheets"]) >= 1

    def test_campaign_overview_always_first(self, campaign_odd):
        result = run({"odd_df": campaign_odd})
        first_section = result["sections"][0]
        assert first_section["heading"] == "Campaign Overview"

    def test_sheets_have_required_keys(self, campaign_odd):
        result = run({"odd_df": campaign_odd})
        for sheet in result["sheets"]:
            assert "name" in sheet
            assert "df" in sheet
            assert isinstance(sheet["df"], pd.DataFrame)

    def test_sections_have_required_keys(self, campaign_odd):
        result = run({"odd_df": campaign_odd})
        for section in result["sections"]:
            assert "heading" in section
            assert "narrative" in section
            assert "figures" in section
            assert "tables" in section
            assert isinstance(section["figures"], list)
            assert isinstance(section["tables"], list)

    def test_description_populated(self, campaign_odd):
        result = run({"odd_df": campaign_odd})
        assert "description" in result
        assert len(result["description"]) > 0

    def test_all_sheet_names_unique(self, campaign_odd):
        result = run({"odd_df": campaign_odd})
        names = [s["name"] for s in result["sheets"]]
        assert len(names) == len(set(names)), "Duplicate sheet names found"

    def test_multiple_sections_with_full_data(self, campaign_odd):
        """With full campaign data, multiple analyses should produce results."""
        result = run({"odd_df": campaign_odd})
        # At least overview + a few more
        assert len(result["sections"]) >= 3
