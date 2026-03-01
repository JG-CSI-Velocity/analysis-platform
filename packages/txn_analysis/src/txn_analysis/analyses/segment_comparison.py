"""M22: Segment behavioral comparison -- cross-segment metrics.

Computes key behavioral metrics for each ARS segment
(Responder / Non-Responder / Control) to highlight differences
in transaction volume, spend, and category concentration.
"""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.analyses.segment_helpers import SEGMENT_ORDER, merge_segments_to_txn
from txn_analysis.settings import Settings


def analyze_segment_comparison(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Compare behavioral metrics across ARS segments."""
    ctx = context or {}
    odd_df = ctx.get("odd_df")

    if odd_df is None or (isinstance(odd_df, pd.DataFrame) and odd_df.empty):
        return AnalysisResult.from_df(
            "segment_comparison",
            "Segment Behavioral Comparison",
            pd.DataFrame({"Note": ["ODD data required for segment comparison"]}),
            metadata={"sheet_name": "M22 Comparison"},
        )

    if df.empty or "amount" not in df.columns:
        return AnalysisResult.from_df(
            "segment_comparison",
            "Segment Behavioral Comparison",
            pd.DataFrame(),
            error="No transaction data available",
        )

    merged = merge_segments_to_txn(df, odd_df)
    known = merged[merged["ars_segment"] != "Unknown"]

    if known.empty:
        return AnalysisResult.from_df(
            "segment_comparison",
            "Segment Behavioral Comparison",
            pd.DataFrame({"Note": ["No accounts matched between ODD and transactions"]}),
            metadata={"sheet_name": "M22 Comparison"},
        )

    rows: list[dict] = []
    for seg in SEGMENT_ORDER:
        seg_df = known[known["ars_segment"] == seg]
        if seg_df.empty:
            continue

        n_accts = seg_df["primary_account_num"].nunique()
        n_txns = len(seg_df)
        total_spend = seg_df["amount"].sum()
        avg_ticket = seg_df["amount"].mean()
        avg_txns_per_acct = n_txns / n_accts if n_accts else 0
        avg_monthly_spend = total_spend / n_accts if n_accts else 0

        # Top MCC and concentration
        top_mcc = "N/A"
        top3_pct = 0.0
        if "mcc_description" in seg_df.columns:
            mcc_spend = (
                seg_df.groupby("mcc_description")["amount"].sum().sort_values(ascending=False)
            )
            if not mcc_spend.empty:
                top_mcc = mcc_spend.index[0]
                top3_pct = (
                    round(mcc_spend.head(3).sum() / total_spend * 100, 1) if total_spend else 0
                )

        rows.append(
            {
                "Segment": seg,
                "Accounts": n_accts,
                "Avg Txns/Account": round(avg_txns_per_acct, 1),
                "Avg Monthly Spend": round(avg_monthly_spend, 2),
                "Avg Ticket": round(avg_ticket, 2),
                "Top Category": top_mcc,
                "Top 3 MCC Concentration": f"{top3_pct}%",
            }
        )

    result_df = pd.DataFrame(rows)

    summary = ""
    if len(rows) >= 2:
        resp = next((r for r in rows if r["Segment"] == "Responder"), None)
        non_resp = next((r for r in rows if r["Segment"] == "Non-Responder"), None)
        if resp and non_resp and non_resp["Avg Ticket"] > 0:
            lift = (resp["Avg Ticket"] - non_resp["Avg Ticket"]) / non_resp["Avg Ticket"] * 100
            summary = f"Responder avg ticket is {lift:+.1f}% vs Non-Responder"

    return AnalysisResult(
        name="segment_comparison",
        title="Segment Behavioral Comparison",
        data={"main": result_df},
        metadata={
            "sheet_name": "M22 Comparison",
            "category": "Spending Intelligence",
            "chart_id": "M22",
        },
        summary=summary or "Cross-segment behavioral metrics",
    )
