"""M17: Spending behavior by demographics and mailer response timing.

Cross-references transaction data with ODD (account demographics) to answer:
  - Do ARS responders swipe early and often during response months?
  - How does spending differ across account holder age groups?
  - How does spending differ across branches?
  - Are larger transactions concentrated early or late in the month?

Requires ODD data in context["odd_df"] for demographic breakdowns.
Response-month analysis requires MmmYY Mail/Resp columns in ODD.
"""

from __future__ import annotations

import re

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

# Age group buckets based on account holder age
_AGE_BUCKETS = [
    ("18-25", 18, 25),
    ("26-35", 26, 35),
    ("36-45", 36, 45),
    ("46-55", 46, 55),
    ("56-65", 56, 65),
    ("65+", 65, 999),
]

_RESPONSE_SEGMENTS = {"NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"}


def _detect_acct_col(odd_df: pd.DataFrame) -> str | None:
    """Find the account number column in ODD."""
    for col in ("Account Number", "Acct Number", "Account_Number"):
        if col in odd_df.columns:
            return col
    return None


def _detect_resp_pairs(odd_df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Find (month, resp_col, mail_col) pairs in ODD columns."""
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


def _build_response_month_velocity(
    txn_df: pd.DataFrame,
    odd_df: pd.DataFrame,
    acct_col: str,
    pairs: list[tuple[str, str, str]],
) -> pd.DataFrame:
    """Compare responder vs non-responder swipe timing within response months.

    For each response month, splits accounts into responders vs non-responders,
    then looks at their transaction timing (day-of-month) in that calendar month.
    """
    dt = pd.to_datetime(txn_df["transaction_date"], errors="coerce")
    txn_work = txn_df[dt.notna()].copy()
    txn_work["txn_date"] = dt[dt.notna()]
    txn_work["txn_ym"] = txn_work["txn_date"].dt.to_period("M").astype(str)
    txn_work["day_of_month"] = txn_work["txn_date"].dt.day

    rows: list[dict] = []

    for month_str, resp_col, mail_col in pairs:
        # Parse month to YYYY-MM format for matching
        try:
            month_dt = pd.to_datetime(month_str, format="%b%y")
            ym = month_dt.strftime("%Y-%m")
        except Exception:
            continue

        # Identify responders and non-responders for this month
        mailed = odd_df[odd_df[mail_col].notna() & (odd_df[mail_col] != "")]
        if mailed.empty:
            continue

        resp_accts = set(
            mailed[mailed[resp_col].isin(_RESPONSE_SEGMENTS)][acct_col].astype(str)
        )
        non_resp_accts = set(mailed[~mailed[resp_col].isin(_RESPONSE_SEGMENTS)][acct_col].astype(str))

        # Get transactions in that calendar month
        month_txns = txn_work[txn_work["txn_ym"] == ym]
        if month_txns.empty:
            continue

        for label, acct_set in [("Responders", resp_accts), ("Non-Responders", non_resp_accts)]:
            segment_txns = month_txns[
                month_txns["primary_account_num"].astype(str).isin(acct_set)
            ]
            if segment_txns.empty:
                continue

            n_txns = len(segment_txns)
            n_accts = segment_txns["primary_account_num"].nunique()
            avg_dom = segment_txns["day_of_month"].mean()
            median_dom = segment_txns["day_of_month"].median()
            early_pct = (segment_txns["day_of_month"] <= 10).sum() / n_txns * 100
            avg_ticket = segment_txns["amount"].mean()
            total_spend = segment_txns["amount"].sum()

            rows.append({
                "month": month_str,
                "segment": label,
                "accounts": n_accts,
                "transactions": n_txns,
                "txns_per_account": round(n_txns / n_accts, 1) if n_accts else 0,
                "avg_day_of_month": round(avg_dom, 1),
                "median_day_of_month": round(median_dom, 1),
                "pct_first_10_days": round(early_pct, 1),
                "avg_ticket": round(avg_ticket, 2),
                "total_spend": round(total_spend, 2),
            })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result.columns = [
        "Month",
        "Segment",
        "Accounts",
        "Transactions",
        "Txns/Account",
        "Avg Day of Month",
        "Median Day",
        "% in First 10 Days",
        "Avg Ticket",
        "Total Spend",
    ]
    return result


def _build_age_group_spending(
    txn_df: pd.DataFrame,
    odd_df: pd.DataFrame,
    acct_col: str,
) -> pd.DataFrame:
    """Break down spending habits by account holder age group."""
    age_col = None
    for candidate in ("Account Holder Age", "Age", "Account_Holder_Age"):
        if candidate in odd_df.columns:
            age_col = candidate
            break

    if age_col is None:
        return pd.DataFrame()

    # Merge ODD age into transactions
    acct_age = odd_df[[acct_col, age_col]].copy()
    acct_age[age_col] = pd.to_numeric(acct_age[age_col], errors="coerce")
    acct_age = acct_age.dropna(subset=[age_col])
    acct_age[acct_col] = acct_age[acct_col].astype(str)

    merged = txn_df.merge(
        acct_age,
        left_on="primary_account_num",
        right_on=acct_col,
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame()

    # Assign age buckets
    def _age_bucket(age: float) -> str:
        for label, lo, hi in _AGE_BUCKETS:
            if lo <= age <= hi:
                return label
        return "Unknown"

    merged["age_group"] = merged[age_col].apply(_age_bucket)

    result = (
        merged.groupby("age_group")
        .agg(
            accounts=("primary_account_num", "nunique"),
            transactions=("amount", "count"),
            total_spend=("amount", "sum"),
            avg_ticket=("amount", "mean"),
        )
        .reset_index()
    )
    # Reorder by age bucket
    bucket_order = [b[0] for b in _AGE_BUCKETS]
    result["age_group"] = pd.Categorical(result["age_group"], categories=bucket_order, ordered=True)
    result = result.sort_values("age_group").reset_index(drop=True)
    result["age_group"] = result["age_group"].astype(str)

    result["pct_of_spend"] = (result["total_spend"] / result["total_spend"].sum() * 100).round(1)
    result["total_spend"] = result["total_spend"].round(2)
    result["avg_ticket"] = result["avg_ticket"].round(2)

    result.columns = [
        "Age Group",
        "Accounts",
        "Transactions",
        "Total Spend",
        "Avg Ticket",
        "% of Spend",
    ]
    return result


def _build_branch_spending(
    txn_df: pd.DataFrame,
    odd_df: pd.DataFrame,
    acct_col: str,
) -> pd.DataFrame:
    """Break down spending habits by branch."""
    if "Branch" not in odd_df.columns:
        return pd.DataFrame()

    acct_branch = odd_df[[acct_col, "Branch"]].dropna(subset=["Branch"]).copy()
    acct_branch[acct_col] = acct_branch[acct_col].astype(str)
    acct_branch["Branch"] = acct_branch["Branch"].astype(str)

    merged = txn_df.merge(
        acct_branch,
        left_on="primary_account_num",
        right_on=acct_col,
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame()

    result = (
        merged.groupby("Branch")
        .agg(
            accounts=("primary_account_num", "nunique"),
            transactions=("amount", "count"),
            total_spend=("amount", "sum"),
            avg_ticket=("amount", "mean"),
        )
        .reset_index()
        .sort_values("total_spend", ascending=False)
    )

    result["pct_of_spend"] = (result["total_spend"] / result["total_spend"].sum() * 100).round(1)
    result["total_spend"] = result["total_spend"].round(2)
    result["avg_ticket"] = result["avg_ticket"].round(2)

    result.columns = [
        "Branch",
        "Accounts",
        "Transactions",
        "Total Spend",
        "Avg Ticket",
        "% of Spend",
    ]
    return result


def analyze_spending_behavior(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Analyze spending behavior by demographics and mailer response timing.

    Requires ODD data in context["odd_df"].
    Returns up to 3 data sheets:
      - response_velocity: Responder vs non-responder swipe timing
      - age_groups: Spending by account holder age group
      - branches: Spending by branch
    """
    ctx = context or {}
    odd_df = ctx.get("odd_df")

    if odd_df is None or (isinstance(odd_df, pd.DataFrame) and odd_df.empty):
        return AnalysisResult.from_df(
            "spending_behavior",
            "Spending Behavior Analysis",
            pd.DataFrame({"Note": ["ODD data required for demographic analysis"]}),
            metadata={"sheet_name": "M17 Behavior"},
        )

    acct_col = _detect_acct_col(odd_df)
    if acct_col is None:
        return AnalysisResult.from_df(
            "spending_behavior",
            "Spending Behavior Analysis",
            pd.DataFrame({"Note": ["No account number column found in ODD"]}),
            metadata={"sheet_name": "M17 Behavior"},
        )

    data: dict[str, pd.DataFrame] = {}
    summary_parts: list[str] = []

    # Response-month velocity
    pairs = _detect_resp_pairs(odd_df)
    if pairs:
        velocity = _build_response_month_velocity(df, odd_df, acct_col, pairs)
        if not velocity.empty:
            data["response_velocity"] = velocity

            # Compute overall responder vs non-responder comparison
            resp_rows = velocity[velocity["Segment"] == "Responders"]
            non_resp_rows = velocity[velocity["Segment"] == "Non-Responders"]
            if not resp_rows.empty and not non_resp_rows.empty:
                resp_early = resp_rows["% in First 10 Days"].mean()
                non_resp_early = non_resp_rows["% in First 10 Days"].mean()
                resp_tpa = resp_rows["Txns/Account"].mean()
                summary_parts.append(
                    f"Responders: {resp_early:.0f}% of swipes in first 10 days "
                    f"(vs {non_resp_early:.0f}% non-responders), "
                    f"{resp_tpa:.1f} txns/account"
                )

    # Age group spending
    age_df = _build_age_group_spending(df, odd_df, acct_col)
    if not age_df.empty:
        data["age_groups"] = age_df
        top_age = age_df.iloc[age_df["% of Spend"].values.argmax()]
        summary_parts.append(
            f"Top spending age group: {top_age['Age Group']} "
            f"({top_age['% of Spend']}% of spend)"
        )

    # Branch spending
    branch_df = _build_branch_spending(df, odd_df, acct_col)
    if not branch_df.empty:
        data["branches"] = branch_df
        summary_parts.append(f"{len(branch_df)} branches with transaction activity")

    if not data:
        return AnalysisResult.from_df(
            "spending_behavior",
            "Spending Behavior Analysis",
            pd.DataFrame({"Note": ["No demographic data available for analysis"]}),
            metadata={"sheet_name": "M17 Behavior"},
        )

    # Use the first available sheet as "main" for Excel export
    first_key = next(iter(data))
    main_df = data[first_key]

    meta = {
        "sheet_name": "M17 Behavior",
        "sheets": list(data.keys()),
        "response_months": len(pairs),
        "age_groups": len(age_df) if not age_df.empty else 0,
        "branches": len(branch_df) if not branch_df.empty else 0,
    }

    return AnalysisResult(
        name="spending_behavior",
        title="Spending Behavior Analysis",
        data={"main": main_df, **{k: v for k, v in data.items() if k != first_key}},
        metadata=meta,
        summary=". ".join(summary_parts) if summary_parts else "Demographic spending analysis",
    )
