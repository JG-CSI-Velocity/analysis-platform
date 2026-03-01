"""M18: Share of wallet radar -- MCC category spend distribution by ARS segment.

Produces a radar / spider chart comparing how each ARS segment
(Responder / Non-Responder / Control) allocates its spend across
the top MCC categories.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import SEGMENT_ORDER, merge_segments_to_txn
from txn_analysis.settings import Settings

_MAX_CATEGORIES = 10


def analyze_wallet_radar(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Compute share-of-wallet by MCC category per ARS segment."""
    ctx = context or {}
    odd_df = ctx.get("odd_df")

    if odd_df is None or (isinstance(odd_df, pd.DataFrame) and odd_df.empty):
        return AnalysisResult.from_df(
            "wallet_radar",
            "Share of Wallet Analysis",
            pd.DataFrame({"Note": ["ODD data required for segment analysis"]}),
            metadata={"sheet_name": "M18 Wallet"},
        )

    if df.empty or "amount" not in df.columns:
        return AnalysisResult.from_df(
            "wallet_radar",
            "Share of Wallet Analysis",
            pd.DataFrame(),
            error="No transaction data available",
        )

    if "mcc_description" not in df.columns:
        return AnalysisResult.from_df(
            "wallet_radar",
            "Share of Wallet Analysis",
            pd.DataFrame({"Note": ["MCC description column required"]}),
            metadata={"sheet_name": "M18 Wallet"},
        )

    merged = merge_segments_to_txn(df, odd_df)
    known = merged[merged["ars_segment"] != "Unknown"]

    if known.empty:
        return AnalysisResult.from_df(
            "wallet_radar",
            "Share of Wallet Analysis",
            pd.DataFrame({"Note": ["No accounts matched between ODD and transactions"]}),
            metadata={"sheet_name": "M18 Wallet"},
        )

    # Determine top N MCC categories by total spend (across all segments)
    top_mccs = (
        known.groupby("mcc_description")["amount"].sum().nlargest(_MAX_CATEGORIES).index.tolist()
    )

    # Compute % share per segment per MCC category
    rows: list[dict] = []
    for seg in SEGMENT_ORDER:
        seg_df = known[known["ars_segment"] == seg]
        if seg_df.empty:
            continue

        seg_total = seg_df["amount"].sum()
        if seg_total == 0:
            continue

        row: dict = {"Segment": seg}
        for mcc in top_mccs:
            mcc_spend = seg_df[seg_df["mcc_description"] == mcc]["amount"].sum()
            row[mcc] = round(mcc_spend / seg_total * 100, 1)
        rows.append(row)

    result_df = pd.DataFrame(rows)

    meta: dict = {
        "sheet_name": "M18 Wallet",
        "category": "Wallet Analysis",
        "chart_id": "M18",
        "mcc_categories": top_mccs,
    }

    summary = f"Top {len(top_mccs)} MCC categories analysed across {len(rows)} segments"

    return AnalysisResult(
        name="wallet_radar",
        title="Share of Wallet Analysis",
        data={"main": result_df},
        metadata=meta,
        summary=summary,
    )
