"""Tests for M18-M22 new TXN analysis modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from txn_analysis.analyses.segment_helpers import (
    TIER_ORDER,
    classify_spending_tiers,
    detect_acct_col,
    extract_ars_segments,
    merge_segments_to_txn,
)
from txn_analysis.settings import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def odd_df() -> pd.DataFrame:
    """Minimal ODD with Segmentation column."""
    return pd.DataFrame(
        {
            "Acct Number": ["1001", "1002", "1003", "1004", "1005", "1006"],
            "Jan26 Segmentation": [
                "Responder",
                "Non-Responder",
                "Control",
                "Responder",
                "Non-Responder",
                "Control",
            ],
            "Account Holder Age": [25, 35, 45, 55, 30, 60],
            "Branch": ["Main", "West", "Main", "East", "West", "East"],
        }
    )


@pytest.fixture()
def txn_df() -> pd.DataFrame:
    """Minimal transaction data matching the ODD accounts."""
    rng = np.random.default_rng(42)
    n = 120
    return pd.DataFrame(
        {
            "primary_account_num": rng.choice(["1001", "1002", "1003", "1004", "1005", "1006"], n),
            "amount": rng.uniform(5, 500, n).round(2),
            "transaction_date": pd.date_range("2025-07-01", periods=n, freq="D").astype(str),
            "mcc_description": rng.choice(
                ["Groceries", "Gas", "Restaurants", "Travel", "Retail", "Healthcare"],
                n,
            ),
            "business_flag": rng.choice(["Yes", "No"], n, p=[0.3, 0.7]),
        }
    )


@pytest.fixture()
def settings() -> Settings:
    return Settings(data_file=None)


# ---------------------------------------------------------------------------
# Segment helpers tests
# ---------------------------------------------------------------------------


class TestSegmentHelpers:
    def test_detect_acct_col(self, odd_df: pd.DataFrame) -> None:
        assert detect_acct_col(odd_df) == "Acct Number"

    def test_detect_acct_col_missing(self) -> None:
        assert detect_acct_col(pd.DataFrame({"other": [1]})) is None

    def test_extract_3way(self, odd_df: pd.DataFrame) -> None:
        result = extract_ars_segments(odd_df)
        assert "Responder" in result
        assert "Non-Responder" in result
        assert "Control" in result
        assert len(result["Responder"]) == 2
        assert len(result["Non-Responder"]) == 2
        assert len(result["Control"]) == 2

    def test_extract_no_segmentation_cols(self) -> None:
        df = pd.DataFrame({"Acct Number": ["1001"], "Other": ["X"]})
        assert extract_ars_segments(df) == {}

    def test_extract_no_acct_col(self) -> None:
        df = pd.DataFrame({"Jan26 Segmentation": ["Responder"], "Other": [1]})
        assert extract_ars_segments(df) == {}

    def test_merge_to_txn(self, txn_df: pd.DataFrame, odd_df: pd.DataFrame) -> None:
        merged = merge_segments_to_txn(txn_df, odd_df)
        assert "ars_segment" in merged.columns
        assert set(merged["ars_segment"].unique()) <= {
            "Responder",
            "Non-Responder",
            "Control",
            "Unknown",
        }
        assert len(merged) == len(txn_df)

    def test_merge_no_segmentation(self, txn_df: pd.DataFrame) -> None:
        odd = pd.DataFrame({"Acct Number": ["1001"], "Other": ["X"]})
        merged = merge_segments_to_txn(txn_df, odd)
        assert (merged["ars_segment"] == "Unknown").all()

    def test_classify_tiers(self, txn_df: pd.DataFrame) -> None:
        result = classify_spending_tiers(txn_df)
        assert "spending_tier" in result.columns
        assert set(result["spending_tier"].unique()) <= set(TIER_ORDER)

    def test_classify_tiers_order(self, txn_df: pd.DataFrame) -> None:
        result = classify_spending_tiers(txn_df)
        for tier in result["spending_tier"].unique():
            assert tier in TIER_ORDER


# ---------------------------------------------------------------------------
# M18: Wallet Radar
# ---------------------------------------------------------------------------


class TestWalletRadar:
    def test_basic(self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.wallet_radar import analyze_wallet_radar

        ctx = {"odd_df": odd_df}
        result = analyze_wallet_radar(txn_df, txn_df, txn_df, settings, ctx)
        assert result.success
        assert result.name == "wallet_radar"
        assert not result.df.empty
        assert "Segment" in result.df.columns

    def test_no_odd(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.wallet_radar import analyze_wallet_radar

        result = analyze_wallet_radar(txn_df, txn_df, txn_df, settings, None)
        assert result.success  # Returns graceful note, not error
        assert "ODD" in result.df.iloc[0, 0] or "Note" in result.df.columns

    def test_no_mcc(self, odd_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.wallet_radar import analyze_wallet_radar

        df = pd.DataFrame(
            {"primary_account_num": ["1001"], "amount": [100], "business_flag": ["No"]}
        )
        result = analyze_wallet_radar(df, df, df, settings, {"odd_df": odd_df})
        assert result.success

    def test_category_completeness(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.wallet_radar import analyze_wallet_radar

        ctx = {"odd_df": odd_df}
        result = analyze_wallet_radar(txn_df, txn_df, txn_df, settings, ctx)
        assert "category_completeness" in result.data
        cc = result.data["category_completeness"]
        assert "Segment" in cc.columns
        assert "Completeness %" in cc.columns
        assert (cc["Completeness %"] >= 0).all()
        assert (cc["Completeness %"] <= 100).all()

    def test_summary_mentions_completeness(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.wallet_radar import analyze_wallet_radar

        ctx = {"odd_df": odd_df}
        result = analyze_wallet_radar(txn_df, txn_df, txn_df, settings, ctx)
        assert "completeness" in result.summary.lower()


# ---------------------------------------------------------------------------
# M19: Spending Trends
# ---------------------------------------------------------------------------


class TestSpendingTrends:
    def test_basic(self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.spending_trends import analyze_spending_trends

        result = analyze_spending_trends(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        assert result.success
        assert result.name == "spending_trends"
        assert "Week" in result.df.columns

    def test_insights_generated(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.spending_trends import analyze_spending_trends

        result = analyze_spending_trends(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        insights = result.metadata.get("insights", [])
        assert isinstance(insights, list)

    def test_no_odd(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.spending_trends import analyze_spending_trends

        result = analyze_spending_trends(txn_df, txn_df, txn_df, settings, None)
        assert result.success


# ---------------------------------------------------------------------------
# M20: Spending Profile
# ---------------------------------------------------------------------------


class TestSpendingProfile:
    def test_tiers(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.spending_profile import analyze_spending_profile

        result = analyze_spending_profile(txn_df, txn_df, txn_df, settings)
        assert result.success
        assert "Spending Tier" in result.df.columns
        tiers = set(result.df["Spending Tier"].tolist())
        assert tiers <= set(TIER_ORDER)

    def test_crosstab_with_odd(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.spending_profile import analyze_spending_profile

        result = analyze_spending_profile(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        assert result.success
        assert "segment_crosstab" in result.data

    def test_empty_df(self, settings: Settings) -> None:
        from txn_analysis.analyses.spending_profile import analyze_spending_profile

        empty = pd.DataFrame()
        result = analyze_spending_profile(empty, empty, empty, settings)
        assert result.error is not None


# ---------------------------------------------------------------------------
# M21: Transaction Distribution
# ---------------------------------------------------------------------------


class TestTxnDistribution:
    def test_stats(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        assert result.success
        assert "Spending Tier" in result.df.columns
        assert "Mean" in result.df.columns
        assert "Median" in result.df.columns

    def test_outlier_cap(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        raw = result.data.get("raw_amounts")
        if raw is not None and not raw.empty:
            cap = result.df["99th Pct Cap"].iloc[0]
            assert raw["amount"].max() <= cap + 0.01

    def test_empty_df(self, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution

        empty = pd.DataFrame()
        result = analyze_txn_distribution(empty, empty, empty, settings)
        assert result.error is not None

    def test_ticket_tiers(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        assert "ticket_tiers" in result.data
        tiers = result.data["ticket_tiers"]
        assert "Ticket Tier" in tiers.columns
        assert "% of Transactions" in tiers.columns
        assert "% of Spend" in tiers.columns
        # Sum of % should be ~100
        assert abs(tiers["% of Transactions"].sum() - 100.0) < 0.2

    def test_ticket_tier_order(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import (
            TICKET_TIER_ORDER,
            analyze_txn_distribution,
        )

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        tiers = result.data["ticket_tiers"]
        assert list(tiers["Ticket Tier"]) == TICKET_TIER_ORDER

    def test_monthly_trend(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        assert "monthly_trend" in result.data
        trend = result.data["monthly_trend"]
        assert "Month" in trend.columns
        assert "Avg Ticket" in trend.columns
        assert "Median Ticket" in trend.columns
        assert len(trend) > 0

    def test_metadata_enriched(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        assert "dominant_tier" in result.metadata
        assert "latest_avg_ticket" in result.metadata


# ---------------------------------------------------------------------------
# M22: Segment Comparison
# ---------------------------------------------------------------------------


class TestSegmentComparison:
    def test_metrics(self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.segment_comparison import analyze_segment_comparison

        result = analyze_segment_comparison(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        assert result.success
        assert "Segment" in result.df.columns
        assert "Avg Ticket" in result.df.columns

    def test_no_odd(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.segment_comparison import analyze_segment_comparison

        result = analyze_segment_comparison(txn_df, txn_df, txn_df, settings, None)
        assert result.success  # Returns note, not error


# ---------------------------------------------------------------------------
# Chart tests
# ---------------------------------------------------------------------------


class TestCharts:
    def test_wallet_radar_chart(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.wallet_radar import analyze_wallet_radar
        from txn_analysis.charts.wallet_radar import chart_wallet_radar
        from txn_analysis.settings import ChartConfig

        result = analyze_wallet_radar(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        fig = chart_wallet_radar(result, ChartConfig())
        assert fig is not None
        assert len(fig.get_axes()) > 0
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_spending_trends_chart(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.spending_trends import analyze_spending_trends
        from txn_analysis.charts.spending_trends import chart_spending_trends
        from txn_analysis.settings import ChartConfig

        result = analyze_spending_trends(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        fig = chart_spending_trends(result, ChartConfig())
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_violin_chart(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.txn_distribution import analyze_txn_distribution
        from txn_analysis.charts.txn_distribution import chart_txn_violin
        from txn_analysis.settings import ChartConfig

        result = analyze_txn_distribution(txn_df, txn_df, txn_df, settings)
        fig = chart_txn_violin(result, ChartConfig())
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_segment_comparison_chart(
        self, txn_df: pd.DataFrame, odd_df: pd.DataFrame, settings: Settings
    ) -> None:
        from txn_analysis.analyses.segment_comparison import analyze_segment_comparison
        from txn_analysis.charts.segment_comparison import chart_segment_comparison_bars
        from txn_analysis.settings import ChartConfig

        result = analyze_segment_comparison(txn_df, txn_df, txn_df, settings, {"odd_df": odd_df})
        fig = chart_segment_comparison_bars(result, ChartConfig())
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_spending_profile_table(self, txn_df: pd.DataFrame, settings: Settings) -> None:
        from txn_analysis.analyses.spending_profile import analyze_spending_profile
        from txn_analysis.charts.spending_profile import chart_spending_profile_table
        from txn_analysis.settings import ChartConfig

        result = analyze_spending_profile(txn_df, txn_df, txn_df, settings)
        fig = chart_spending_profile_table(result, ChartConfig())
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_analysis_registry_contains_m18_m22(self) -> None:
        from txn_analysis.analyses import ANALYSIS_REGISTRY

        names = [name for name, _ in ANALYSIS_REGISTRY]
        for expected in (
            "wallet_radar",
            "spending_trends",
            "spending_profile",
            "txn_distribution",
            "segment_comparison",
            "merchant_loyalty",
        ):
            assert expected in names, f"{expected} not in ANALYSIS_REGISTRY"

    def test_chart_registry_contains_m18_m22(self) -> None:
        from txn_analysis.charts import CHART_REGISTRY

        for expected in (
            "wallet_radar",
            "spending_trends",
            "spending_profile",
            "spending_profile:tiers",
            "txn_distribution",
            "segment_comparison",
        ):
            assert expected in CHART_REGISTRY, f"{expected} not in CHART_REGISTRY"

    def test_scorecard_still_last(self) -> None:
        from txn_analysis.analyses import ANALYSIS_REGISTRY

        names = [name for name, _ in ANALYSIS_REGISTRY]
        assert names[-1] == "portfolio_scorecard"
