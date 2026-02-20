"""Tests for attrition shared helpers."""

import pandas as pd
import pytest

from ars_analysis.analytics.attrition._helpers import (
    BALANCE_ORDER,
    DURATION_ORDER,
    TENURE_ORDER,
    categorize_balance,
    categorize_duration,
    categorize_tenure,
    prepare_attrition_data,
    product_col,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Ordering constants have expected lengths."""

    def test_duration_order_count(self):
        assert len(DURATION_ORDER) == 8

    def test_tenure_order_count(self):
        assert len(TENURE_ORDER) == 6

    def test_balance_order_count(self):
        assert len(BALANCE_ORDER) == 8


# ---------------------------------------------------------------------------
# categorize_duration
# ---------------------------------------------------------------------------


class TestCategorizeDuration:
    """categorize_duration buckets days correctly."""

    @pytest.mark.parametrize(
        "days, expected",
        [
            (15, "0-1 Month"),
            (60, "1-3 Months"),
            (120, "3-6 Months"),
            (300, "6-12 Months"),
            (500, "1-2 Years"),
            (1200, "2-5 Years"),
            (2800, "5-10 Years"),
            (5000, "10+ Years"),
        ],
    )
    def test_buckets(self, days, expected):
        assert categorize_duration(days) == expected

    def test_negative_returns_none(self):
        assert categorize_duration(-1) is None

    def test_nan_returns_none(self):
        assert categorize_duration(float("nan")) is None


# ---------------------------------------------------------------------------
# categorize_tenure
# ---------------------------------------------------------------------------


class TestCategorizeTenure:
    """categorize_tenure buckets days correctly."""

    @pytest.mark.parametrize(
        "days, expected",
        [
            (90, "0-6 Months"),
            (270, "6-12 Months"),
            (500, "1-2 Years"),
            (1200, "2-5 Years"),
            (2800, "5-10 Years"),
            (5000, "10+ Years"),
        ],
    )
    def test_buckets(self, days, expected):
        assert categorize_tenure(days) == expected

    def test_negative_returns_none(self):
        assert categorize_tenure(-1) is None


# ---------------------------------------------------------------------------
# categorize_balance
# ---------------------------------------------------------------------------


class TestCategorizeBalance:
    """categorize_balance buckets amounts correctly."""

    @pytest.mark.parametrize(
        "bal, expected",
        [
            (-100, "Negative"),
            (0, "$0"),
            (250, "$1-$499"),
            (750, "$500-$999"),
            (1500, "$1K-$2.5K"),
            (3000, "$2.5K-$5K"),
            (7000, "$5K-$10K"),
            (15000, "$10K+"),
        ],
    )
    def test_buckets(self, bal, expected):
        assert categorize_balance(bal) == expected

    def test_nan_returns_none(self):
        assert categorize_balance(float("nan")) is None


# ---------------------------------------------------------------------------
# product_col
# ---------------------------------------------------------------------------


class TestProductCol:
    """product_col detects the correct column name."""

    def test_product_code(self):
        df = pd.DataFrame({"Product Code": ["DDA"]})
        assert product_col(df) == "Product Code"

    def test_prod_code_fallback(self):
        df = pd.DataFrame({"Prod Code": ["DDA"]})
        assert product_col(df) == "Prod Code"

    def test_missing_returns_none(self):
        df = pd.DataFrame({"Other": [1]})
        assert product_col(df) is None


# ---------------------------------------------------------------------------
# prepare_attrition_data
# ---------------------------------------------------------------------------


class TestPrepareAttritionData:
    """prepare_attrition_data splits and caches correctly."""

    def test_splits_open_closed(self, attrition_ctx):
        all_data, open_accts, closed = prepare_attrition_data(attrition_ctx)
        assert len(all_data) == 60
        assert len(open_accts) == 30
        assert len(closed) == 30

    def test_closed_has_duration(self, attrition_ctx):
        _, _, closed = prepare_attrition_data(attrition_ctx)
        assert "_duration_days" in closed.columns
        assert "_duration_cat" in closed.columns

    def test_caches_result(self, attrition_ctx):
        r1 = prepare_attrition_data(attrition_ctx)
        r2 = prepare_attrition_data(attrition_ctx)
        assert r1 is r2

    def test_no_data_returns_empty(self, attrition_ctx):
        attrition_ctx.data = None
        all_d, open_a, closed = prepare_attrition_data(attrition_ctx)
        assert all_d.empty
        assert open_a.empty
        assert closed.empty
