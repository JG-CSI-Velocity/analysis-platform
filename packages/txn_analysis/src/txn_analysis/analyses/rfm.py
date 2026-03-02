"""M25: RFM (Recency/Frequency/Monetary) segmentation of cardholders.

Scores each account on 3 dimensions using quartiles, maps to named segments,
and optionally compares pre-mailer vs post-mailer segment migration.

Pure TXN analysis; ODD optional for pre/post comparison.

Executive presentation: Headlines are conclusions, not labels.
"""

from __future__ import annotations

import logging

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)

SCORE_BINS = 4  # quartiles

# Named segments based on R + F scores (monetary implicit in F)
_SEGMENT_MAP = {
    (4, 4): "Champions",
    (4, 3): "Champions",
    (3, 4): "Loyal",
    (3, 3): "Loyal",
    (4, 2): "Potential Loyal",
    (3, 2): "Potential Loyal",
    (4, 1): "Recent",
    (3, 1): "Need Attention",
    (2, 4): "At-Risk Champions",
    (2, 3): "At-Risk",
    (2, 2): "About to Lose",
    (2, 1): "About to Lose",
    (1, 4): "Hibernating",
    (1, 3): "Hibernating",
    (1, 2): "Lost",
    (1, 1): "Lost",
}


def _safe_qcut(series: pd.Series, q: int) -> pd.Series:
    """Rank-based qcut that handles duplicate bin edges gracefully."""
    ranked = series.rank(method="first", pct=True)
    bins = [i / q for i in range(q + 1)]
    labels = list(range(1, q + 1))
    return pd.cut(ranked, bins=bins, labels=labels, include_lowest=True).astype(int)


def compute_rfm(txn_df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    """Compute RFM scores for each account.

    Returns DataFrame with columns: account, recency_days, frequency, monetary,
    r_score, f_score, m_score, rfm_segment.
    """
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce", format="mixed")
    work = txn_df[dt.notna()].copy()
    work["txn_date"] = dt[dt.notna()]
    work["acct_str"] = work["primary_account_num"].astype(str).str.strip()

    if work.empty:
        return pd.DataFrame()

    rfm = (
        work.groupby("acct_str", sort=False)
        .agg(
            recency_days=("txn_date", lambda x: (snapshot_date - x.max()).days),
            frequency=("txn_date", "count"),
            monetary=("amount", "sum"),
        )
        .reset_index()
    )
    rfm.rename(columns={"acct_str": "account"}, inplace=True)

    if len(rfm) < SCORE_BINS:
        # Not enough data for quartile scoring
        return pd.DataFrame()

    # Score: high R = recent (low recency_days), high F/M = good
    rfm["r_score"] = _safe_qcut(rfm["recency_days"].rank(ascending=False, method="first"), SCORE_BINS)
    rfm["f_score"] = _safe_qcut(rfm["frequency"], SCORE_BINS)
    rfm["m_score"] = _safe_qcut(rfm["monetary"], SCORE_BINS)

    # Map to named segments
    rfm["rfm_segment"] = rfm.apply(
        lambda row: _SEGMENT_MAP.get((row["r_score"], row["f_score"]), "Other"), axis=1
    )

    rfm["recency_days"] = rfm["recency_days"].astype(int)
    rfm["monetary"] = rfm["monetary"].round(2)

    return rfm


# ---------------------------------------------------------------------------
# M25.1 -- RFM Heatmap
# ---------------------------------------------------------------------------


def _build_rfm_heatmap(rfm: pd.DataFrame) -> pd.DataFrame:
    """Build R x F grid with average monetary value in each cell."""
    if rfm.empty:
        return pd.DataFrame()

    pivot = (
        rfm.groupby(["r_score", "f_score"])["monetary"]
        .mean()
        .round(2)
        .reset_index()
    )
    pivot.columns = ["Recency Score", "Frequency Score", "Avg Monetary"]

    # Also add count
    counts = rfm.groupby(["r_score", "f_score"]).size().reset_index(name="Count")
    pivot = pivot.merge(counts, left_on=["Recency Score", "Frequency Score"],
                        right_on=["r_score", "f_score"])
    pivot.drop(columns=["r_score", "f_score"], inplace=True)

    return pivot


# ---------------------------------------------------------------------------
# M25.2 -- Segment Distribution
# ---------------------------------------------------------------------------


def _build_segment_distribution(rfm: pd.DataFrame) -> pd.DataFrame:
    """Named segment distribution with key metrics."""
    if rfm.empty:
        return pd.DataFrame()

    segments = (
        rfm.groupby("rfm_segment")
        .agg(
            accounts=("account", "count"),
            avg_monetary=("monetary", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_recency=("recency_days", "mean"),
        )
        .reset_index()
        .sort_values("accounts", ascending=False)
    )

    total = segments["accounts"].sum()
    segments["pct"] = (segments["accounts"] / total * 100).round(1) if total else 0
    segments["avg_monetary"] = segments["avg_monetary"].round(2)
    segments["avg_frequency"] = segments["avg_frequency"].round(1)
    segments["avg_recency"] = segments["avg_recency"].round(0)

    segments.columns = [
        "Segment",
        "Accounts",
        "Avg Spend",
        "Avg Txns",
        "Avg Recency (days)",
        "% of Total",
    ]
    return segments


# ---------------------------------------------------------------------------
# M25.3 -- RFM Migration (requires pre/post split)
# ---------------------------------------------------------------------------


def _build_rfm_migration(
    txn_df: pd.DataFrame, cutoff: pd.Timestamp
) -> pd.DataFrame | None:
    """Compare RFM segments before vs after cutoff date.

    Returns migration matrix showing segment shifts.
    """
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce", format="mixed")
    work = txn_df[dt.notna()].copy()
    work["txn_date"] = dt[dt.notna()]

    pre = work[work["txn_date"] < cutoff]
    post = work[work["txn_date"] >= cutoff]

    if pre.empty or post.empty:
        return None

    pre_rfm = compute_rfm(pre, cutoff)
    post_rfm = compute_rfm(post, work["txn_date"].max())

    if pre_rfm.empty or post_rfm.empty:
        return None

    merged = pre_rfm[["account", "rfm_segment"]].merge(
        post_rfm[["account", "rfm_segment"]],
        on="account",
        suffixes=("_pre", "_post"),
    )

    if merged.empty:
        return None

    # Build migration matrix
    migration = (
        merged.groupby(["rfm_segment_pre", "rfm_segment_post"])
        .size()
        .reset_index(name="count")
    )
    migration.columns = ["Pre-Mailer Segment", "Post-Mailer Segment", "Accounts"]

    return migration


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_rfm(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Perform RFM segmentation on transaction data.

    Pure TXN analysis. ODD is used only if available for pre/post migration.
    """
    dt = pd.to_datetime(df["transaction_date"], errors="coerce", format="mixed")
    valid = df[dt.notna()]

    if valid.empty or "amount" not in df.columns:
        return AnalysisResult.from_df(
            "rfm",
            "RFM Segmentation",
            pd.DataFrame(),
            error="No valid transaction data for RFM",
            metadata={"sheet_name": "M25 RFM", "chart_id": "M25"},
        )

    snapshot = dt.max()
    rfm = compute_rfm(df, snapshot)

    if rfm.empty:
        return AnalysisResult.from_df(
            "rfm",
            "RFM Segmentation",
            pd.DataFrame({"Note": ["Insufficient accounts for RFM scoring"]}),
            metadata={"sheet_name": "M25 RFM", "chart_id": "M25"},
        )

    data: dict[str, pd.DataFrame] = {}
    summary_parts: list[str] = []

    # M25.1 -- Heatmap
    heatmap = _build_rfm_heatmap(rfm)
    if not heatmap.empty:
        data["heatmap"] = heatmap

    # M25.2 -- Segment Distribution
    seg_dist = _build_segment_distribution(rfm)
    if not seg_dist.empty:
        data["main"] = seg_dist

        # Key insights
        champions = seg_dist[seg_dist["Segment"] == "Champions"]
        at_risk = seg_dist[seg_dist["Segment"].isin(["At-Risk", "At-Risk Champions"])]
        lost = seg_dist[seg_dist["Segment"] == "Lost"]

        if not champions.empty:
            champ_pct = champions.iloc[0]["% of Total"]
            summary_parts.append(f"{champ_pct:.0f}% are Champions (high recency + frequency)")
        if not at_risk.empty:
            at_risk_n = at_risk["Accounts"].sum()
            summary_parts.append(f"{at_risk_n:,} accounts at-risk -- retention priority")
        if not lost.empty:
            lost_n = int(lost.iloc[0]["Accounts"])
            summary_parts.append(f"{lost_n:,} accounts classified as Lost")

    # M25.3 -- Migration (if cutoff available)
    ctx = context or {}
    odd_df = ctx.get("odd_df")
    migration = None
    if odd_df is not None:
        # Use midpoint of data as cutoff for pre/post comparison
        midpoint = dt.min() + (dt.max() - dt.min()) / 2
        migration = _build_rfm_migration(df, midpoint)
        if migration is not None:
            data["migration"] = migration
            # Count upgrades vs downgrades
            upgrades = migration[
                migration.apply(
                    lambda r: _segment_rank(r["Post-Mailer Segment"])
                    > _segment_rank(r["Pre-Mailer Segment"]),
                    axis=1,
                )
            ]["Accounts"].sum()
            downgrades = migration[
                migration.apply(
                    lambda r: _segment_rank(r["Post-Mailer Segment"])
                    < _segment_rank(r["Pre-Mailer Segment"]),
                    axis=1,
                )
            ]["Accounts"].sum()
            if upgrades + downgrades > 0:
                summary_parts.append(
                    f"{upgrades:,} accounts upgraded, {downgrades:,} downgraded across period"
                )

    if "main" not in data:
        data["main"] = rfm[["account", "r_score", "f_score", "m_score", "rfm_segment"]]

    # Executive headline
    total_accounts = len(rfm)
    headline = f"RFM Segmentation -- {total_accounts:,} cardholders scored"
    if not seg_dist.empty:
        top_seg = seg_dist.iloc[0]
        headline = (
            f"{top_seg['Segment']} is the largest segment ({top_seg['% of Total']:.0f}%) "
            f"-- {total_accounts:,} cardholders scored"
        )

    meta = {
        "sheet_name": "M25 RFM",
        "chart_id": "M25",
        "category": "Cardholder Intelligence",
        "total_accounts": total_accounts,
        "segment_count": len(seg_dist) if not seg_dist.empty else 0,
    }

    return AnalysisResult(
        name="rfm",
        title=headline,
        data=data,
        metadata=meta,
        summary=". ".join(summary_parts) if summary_parts else "RFM segmentation analysis",
    )


def _segment_rank(segment: str) -> int:
    """Rank segments for upgrade/downgrade comparison."""
    ranking = {
        "Champions": 7,
        "Loyal": 6,
        "Potential Loyal": 5,
        "Recent": 4,
        "Need Attention": 3,
        "At-Risk Champions": 3,
        "At-Risk": 2,
        "About to Lose": 2,
        "Hibernating": 1,
        "Lost": 0,
    }
    return ranking.get(segment, 0)
