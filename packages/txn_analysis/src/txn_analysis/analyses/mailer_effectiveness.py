"""M23: Mailer effectiveness measurement via transaction data.

Compares pre-mailer and post-mailer spending for responders vs non-responders
using Difference-in-Differences (DiD), Interrupted Time Series (ITS),
effect decay estimation, and cumulative incremental spend analysis.

Requires ODD data in context["odd_df"] for responder/non-responder classification.

Executive presentation: Headlines are conclusions, not labels.
"""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)

# Successful ARS response tiers (score >= 2 in ladder)
_RESPONSE_TIERS = {"NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"}

# Default analysis windows
_PRE_MONTHS = 6
_POST_MONTHS = 6
_MIN_TXN_COUNT = 3


# ---------------------------------------------------------------------------
# ODD helpers
# ---------------------------------------------------------------------------


def _detect_acct_col(odd_df: pd.DataFrame) -> str | None:
    for col in ("Acct Number", "Account Number", "Account_Number"):
        if col in odd_df.columns:
            return col
    return None


def _detect_resp_pairs(odd_df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Find (month_str, resp_col, mail_col) pairs in ODD columns."""
    cols = list(odd_df.columns)
    mail_cols = sorted(
        [c for c in cols if re.match(r"^[A-Z][a-z]{2}\d{2} Mail$", c)],
        key=lambda c: c[:5],
    )
    pairs: list[tuple[str, str, str]] = []
    for mc in mail_cols:
        month = mc.replace(" Mail", "")
        rc = f"{month} Resp"
        if rc in cols:
            pairs.append((month, rc, mc))
    return pairs


def _classify_accounts(
    odd_df: pd.DataFrame, acct_col: str, pairs: list[tuple[str, str, str]]
) -> tuple[set[str], set[str], pd.Timestamp | None]:
    """Classify accounts as responders or non-responders and find earliest mailer date.

    An account is a responder if it has a successful response tier in ANY mailer month.
    Returns (responder_accts, non_responder_accts, earliest_mailer_date).
    """
    responders: set[str] = set()
    mailed: set[str] = set()
    earliest_date: pd.Timestamp | None = None

    for month_str, resp_col, mail_col in pairs:
        # Parse month
        try:
            month_dt = pd.to_datetime(month_str, format="%b%y")
        except Exception:
            continue

        if earliest_date is None or month_dt < earliest_date:
            earliest_date = month_dt

        mailed_mask = odd_df[mail_col].notna() & (odd_df[mail_col].astype(str).str.strip() != "")
        month_mailed = set(odd_df.loc[mailed_mask, acct_col].astype(str).str.strip())
        mailed |= month_mailed

        resp_mask = mailed_mask & odd_df[resp_col].isin(_RESPONSE_TIERS)
        month_resp = set(odd_df.loc[resp_mask, acct_col].astype(str).str.strip())
        responders |= month_resp

    non_responders = mailed - responders
    return responders, non_responders, earliest_date


def _build_monthly_spend(
    txn_df: pd.DataFrame,
    responders: set[str],
    non_responders: set[str],
) -> pd.DataFrame:
    """Build per-account monthly spend aggregates with group labels.

    Returns DataFrame with columns: account, year_month, spend, txn_count, group.
    """
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce", format="mixed")
    work = txn_df[dt.notna()].copy()
    work["txn_date"] = dt[dt.notna()]
    work["year_month"] = work["txn_date"].dt.to_period("M")
    work["acct_str"] = work["primary_account_num"].astype(str).str.strip()

    # Filter to mailed accounts only
    all_accts = responders | non_responders
    work = work[work["acct_str"].isin(all_accts)]

    if work.empty:
        return pd.DataFrame(columns=["account", "year_month", "spend", "txn_count", "group"])

    monthly = (
        work.groupby(["acct_str", "year_month"])
        .agg(spend=("amount", "sum"), txn_count=("amount", "count"))
        .reset_index()
    )
    monthly.rename(columns={"acct_str": "account"}, inplace=True)
    monthly["group"] = monthly["account"].apply(
        lambda a: "Responder" if a in responders else "Non-Responder"
    )
    return monthly


def _split_pre_post(
    monthly: pd.DataFrame, cutoff: pd.Timestamp, pre_months: int, post_months: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split monthly spend data into pre and post periods relative to cutoff."""
    cutoff_period = pd.Period(cutoff, freq="M")
    pre_start = cutoff_period - pre_months
    post_end = cutoff_period + post_months - 1

    pre = monthly[
        (monthly["year_month"] >= pre_start) & (monthly["year_month"] < cutoff_period)
    ]
    post = monthly[
        (monthly["year_month"] >= cutoff_period) & (monthly["year_month"] <= post_end)
    ]
    return pre, post


# ---------------------------------------------------------------------------
# M23.1 -- Difference-in-Differences
# ---------------------------------------------------------------------------


def _compute_did(pre: pd.DataFrame, post: pd.DataFrame) -> dict:
    """Compute DiD estimate: (post_resp - pre_resp) - (post_ctrl - pre_ctrl)."""
    resp_pre = pre[pre["group"] == "Responder"]["spend"].mean() if not pre.empty else 0
    resp_post = post[post["group"] == "Responder"]["spend"].mean() if not post.empty else 0
    ctrl_pre = pre[pre["group"] == "Non-Responder"]["spend"].mean() if not pre.empty else 0
    ctrl_post = post[post["group"] == "Non-Responder"]["spend"].mean() if not post.empty else 0

    resp_delta = resp_post - resp_pre
    ctrl_delta = ctrl_post - ctrl_pre
    did = resp_delta - ctrl_delta

    return {
        "resp_pre_avg": round(resp_pre, 2),
        "resp_post_avg": round(resp_post, 2),
        "ctrl_pre_avg": round(ctrl_pre, 2),
        "ctrl_post_avg": round(ctrl_post, 2),
        "resp_delta": round(resp_delta, 2),
        "ctrl_delta": round(ctrl_delta, 2),
        "did_estimate": round(did, 2),
        "did_pct": round(did / resp_pre * 100, 1) if resp_pre else 0.0,
    }


def _build_did_table(did: dict) -> pd.DataFrame:
    """Build a presentation-ready DiD summary table."""
    return pd.DataFrame(
        [
            {
                "Metric": "Pre-Mailer Avg Monthly Spend",
                "Responders": f"${did['resp_pre_avg']:,.2f}",
                "Non-Responders": f"${did['ctrl_pre_avg']:,.2f}",
            },
            {
                "Metric": "Post-Mailer Avg Monthly Spend",
                "Responders": f"${did['resp_post_avg']:,.2f}",
                "Non-Responders": f"${did['ctrl_post_avg']:,.2f}",
            },
            {
                "Metric": "Change",
                "Responders": f"${did['resp_delta']:+,.2f}",
                "Non-Responders": f"${did['ctrl_delta']:+,.2f}",
            },
            {
                "Metric": "DiD Estimate (Incremental Lift)",
                "Responders": f"${did['did_estimate']:+,.2f}",
                "Non-Responders": "--",
            },
        ]
    )


# ---------------------------------------------------------------------------
# M23.2 -- DiD by Segment
# ---------------------------------------------------------------------------


def _compute_did_by_segment(
    monthly: pd.DataFrame,
    cutoff: pd.Timestamp,
    odd_df: pd.DataFrame,
    acct_col: str,
    pre_months: int,
    post_months: int,
) -> pd.DataFrame:
    """Break DiD down by balance tier."""
    if "balance_tier" not in odd_df.columns:
        return pd.DataFrame()

    acct_tier = odd_df[[acct_col, "balance_tier"]].dropna(subset=["balance_tier"]).copy()
    acct_tier[acct_col] = acct_tier[acct_col].astype(str).str.strip()
    acct_tier.rename(columns={acct_col: "account"}, inplace=True)

    merged = monthly.merge(acct_tier, on="account", how="inner")
    if merged.empty:
        return pd.DataFrame()

    pre, post = _split_pre_post(merged, cutoff, pre_months, post_months)

    rows: list[dict] = []
    for tier in sorted(merged["balance_tier"].unique()):
        tier_pre = pre[pre["balance_tier"] == tier]
        tier_post = post[post["balance_tier"] == tier]

        did = _compute_did(tier_pre, tier_post)
        rows.append(
            {
                "Balance Tier": tier,
                "DiD Estimate": did["did_estimate"],
                "Responder Lift %": did["did_pct"],
                "Resp Pre Avg": did["resp_pre_avg"],
                "Resp Post Avg": did["resp_post_avg"],
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# M23.3 -- Interrupted Time Series
# ---------------------------------------------------------------------------


def _compute_its(monthly: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Fit pre-trend + post-intercept + post-slope for responders.

    Returns a DataFrame with columns: year_month, actual_spend, fitted, counterfactual.
    """
    resp = monthly[monthly["group"] == "Responder"]
    if resp.empty:
        return pd.DataFrame()

    agg = resp.groupby("year_month")["spend"].mean().sort_index().reset_index()
    agg["period_num"] = range(len(agg))
    cutoff_period = pd.Period(cutoff, freq="M")
    agg["post"] = (agg["year_month"] >= cutoff_period).astype(int)

    # Find the cutoff index
    pre_mask = agg["post"] == 0
    post_mask = agg["post"] == 1

    if pre_mask.sum() < 2 or post_mask.sum() < 1:
        return pd.DataFrame()

    # Simple OLS for pre-trend
    pre_data = agg[pre_mask]
    x_pre = pre_data["period_num"].values.astype(float)
    y_pre = pre_data["spend"].values.astype(float)

    if len(x_pre) >= 2:
        slope_pre = np.polyfit(x_pre, y_pre, 1)
        fitted_pre = np.polyval(slope_pre, agg["period_num"].values)
    else:
        fitted_pre = np.full(len(agg), y_pre.mean())
        slope_pre = [0, y_pre.mean()]

    # Counterfactual: extend pre-trend into post period
    counterfactual = np.polyval(slope_pre, agg["period_num"].values)

    # Post-period actual
    agg["actual_spend"] = agg["spend"]
    agg["counterfactual"] = counterfactual.round(2)
    agg["fitted"] = fitted_pre.round(2)
    agg["year_month_str"] = agg["year_month"].astype(str)

    return agg[["year_month_str", "actual_spend", "fitted", "counterfactual", "post"]].rename(
        columns={"year_month_str": "Month"}
    )


# ---------------------------------------------------------------------------
# M23.4 -- Effect Decay
# ---------------------------------------------------------------------------


def _compute_decay(
    monthly: pd.DataFrame, cutoff: pd.Timestamp, post_months: int
) -> pd.DataFrame:
    """Compute monthly lift (resp - ctrl) in post period, fit exponential decay."""
    cutoff_period = pd.Period(cutoff, freq="M")
    post_end = cutoff_period + post_months - 1

    post = monthly[
        (monthly["year_month"] >= cutoff_period) & (monthly["year_month"] <= post_end)
    ]
    if post.empty:
        return pd.DataFrame()

    resp_monthly = (
        post[post["group"] == "Responder"].groupby("year_month")["spend"].mean()
    )
    ctrl_monthly = (
        post[post["group"] == "Non-Responder"].groupby("year_month")["spend"].mean()
    )

    months_post = sorted(set(resp_monthly.index) & set(ctrl_monthly.index))
    if len(months_post) < 2:
        return pd.DataFrame()

    rows: list[dict] = []
    for i, m in enumerate(months_post):
        lift = resp_monthly[m] - ctrl_monthly[m]
        rows.append(
            {
                "Month": str(m),
                "Months Post-Mailer": i + 1,
                "Responder Avg": round(resp_monthly[m], 2),
                "Non-Responder Avg": round(ctrl_monthly[m], 2),
                "Lift": round(lift, 2),
            }
        )

    df = pd.DataFrame(rows)

    # Fit exponential decay if enough data points with positive lift
    positive_lifts = df[df["Lift"] > 0]
    if len(positive_lifts) >= 2:
        x = positive_lifts["Months Post-Mailer"].values.astype(float)
        y = positive_lifts["Lift"].values.astype(float)
        try:
            log_y = np.log(y)
            coeffs = np.polyfit(x, log_y, 1)
            decay_rate = coeffs[0]
            half_life = -np.log(2) / decay_rate if decay_rate < 0 else float("inf")
            df.attrs["decay_rate"] = round(float(decay_rate), 4)
            df.attrs["half_life_months"] = round(float(half_life), 1)
        except (ValueError, np.linalg.LinAlgError):
            df.attrs["decay_rate"] = None
            df.attrs["half_life_months"] = None
    else:
        df.attrs["decay_rate"] = None
        df.attrs["half_life_months"] = None

    return df


# ---------------------------------------------------------------------------
# M23.5 -- Cumulative Incremental Spend
# ---------------------------------------------------------------------------


def _compute_cumulative_incremental(
    monthly: pd.DataFrame, cutoff: pd.Timestamp, post_months: int
) -> pd.DataFrame:
    """Running sum of incremental dollars (treatment actual - counterfactual)."""
    cutoff_period = pd.Period(cutoff, freq="M")
    post_end = cutoff_period + post_months - 1

    post = monthly[
        (monthly["year_month"] >= cutoff_period) & (monthly["year_month"] <= post_end)
    ]
    if post.empty:
        return pd.DataFrame()

    resp = post[post["group"] == "Responder"]
    ctrl = post[post["group"] == "Non-Responder"]

    resp_agg = resp.groupby("year_month").agg(
        resp_total=("spend", "sum"), resp_accounts=("account", "nunique")
    )
    ctrl_agg = ctrl.groupby("year_month").agg(
        ctrl_avg=("spend", "mean")
    )

    months = sorted(set(resp_agg.index) & set(ctrl_agg.index))
    if not months:
        return pd.DataFrame()

    rows: list[dict] = []
    cumulative = 0.0
    for m in months:
        resp_total = resp_agg.loc[m, "resp_total"]
        resp_n = resp_agg.loc[m, "resp_accounts"]
        ctrl_avg = ctrl_agg.loc[m, "ctrl_avg"]
        # Incremental = actual responder total - (responder count * control avg)
        counterfactual_total = resp_n * ctrl_avg
        incremental = resp_total - counterfactual_total
        cumulative += incremental
        rows.append(
            {
                "Month": str(m),
                "Responder Total": round(resp_total, 2),
                "Counterfactual": round(counterfactual_total, 2),
                "Incremental": round(incremental, 2),
                "Cumulative Incremental": round(cumulative, 2),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# M23.6 -- Lift Distribution
# ---------------------------------------------------------------------------


def _compute_lift_distribution(
    monthly: pd.DataFrame,
    cutoff: pd.Timestamp,
    pre_months: int,
    post_months: int,
    min_txn: int,
) -> pd.DataFrame:
    """Per-account lift: (post avg - pre avg) for responders vs non-responders."""
    pre, post = _split_pre_post(monthly, cutoff, pre_months, post_months)

    # Compute per-account pre/post averages
    pre_avg = pre.groupby(["account", "group"])["spend"].mean().reset_index()
    pre_avg.rename(columns={"spend": "pre_avg"}, inplace=True)

    post_avg = post.groupby(["account", "group"])["spend"].mean().reset_index()
    post_avg.rename(columns={"spend": "post_avg"}, inplace=True)

    # Need accounts with both pre and post data
    merged = pre_avg.merge(post_avg, on=["account", "group"], how="inner")

    # Filter by minimum transaction count
    pre_counts = pre.groupby("account")["txn_count"].sum().reset_index()
    pre_counts.rename(columns={"txn_count": "pre_txn_count"}, inplace=True)
    merged = merged.merge(pre_counts, on="account", how="left")
    merged = merged[merged["pre_txn_count"] >= min_txn]

    if merged.empty:
        return pd.DataFrame()

    merged["lift"] = (merged["post_avg"] - merged["pre_avg"]).round(2)
    merged["lift_pct"] = ((merged["lift"] / merged["pre_avg"]) * 100).round(1)
    merged.loc[merged["pre_avg"] == 0, "lift_pct"] = 0.0

    return merged[["account", "group", "pre_avg", "post_avg", "lift", "lift_pct"]]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_mailer_effectiveness(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Measure mailer effectiveness via transaction data (DiD, ITS, decay).

    Requires context["odd_df"] for responder/non-responder classification.
    """
    ctx = context or {}
    odd_df = ctx.get("odd_df")

    if odd_df is None or (isinstance(odd_df, pd.DataFrame) and odd_df.empty):
        return AnalysisResult.from_df(
            "mailer_effectiveness",
            "Mailer Effectiveness Analysis",
            pd.DataFrame({"Note": ["ODD data required for mailer effectiveness"]}),
            metadata={"sheet_name": "M23 Effectiveness", "chart_id": "M23"},
        )

    acct_col = _detect_acct_col(odd_df)
    if acct_col is None:
        return AnalysisResult.from_df(
            "mailer_effectiveness",
            "Mailer Effectiveness Analysis",
            pd.DataFrame({"Note": ["No account number column in ODD"]}),
            metadata={"sheet_name": "M23 Effectiveness", "chart_id": "M23"},
        )

    pairs = _detect_resp_pairs(odd_df)
    if not pairs:
        return AnalysisResult.from_df(
            "mailer_effectiveness",
            "Mailer Effectiveness Analysis",
            pd.DataFrame({"Note": ["No mailer response columns found in ODD"]}),
            metadata={"sheet_name": "M23 Effectiveness", "chart_id": "M23"},
        )

    responders, non_responders, earliest_date = _classify_accounts(odd_df, acct_col, pairs)
    if not responders or not non_responders:
        return AnalysisResult.from_df(
            "mailer_effectiveness",
            "Mailer Effectiveness Analysis",
            pd.DataFrame({"Note": ["Need both responders and non-responders for DiD"]}),
            metadata={"sheet_name": "M23 Effectiveness", "chart_id": "M23"},
        )

    monthly = _build_monthly_spend(df, responders, non_responders)
    if monthly.empty:
        return AnalysisResult.from_df(
            "mailer_effectiveness",
            "Mailer Effectiveness Analysis",
            pd.DataFrame({"Note": ["No matching transactions for mailed accounts"]}),
            metadata={"sheet_name": "M23 Effectiveness", "chart_id": "M23"},
        )

    data: dict[str, pd.DataFrame] = {}
    summary_parts: list[str] = []

    # M23.1 -- DiD
    pre, post = _split_pre_post(monthly, earliest_date, _PRE_MONTHS, _POST_MONTHS)
    did = _compute_did(pre, post)
    did_table = _build_did_table(did)
    data["main"] = did_table
    data["did_raw"] = pd.DataFrame([did])

    if did["did_estimate"] > 0:
        summary_parts.append(
            f"Mailer drove ${did['did_estimate']:+,.2f}/mo incremental spend per responder "
            f"({did['did_pct']:+.1f}% lift)"
        )
    else:
        summary_parts.append(
            f"DiD estimate: ${did['did_estimate']:+,.2f}/mo per responder"
        )

    # M23.2 -- DiD by Segment
    did_seg = _compute_did_by_segment(
        monthly, earliest_date, odd_df, acct_col, _PRE_MONTHS, _POST_MONTHS
    )
    if not did_seg.empty:
        data["did_by_segment"] = did_seg
        top_tier = did_seg.loc[did_seg["DiD Estimate"].idxmax()]
        summary_parts.append(
            f"Strongest lift in {top_tier['Balance Tier']} tier "
            f"(${top_tier['DiD Estimate']:+,.2f}/mo)"
        )

    # M23.3 -- ITS
    its = _compute_its(monthly, earliest_date)
    if not its.empty:
        data["its"] = its

    # M23.4 -- Decay
    decay = _compute_decay(monthly, earliest_date, _POST_MONTHS)
    if not decay.empty:
        data["decay"] = decay
        half_life = decay.attrs.get("half_life_months")
        if half_life and half_life != float("inf"):
            summary_parts.append(f"Effect half-life: {half_life:.1f} months")
        first_lift = decay.iloc[0]["Lift"] if not decay.empty else 0
        last_lift = decay.iloc[-1]["Lift"] if not decay.empty else 0
        if first_lift > 0 and last_lift > 0:
            retention = last_lift / first_lift * 100
            summary_parts.append(f"{retention:.0f}% of initial lift retained by month {len(decay)}")

    # M23.5 -- Cumulative Incremental
    cum = _compute_cumulative_incremental(monthly, earliest_date, _POST_MONTHS)
    if not cum.empty:
        data["cumulative"] = cum
        total_incremental = cum.iloc[-1]["Cumulative Incremental"]
        summary_parts.append(f"Total incremental spend: ${total_incremental:,.0f}")

    # M23.6 -- Lift Distribution
    lift_dist = _compute_lift_distribution(
        monthly, earliest_date, _PRE_MONTHS, _POST_MONTHS, _MIN_TXN_COUNT
    )
    if not lift_dist.empty:
        data["lift_distribution"] = lift_dist
        resp_lift = lift_dist[lift_dist["group"] == "Responder"]
        if not resp_lift.empty:
            positive_pct = (resp_lift["lift"] > 0).sum() / len(resp_lift) * 100
            summary_parts.append(
                f"{positive_pct:.0f}% of responders increased spending post-mailer"
            )

    meta = {
        "sheet_name": "M23 Effectiveness",
        "chart_id": "M23",
        "category": "Mailer Intelligence",
        "n_responders": len(responders),
        "n_non_responders": len(non_responders),
        "did_estimate": did["did_estimate"],
        "did_pct": did["did_pct"],
        "half_life": decay.attrs.get("half_life_months") if not decay.empty else None,
    }

    # Executive headline (conclusion, not label)
    headline = "Mailer Effectiveness Analysis"
    if did["did_estimate"] > 0:
        headline = (
            f"Mailer drove ${did['did_estimate']:,.0f}/mo incremental spend "
            f"-- {len(responders):,} responders vs {len(non_responders):,} control"
        )

    return AnalysisResult(
        name="mailer_effectiveness",
        title=headline,
        data=data,
        metadata=meta,
        summary=". ".join(summary_parts),
    )
