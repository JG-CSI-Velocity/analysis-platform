# v4_s2_merchant_intel.py
# Storyline 2: Merchant Intelligence
# =============================================================================
# Top merchants, MCC analysis, business/personal splits, rank movement, growth

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from txn_analysis.v4_themes import (
    COLORS,
    apply_theme,
    format_currency,
    stacked_bar,
)


def run(ctx: dict) -> dict:
    """
    Run Merchant Intelligence analyses.
    """
    df = ctx["combined_df"]
    biz = ctx["business_df"]
    per = ctx["personal_df"]
    config = ctx["config"]
    top_n = config.get("top_n", 50)

    sections = []
    sheets = []
    merch_col = (
        "merchant_consolidated" if "merchant_consolidated" in df.columns else "merchant_name"
    )

    # --- Top Merchants by Spend ---
    spend_df = _top_merchants(df, merch_col, "amount_sum", top_n)
    spend_fig = _merchant_bar(
        spend_df, "Total Spend", f"Top {min(25, top_n)} Merchants by Total Spend"
    )
    sections.append(
        {
            "heading": "Top Merchants by Total Spend",
            "narrative": _top_narrative(spend_df, "spend", df),
            "figures": [spend_fig],
            "tables": [("Top Merchants - Spend", spend_df.head(top_n))],
        }
    )
    sheets.append(
        {
            "name": "S2 Top Spend",
            "df": spend_df,
            "currency_cols": ["Total Spend", "Avg Transaction"],
            "number_cols": ["Transactions", "Unique Accounts"],
        }
    )

    # --- Top Merchants by Transaction Count ---
    txn_df = _top_merchants(df, merch_col, "txn_count", top_n)
    txn_fig = _merchant_bar(
        txn_df,
        "Transactions",
        f"Top {min(25, top_n)} Merchants by Transaction Count",
        color=COLORS["secondary"],
    )
    sections.append(
        {
            "heading": "Top Merchants by Transaction Count",
            "narrative": "",
            "figures": [txn_fig],
            "tables": [("Top Merchants - Transactions", txn_df.head(top_n))],
        }
    )
    sheets.append(
        {
            "name": "S2 Top Txn Count",
            "df": txn_df,
            "currency_cols": ["Total Spend", "Avg Transaction"],
            "number_cols": ["Transactions", "Unique Accounts"],
        }
    )

    # --- Top Merchants by Unique Accounts ---
    acct_df = _top_merchants(df, merch_col, "unique_accounts", top_n)
    acct_fig = _merchant_bar(
        acct_df,
        "Unique Accounts",
        f"Top {min(25, top_n)} Merchants by Account Penetration",
        color=COLORS["accent"],
    )
    sections.append(
        {
            "heading": "Top Merchants by Unique Accounts",
            "narrative": "",
            "figures": [acct_fig],
            "tables": [],
        }
    )
    sheets.append(
        {
            "name": "S2 Top Accounts",
            "df": acct_df,
            "currency_cols": ["Total Spend", "Avg Transaction"],
            "number_cols": ["Transactions", "Unique Accounts"],
        }
    )

    # --- MCC Category Analysis (3-panel: spend, txn count, unique accounts) ---
    if "mcc_code" in df.columns:
        mcc_df = _mcc_analysis(df, top_n)
        mcc_spend_fig = _merchant_bar(
            mcc_df,
            "Total Spend",
            "Top 20 MCC Categories by Spend",
            y_col="MCC Code",
            color=COLORS["primary"],
        )
        mcc_txn_df = mcc_df.sort_values("Transactions", ascending=False).head(20)
        mcc_txn_fig = _merchant_bar(
            mcc_txn_df,
            "Transactions",
            "Top 20 MCC Categories by Transaction Count",
            y_col="MCC Code",
            color=COLORS["secondary"],
        )
        mcc_acct_df = mcc_df.sort_values("Unique Accounts", ascending=False).head(20)
        mcc_acct_fig = _merchant_bar(
            mcc_acct_df,
            "Unique Accounts",
            "Top 20 MCC Categories by Account Penetration",
            y_col="MCC Code",
            color=COLORS["accent"],
        )
        sections.append(
            {
                "heading": "Merchant Category (MCC) Analysis",
                "narrative": f"Top {top_n} MCC codes analyzed across spend, transaction volume, and account penetration.",
                "figures": [mcc_spend_fig, mcc_txn_fig, mcc_acct_fig],
                "tables": [("MCC Categories", mcc_df.head(20))],
            }
        )
        sheets.append(
            {
                "name": "S2 MCC Analysis",
                "df": mcc_df,
                "currency_cols": ["Total Spend", "Avg Transaction"],
                "number_cols": ["Transactions", "Unique Accounts", "Merchants"],
            }
        )

    # --- Business Top Merchants (spend, txn count, unique accounts) ---
    if len(biz) > 0:
        biz_df = _top_merchants(biz, merch_col, "amount_sum", top_n)
        biz_fig = _merchant_bar(
            biz_df, "Total Spend", "Top 25 Business Merchants by Spend", color="#7B2D8E"
        )
        biz_txn_df = _top_merchants(biz, merch_col, "txn_count", top_n)
        biz_txn_fig = _merchant_bar(
            biz_txn_df, "Transactions", "Top 25 Business Merchants by Txn Count", color="#7B2D8E"
        )
        biz_acct_df = _top_merchants(biz, merch_col, "unique_accounts", top_n)
        biz_acct_fig = _merchant_bar(
            biz_acct_df, "Unique Accounts", "Top 25 Business Merchants by Accounts", color="#7B2D8E"
        )
        sections.append(
            {
                "heading": "Business Account - Top Merchants",
                "narrative": f"<b>{len(biz):,}</b> business transactions across <b>{biz['primary_account_num'].nunique():,}</b> accounts.",
                "figures": [biz_fig, biz_txn_fig, biz_acct_fig],
                "tables": [],
            }
        )
        sheets.append(
            {
                "name": "S2 Business Merchants",
                "df": biz_df,
                "currency_cols": ["Total Spend", "Avg Transaction"],
                "number_cols": ["Transactions", "Unique Accounts"],
            }
        )

    # --- Personal Top Merchants (spend, txn count, unique accounts) ---
    if len(per) > 0:
        per_df = _top_merchants(per, merch_col, "amount_sum", top_n)
        per_fig = _merchant_bar(
            per_df, "Total Spend", "Top 25 Personal Merchants by Spend", color=COLORS["secondary"]
        )
        per_txn_df = _top_merchants(per, merch_col, "txn_count", top_n)
        per_txn_fig = _merchant_bar(
            per_txn_df,
            "Transactions",
            "Top 25 Personal Merchants by Txn Count",
            color=COLORS["secondary"],
        )
        per_acct_df = _top_merchants(per, merch_col, "unique_accounts", top_n)
        per_acct_fig = _merchant_bar(
            per_acct_df,
            "Unique Accounts",
            "Top 25 Personal Merchants by Accounts",
            color=COLORS["secondary"],
        )
        sections.append(
            {
                "heading": "Personal Account - Top Merchants",
                "narrative": f"<b>{len(per):,}</b> personal transactions across <b>{per['primary_account_num'].nunique():,}</b> accounts.",
                "figures": [per_fig, per_txn_fig, per_acct_fig],
                "tables": [],
            }
        )
        sheets.append(
            {
                "name": "S2 Personal Merchants",
                "df": per_df,
                "currency_cols": ["Total Spend", "Avg Transaction"],
                "number_cols": ["Transactions", "Unique Accounts"],
            }
        )

    # --- Monthly Rank Movement ---
    if "year_month" in df.columns:
        rank_df, rank_fig = _monthly_rank_tracking(df, merch_col)
        if rank_df is not None:
            sections.append(
                {
                    "heading": "Monthly Merchant Rank Movement",
                    "narrative": "Tracks how top merchants move up and down in spend rankings month-over-month. Stable leaders vs. volatile risers/fallers.",
                    "figures": [rank_fig],
                    "tables": [],
                }
            )
            sheets.append(
                {
                    "name": "S2 Rank Tracking",
                    "df": rank_df,
                    "number_cols": list(rank_df.columns[1:]),
                }
            )

    # --- Growth Leaders & Decliners ---
    if "year_month" in df.columns:
        growth_df, growth_fig, decline_fig = _growth_analysis(df, merch_col, config)
        if growth_df is not None:
            sections.append(
                {
                    "heading": "Growth Leaders & Decliners",
                    "narrative": "Merchants with the largest absolute spend changes between the first and second half of the analysis period.",
                    "figures": [growth_fig, decline_fig],
                    "tables": [("Growth/Decline", growth_df.head(30))],
                }
            )
            sheets.append(
                {
                    "name": "S2 Growth Leaders",
                    "df": growth_df,
                    "currency_cols": ["First Half Spend", "Second Half Spend", "Change"],
                    "pct_cols": ["Change %"],
                }
            )

    # --- Spending Consistency / Volatility ---
    if "year_month" in df.columns:
        result = _spending_consistency(df, merch_col)
        if result is not None:
            consist_df, consist_fig, volatile_fig = result
            sections.append(
                {
                    "heading": "Spending Consistency & Volatility",
                    "narrative": (
                        "Measures how predictable each merchant's monthly spend is. "
                        "Consistency Score = 100 minus the coefficient of variation "
                        "(capped at 100). Merchants with $10K+ total spend and 3+ "
                        "active months are included."
                    ),
                    "figures": [consist_fig, volatile_fig],
                    "tables": [("Consistency Data", consist_df.head(30))],
                }
            )
            sheets.append(
                {
                    "name": "S2 Consistency",
                    "df": consist_df,
                    "currency_cols": ["Total Spend", "Avg Monthly"],
                    "number_cols": ["Std Dev", "CV (%)", "Consistency Score", "Months Active"],
                }
            )

    # --- Month-over-Month Growth ---
    if "year_month" in df.columns:
        result = _mom_growth(df, merch_col)
        if result is not None:
            mom_df, mom_growth_fig, mom_decline_fig = result
            sections.append(
                {
                    "heading": "Month-over-Month Growth Analysis",
                    "narrative": (
                        "Tracks the biggest month-over-month spending changes "
                        "across all consecutive month pairs. Only merchants with "
                        "$1K+ in either month are included."
                    ),
                    "figures": [mom_growth_fig, mom_decline_fig],
                    "tables": [("MoM Growth", mom_df.head(50))],
                }
            )
            sheets.append(
                {
                    "name": "S2 MoM Growth",
                    "df": mom_df,
                    "currency_cols": ["Prev Spend", "Curr Spend", "Change ($)"],
                    "pct_cols": ["Change (%)"],
                }
            )

    # --- New vs Declining Merchant Cohort ---
    if "year_month" in df.columns:
        result = _merchant_cohort(df, merch_col)
        if result is not None:
            cohort_df, cohort_fig = result
            sections.append(
                {
                    "heading": "New vs Declining Merchant Cohort",
                    "narrative": (
                        "Tracks merchant lifecycle each month: new merchants "
                        "(first appearance), returning merchants (seen before but "
                        "not in the prior month), and lost merchants (active last "
                        "month but absent this month)."
                    ),
                    "figures": [cohort_fig],
                    "tables": [("Cohort Data", cohort_df)],
                }
            )
            sheets.append(
                {
                    "name": "S2 Merchant Cohort",
                    "df": cohort_df,
                    "currency_cols": ["New Merchant $"],
                    "pct_cols": ["New %", "Return %", "New $ %"],
                    "number_cols": ["Total Merchants", "New", "Returning", "Lost"],
                }
            )

    # --- Cohort Top-5 New Merchants (most recent months) ---
    if "year_month" in df.columns:
        cohort_top5 = _cohort_top_new(df, merch_col)
        if cohort_top5 is not None:
            sections.append(
                {
                    "heading": "Top New Merchants by Month",
                    "narrative": (
                        "The top 5 newly appearing merchants each recent month, "
                        "ranked by their entry spend. Highlights emerging merchant "
                        "relationships gaining traction quickly."
                    ),
                    "figures": [],
                    "tables": [("Top New Merchants", cohort_top5)],
                }
            )
            sheets.append(
                {
                    "name": "S2 Top New Merchants",
                    "df": cohort_top5,
                    "currency_cols": ["Entry Spend"],
                    "number_cols": ["Accounts"],
                }
            )

    # --- Business Account Rank Movers ---
    if "year_month" in df.columns and len(biz) > 0:
        result = _account_rank_movers(biz, merch_col, label="Business")
        if result is not None:
            biz_mover_df, biz_climb_fig, biz_fall_fig = result
            sections.append(
                {
                    "heading": "Business Account Rank Movers",
                    "narrative": (
                        "Compares merchant spend rankings between consecutive "
                        "months for business accounts. Rank change = previous "
                        "rank minus current rank (positive = climbed)."
                    ),
                    "figures": [biz_climb_fig, biz_fall_fig],
                    "tables": [("Biz Rank Movers", biz_mover_df.head(30))],
                }
            )
            sheets.append(
                {
                    "name": "S2 Biz Rank Movers",
                    "df": biz_mover_df,
                    "currency_cols": ["Prev $", "Curr $", "Spend Change"],
                    "pct_cols": ["Spend Change %"],
                    "number_cols": ["Rank Change"],
                }
            )

    # --- Personal Account Rank Movers ---
    if "year_month" in df.columns and len(per) > 0:
        result = _personal_rank_movers(per, merch_col)
        if result is not None:
            per_mover_df, per_climb_fig, per_fall_fig, per_spend_fig = result
            sections.append(
                {
                    "heading": "Personal Account Rank Movers",
                    "narrative": (
                        "Compares merchant spend rankings between consecutive "
                        "months for personal accounts. Also highlights merchants "
                        "with the largest absolute spend increases."
                    ),
                    "figures": [per_climb_fig, per_fall_fig, per_spend_fig],
                    "tables": [("Per Rank Movers", per_mover_df.head(30))],
                }
            )
            sheets.append(
                {
                    "name": "S2 Per Rank Movers",
                    "df": per_mover_df,
                    "currency_cols": ["Prev $", "Curr $", "Spend Change"],
                    "pct_cols": ["Spend Change %"],
                    "number_cols": ["Rank Change"],
                }
            )

    return {
        "title": "S2: Merchant Intelligence",
        "description": "Top merchants, MCC categories, business/personal splits, rank movement, growth leaders",
        "sections": sections,
        "sheets": sheets,
    }


# =============================================================================
# Core Analysis Functions
# =============================================================================


def _top_merchants(df, merch_col, sort_by, top_n):
    agg = (
        df.groupby(merch_col)
        .agg(
            {
                "amount": ["sum", "count", "mean"],
                "primary_account_num": "nunique",
            }
        )
        .round(2)
    )
    agg.columns = ["Total Spend", "Transactions", "Avg Transaction", "Unique Accounts"]

    sort_map = {
        "amount_sum": "Total Spend",
        "txn_count": "Transactions",
        "unique_accounts": "Unique Accounts",
    }
    agg = agg.sort_values(sort_map.get(sort_by, "Total Spend"), ascending=False).head(top_n)
    agg = agg.reset_index().rename(columns={merch_col: "Merchant"})
    return agg


def _merchant_bar(df, value_col, title, y_col="Merchant", color=None, top_n=25):
    top = df.head(top_n).iloc[::-1]
    color = color or COLORS["primary"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=top[value_col],
            y=top[y_col].astype(str).str[:40],
            orientation="h",
            marker_color=color,
            text=top[value_col].apply(
                lambda v: (
                    format_currency(v)
                    if value_col in ("Total Spend", "Avg Transaction")
                    else f"{v:,.0f}"
                )
            ),
            textposition="outside",
            textfont=dict(size=10),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=value_col,
        yaxis=dict(automargin=True),
        height=max(500, top_n * 22),
        margin=dict(l=10),
    )
    if value_col in ("Total Spend", "Avg Transaction"):
        fig.update_xaxes(tickprefix="$", tickformat=",")
    else:
        fig.update_xaxes(tickformat=",")
    fig = apply_theme(fig)
    return fig


def _mcc_analysis(df, top_n):
    agg = (
        df.groupby("mcc_code")
        .agg(
            {
                "amount": ["sum", "count", "mean"],
                "primary_account_num": "nunique",
                "merchant_name": "nunique",
            }
        )
        .round(2)
    )
    agg.columns = ["Total Spend", "Transactions", "Avg Transaction", "Unique Accounts", "Merchants"]
    agg = agg.sort_values("Total Spend", ascending=False).head(top_n)
    agg = agg.reset_index().rename(columns={"mcc_code": "MCC Code"})
    return agg


def _top_narrative(spend_df, metric_type, df):
    if spend_df.empty:
        return ""
    top = spend_df.iloc[0]
    total = df["amount"].sum()
    top_pct = (top["Total Spend"] / total * 100) if total > 0 else 0
    top_50_pct = (spend_df["Total Spend"].sum() / total * 100) if total > 0 else 0
    return (
        f"The #1 merchant is <b>{top['Merchant']}</b> with "
        f"{format_currency(top['Total Spend'])} in spend ({top_pct:.1f}% of total). "
        f"The top {len(spend_df)} merchants account for <b>{top_50_pct:.1f}%</b> of all spend "
        f"({format_currency(spend_df['Total Spend'].sum())} of {format_currency(total)})."
    )


# =============================================================================
# Monthly Rank Tracking
# =============================================================================


def _monthly_rank_tracking(df, merch_col):
    sorted_months = sorted(df["year_month"].unique())
    if len(sorted_months) < 3:
        return None, None

    monthly_ranks = {}
    for month in sorted_months:
        month_data = df[df["year_month"] == month]
        rankings = month_data.groupby(merch_col)["amount"].sum().sort_values(ascending=False)
        for rank, merchant in enumerate(rankings.index, 1):
            if merchant not in monthly_ranks:
                monthly_ranks[merchant] = {}
            monthly_ranks[merchant][str(month)] = rank

    # Get merchants in top 10 across most months
    rows = []
    for merchant, ranks in monthly_ranks.items():
        avg_rank = np.mean(list(ranks.values()))
        months_top_10 = sum(1 for r in ranks.values() if r <= 10)
        if months_top_10 >= len(sorted_months) // 2:
            row = {"Merchant": merchant, "Avg Rank": round(avg_rank, 1)}
            for month in sorted_months:
                row[str(month)] = ranks.get(str(month), None)
            rows.append(row)

    if not rows:
        return None, None

    rank_df = pd.DataFrame(rows).sort_values("Avg Rank").head(15)

    # Chart: line chart of rank trajectory (inverted y-axis)
    fig = go.Figure()
    month_strs = [str(m) for m in sorted_months]
    for _, row in rank_df.iterrows():
        ranks = [row.get(m) for m in month_strs]
        fig.add_trace(
            go.Scatter(
                x=month_strs,
                y=ranks,
                mode="lines+markers",
                name=str(row["Merchant"])[:30],
                line=dict(width=2),
                marker=dict(size=6),
            )
        )

    fig.update_layout(
        title="Top Merchant Rank Movement (Lower = Better)",
        yaxis=dict(title="Rank", autorange="reversed", dtick=1),
        xaxis_title="Month",
        height=600,
        legend=dict(font=dict(size=10)),
        hovermode="x unified",
    )
    fig = apply_theme(fig)

    return rank_df, fig


# =============================================================================
# Growth Leaders & Decliners
# =============================================================================


def _growth_analysis(df, merch_col, config):
    sorted_months = sorted(df["year_month"].unique())
    if len(sorted_months) < 4:
        return None, None, None

    mid = len(sorted_months) // 2
    first_half = sorted_months[:mid]
    second_half = sorted_months[mid:]

    h1 = df[df["year_month"].isin(first_half)].groupby(merch_col)["amount"].sum()
    h2 = df[df["year_month"].isin(second_half)].groupby(merch_col)["amount"].sum()

    growth = pd.DataFrame({"First Half Spend": h1, "Second Half Spend": h2}).fillna(0)
    growth["Change"] = growth["Second Half Spend"] - growth["First Half Spend"]
    growth["Change %"] = np.where(
        growth["First Half Spend"] > 0,
        (growth["Change"] / growth["First Half Spend"] * 100).round(1),
        0,
    )

    min_threshold = config.get("growth_min_threshold", 1000)
    growth = growth[
        (growth["First Half Spend"] >= min_threshold)
        | (growth["Second Half Spend"] >= min_threshold)
    ]
    growth = growth.sort_values("Change", ascending=False)
    growth = growth.reset_index().rename(columns={merch_col: "Merchant"})

    # Growth chart (top 15)
    top_growth = growth.head(15).iloc[::-1]
    growth_fig = go.Figure()
    growth_fig.add_trace(
        go.Bar(
            x=top_growth["Change"],
            y=top_growth["Merchant"].astype(str).str[:35],
            orientation="h",
            marker_color=COLORS["positive"],
            text=top_growth["Change"].apply(lambda v: f"+{format_currency(v)}"),
            textposition="outside",
        )
    )
    growth_fig.update_layout(
        title="Top 15 Growth Leaders (Absolute Spend Increase)",
        xaxis_title="Spend Change ($)",
        xaxis_tickprefix="$",
        xaxis_tickformat=",",
        height=500,
    )
    growth_fig = apply_theme(growth_fig)

    # Decline chart (bottom 15)
    top_decline = growth.tail(15)
    decline_fig = go.Figure()
    decline_fig.add_trace(
        go.Bar(
            x=top_decline["Change"],
            y=top_decline["Merchant"].astype(str).str[:35],
            orientation="h",
            marker_color=COLORS["negative"],
            text=top_decline["Change"].apply(lambda v: format_currency(v)),
            textposition="outside",
        )
    )
    decline_fig.update_layout(
        title="Top 15 Decliners (Absolute Spend Decrease)",
        xaxis_title="Spend Change ($)",
        xaxis_tickprefix="$",
        xaxis_tickformat=",",
        height=500,
    )
    decline_fig = apply_theme(decline_fig)

    return growth, growth_fig, decline_fig


# =============================================================================
# Spending Consistency / Volatility (M5C)
# =============================================================================

MIN_ACTIVE_MONTHS = 3
MIN_TOTAL_SPEND = 10_000


def _spending_consistency(df, merch_col):
    """Classify merchants by spending volatility using coefficient of variation.

    CV = std / mean * 100. Consistency score = 100 - min(CV, 100).
    Filters: 3+ active months and $10K+ total spend.
    """
    monthly_spend = df.groupby([merch_col, "year_month"])["amount"].sum().reset_index()

    pivot = monthly_spend.pivot(index=merch_col, columns="year_month", values="amount").fillna(0)

    # Count months with non-zero spend
    active_months = (pivot > 0).sum(axis=1)
    pivot = pivot.loc[active_months >= MIN_ACTIVE_MONTHS]

    if pivot.empty:
        return None

    # Replace zeros with NaN so they do not deflate mean for inactive months
    numeric_pivot = pivot.replace(0, np.nan)

    stats = pd.DataFrame(
        {
            "Total Spend": pivot.sum(axis=1),
            "Avg Monthly": numeric_pivot.mean(axis=1),
            "Std Dev": numeric_pivot.std(axis=1),
            "Months Active": active_months.reindex(pivot.index),
        }
    )

    stats = stats[stats["Total Spend"] >= MIN_TOTAL_SPEND].copy()
    if stats.empty:
        return None

    stats["CV (%)"] = np.where(
        stats["Avg Monthly"] > 0,
        (stats["Std Dev"] / stats["Avg Monthly"] * 100).round(1),
        0,
    )
    stats["Consistency Score"] = (100 - stats["CV (%)"].clip(upper=100)).round(1)
    stats["Classification"] = pd.cut(
        stats["CV (%)"],
        bins=[-np.inf, 50, 100, np.inf],
        labels=["Consistent", "Moderate", "Volatile"],
    )

    stats = stats.round(2).reset_index().rename(columns={merch_col: "Merchant"})

    # --- Chart 1: Top 30 Most Consistent (lowest CV) ---
    consistent = stats.sort_values("CV (%)").head(30).iloc[::-1]
    consist_fig = go.Figure()
    consist_fig.add_trace(
        go.Bar(
            x=consistent["Consistency Score"],
            y=consistent["Merchant"].astype(str).str[:35],
            orientation="h",
            marker_color=COLORS["positive"],
            text=consistent["Consistency Score"].apply(lambda v: f"{v:.0f}"),
            textposition="outside",
            textfont=dict(size=10),
        )
    )
    consist_fig.update_layout(
        title="Top 30 Most Consistent Merchants (by Consistency Score)",
        xaxis_title="Consistency Score",
        yaxis=dict(automargin=True),
        height=max(500, 30 * 22),
        margin=dict(l=10),
    )
    consist_fig = apply_theme(consist_fig)

    # --- Chart 2: Top 30 Most Volatile (highest CV) ---
    volatile = stats.sort_values("CV (%)", ascending=False).head(30).iloc[::-1]
    volatile_fig = go.Figure()
    volatile_fig.add_trace(
        go.Bar(
            x=volatile["CV (%)"],
            y=volatile["Merchant"].astype(str).str[:35],
            orientation="h",
            marker_color=COLORS["negative"],
            text=volatile["CV (%)"].apply(lambda v: f"{v:.0f}%"),
            textposition="outside",
            textfont=dict(size=10),
        )
    )
    volatile_fig.update_layout(
        title="Top 30 Most Volatile Merchants (by CV %)",
        xaxis_title="Coefficient of Variation (%)",
        yaxis=dict(automargin=True),
        height=max(500, 30 * 22),
        margin=dict(l=10),
    )
    volatile_fig = apply_theme(volatile_fig)

    # Sort output by total spend descending for the sheet
    stats = stats.sort_values("Total Spend", ascending=False)

    return stats, consist_fig, volatile_fig


# =============================================================================
# Month-over-Month Growth (M5B)
# =============================================================================

MOM_MIN_SPEND = 1_000


def _mom_growth(df, merch_col):
    """Calculate month-over-month spend changes for each merchant.

    Compares every consecutive month pair. Only includes merchants
    with $1K+ spend in either the previous or current month.
    Returns top 50 growth leaders and top 50 decliners across all pairs.
    """
    sorted_months = sorted(df["year_month"].unique())
    if len(sorted_months) < 2:
        return None

    monthly = df.groupby([merch_col, "year_month"])["amount"].sum().reset_index()

    rows = []
    for i in range(len(sorted_months) - 1):
        prev_month = sorted_months[i]
        curr_month = sorted_months[i + 1]

        prev_data = monthly[monthly["year_month"] == prev_month].set_index(merch_col)["amount"]
        curr_data = monthly[monthly["year_month"] == curr_month].set_index(merch_col)["amount"]

        all_merchants = set(prev_data.index) | set(curr_data.index)
        for merchant in all_merchants:
            prev_val = prev_data.get(merchant, 0)
            curr_val = curr_data.get(merchant, 0)

            if prev_val < MOM_MIN_SPEND and curr_val < MOM_MIN_SPEND:
                continue

            change_abs = curr_val - prev_val
            change_pct = (change_abs / prev_val * 100) if prev_val > 0 else 0

            rows.append(
                {
                    "Merchant": merchant,
                    "Period": f"{prev_month} -> {curr_month}",
                    "Prev Spend": round(prev_val, 2),
                    "Curr Spend": round(curr_val, 2),
                    "Change ($)": round(change_abs, 2),
                    "Change (%)": round(change_pct, 1),
                }
            )

    if not rows:
        return None

    mom_df = pd.DataFrame(rows)

    # Top 50 growth leaders (largest positive change)
    leaders = mom_df.sort_values("Change ($)", ascending=False).head(50)
    # Top 50 decliners (largest negative change)
    decliners = mom_df.sort_values("Change ($)").head(50)

    # --- Growth leaders chart ---
    chart_leaders = leaders.head(50).iloc[::-1]
    chart_leaders_label = chart_leaders.apply(
        lambda r: f"{r['Merchant'][:25]} ({r['Period']})", axis=1
    )
    growth_fig = go.Figure()
    growth_fig.add_trace(
        go.Bar(
            x=chart_leaders["Change ($)"],
            y=chart_leaders_label,
            orientation="h",
            marker_color=COLORS["positive"],
            text=chart_leaders["Change ($)"].apply(lambda v: f"+{format_currency(v)}"),
            textposition="outside",
            textfont=dict(size=9),
        )
    )
    growth_fig.update_layout(
        title="Top 50 MoM Growth Leaders",
        xaxis_title="Spend Change ($)",
        xaxis_tickprefix="$",
        xaxis_tickformat=",",
        yaxis=dict(automargin=True, tickfont=dict(size=9)),
        height=max(600, 50 * 20),
        margin=dict(l=10),
    )
    growth_fig = apply_theme(growth_fig)

    # --- Decliners chart ---
    chart_decliners = decliners.head(50)
    chart_decliners_label = chart_decliners.apply(
        lambda r: f"{r['Merchant'][:25]} ({r['Period']})", axis=1
    )
    decline_fig = go.Figure()
    decline_fig.add_trace(
        go.Bar(
            x=chart_decliners["Change ($)"],
            y=chart_decliners_label,
            orientation="h",
            marker_color=COLORS["negative"],
            text=chart_decliners["Change ($)"].apply(format_currency),
            textposition="outside",
            textfont=dict(size=9),
        )
    )
    decline_fig.update_layout(
        title="Top 50 MoM Decliners",
        xaxis_title="Spend Change ($)",
        xaxis_tickprefix="$",
        xaxis_tickformat=",",
        yaxis=dict(automargin=True, tickfont=dict(size=9)),
        height=max(600, 50 * 20),
        margin=dict(l=10),
    )
    decline_fig = apply_theme(decline_fig)

    # Full dataset sorted by absolute change for the sheet
    mom_df = mom_df.sort_values("Change ($)", ascending=False)

    return mom_df, growth_fig, decline_fig


# =============================================================================
# New vs Declining Merchant Cohort (M5D)
# =============================================================================


def _merchant_cohort(df, merch_col):
    """Track new, returning, and lost merchants each month.

    - New: merchant's first appearance ever
    - Returning: seen before historically but not in the prior month
    - Lost: active in prior month but absent this month
    """
    sorted_months = sorted(df["year_month"].unique())
    if len(sorted_months) < 2:
        return None

    # Build per-month merchant sets
    month_merchants = {}
    for month in sorted_months:
        merchants = set(df.loc[df["year_month"] == month, merch_col].unique())
        month_merchants[month] = merchants

    # Build per-month spend
    month_spend = df.groupby(["year_month", merch_col])["amount"].sum().reset_index()

    # First-month lookup for each merchant
    first_seen = df.groupby(merch_col)["year_month"].min().to_dict()

    all_seen_so_far = set()
    prev_merchants = set()
    cohort_rows = []

    for month in sorted_months:
        current = month_merchants[month]
        new_merchants = {m for m in current if first_seen.get(m) == month}
        returning = current - new_merchants - prev_merchants
        # Returning only if they were seen historically before this month
        returning = {m for m in returning if m in all_seen_so_far}
        lost = prev_merchants - current

        total_count = len(current)
        new_count = len(new_merchants)
        returning_count = len(returning)
        lost_count = len(lost)

        # Spend from new merchants this month
        month_spend_data = month_spend[month_spend["year_month"] == month]
        total_month_spend = month_spend_data["amount"].sum()
        new_spend = month_spend_data.loc[
            month_spend_data[merch_col].isin(new_merchants), "amount"
        ].sum()

        new_pct = (new_count / total_count * 100) if total_count > 0 else 0
        return_pct = (returning_count / total_count * 100) if total_count > 0 else 0
        new_spend_pct = (new_spend / total_month_spend * 100) if total_month_spend > 0 else 0

        cohort_rows.append(
            {
                "Month": str(month),
                "Total Merchants": total_count,
                "New": new_count,
                "New %": round(new_pct, 1),
                "Returning": returning_count,
                "Return %": round(return_pct, 1),
                "Lost": lost_count,
                "New Merchant $": round(new_spend, 2),
                "New $ %": round(new_spend_pct, 1),
            }
        )

        all_seen_so_far.update(current)
        prev_merchants = current

    cohort_df = pd.DataFrame(cohort_rows)

    # Stacked bar chart: New / Returning / Lost per month
    cohort_fig = stacked_bar(
        cohort_df,
        x_col="Month",
        y_cols=["New", "Returning", "Lost"],
        title="Merchant Cohort Flow by Month (New / Returning / Lost)",
        colors=[COLORS["positive"], COLORS["accent"], COLORS["negative"]],
    )

    return cohort_df, cohort_fig


def _cohort_top_new(df, merch_col, top_n=5, recent_months=3):
    """Top *top_n* new merchants per recent month by entry spend."""
    sorted_months = sorted(df["year_month"].unique())
    if len(sorted_months) < 2:
        return None

    first_seen = df.groupby(merch_col)["year_month"].min().to_dict()
    target_months = sorted_months[-recent_months:]

    rows = []
    for month in target_months:
        new_merchants = {m for m, fs in first_seen.items() if fs == month}
        if not new_merchants:
            continue
        m_data = df[(df["year_month"] == month) & (df[merch_col].isin(new_merchants))]
        agg = (
            m_data.groupby(merch_col)
            .agg(
                spend=("amount", "sum"),
                accounts=("primary_account_num", "nunique"),
            )
            .sort_values("spend", ascending=False)
            .head(top_n)
            .reset_index()
        )
        for _, r in agg.iterrows():
            rows.append(
                {
                    "Month": str(month),
                    "Merchant": r[merch_col],
                    "Entry Spend": round(r["spend"], 2),
                    "Accounts": int(r["accounts"]),
                }
            )

    if not rows:
        return None
    return pd.DataFrame(rows)


# =============================================================================
# Business Account Rank Movers (M5E)
# =============================================================================

TOP_RANK_THRESHOLD = 100


def _account_rank_movers(subset_df, merch_col, label="Business"):
    """Compare merchant spend ranks between consecutive months.

    Only merchants ranked in the top 100 in either month are considered.
    Returns a DataFrame and two horizontal bar charts (climbers / fallers).
    """
    if "year_month" not in subset_df.columns:
        return None

    sorted_months = sorted(subset_df["year_month"].unique())
    if len(sorted_months) < 2:
        return None

    monthly_spend = subset_df.groupby([merch_col, "year_month"])["amount"].sum().reset_index()

    all_movers = []

    for i in range(len(sorted_months) - 1):
        prev_month = sorted_months[i]
        curr_month = sorted_months[i + 1]

        prev = (
            monthly_spend[monthly_spend["year_month"] == prev_month]
            .sort_values("amount", ascending=False)
            .reset_index(drop=True)
        )
        prev["rank"] = range(1, len(prev) + 1)

        curr = (
            monthly_spend[monthly_spend["year_month"] == curr_month]
            .sort_values("amount", ascending=False)
            .reset_index(drop=True)
        )
        curr["rank"] = range(1, len(curr) + 1)

        merged = pd.merge(
            prev[[merch_col, "rank", "amount"]].rename(
                columns={"rank": "prev_rank", "amount": "prev_spend"}
            ),
            curr[[merch_col, "rank", "amount"]].rename(
                columns={"rank": "curr_rank", "amount": "curr_spend"}
            ),
            on=merch_col,
            how="outer",
        )

        # Only merchants in top N in either month
        merged = merged[
            (merged["prev_rank"] <= TOP_RANK_THRESHOLD)
            | (merged["curr_rank"] <= TOP_RANK_THRESHOLD)
        ].copy()

        # Fill missing ranks with a value just outside threshold
        fill_rank = TOP_RANK_THRESHOLD + 1
        merged["prev_rank"] = merged["prev_rank"].fillna(fill_rank)
        merged["curr_rank"] = merged["curr_rank"].fillna(fill_rank)
        merged["prev_spend"] = merged["prev_spend"].fillna(0).round(2)
        merged["curr_spend"] = merged["curr_spend"].fillna(0).round(2)

        merged["Rank Change"] = (merged["prev_rank"] - merged["curr_rank"]).astype(int)
        merged["Spend Change"] = (merged["curr_spend"] - merged["prev_spend"]).round(2)
        merged["Spend Change %"] = np.where(
            merged["prev_spend"] > 0,
            ((merged["curr_spend"] - merged["prev_spend"]) / merged["prev_spend"] * 100).round(1),
            0,
        )
        merged["Period"] = f"{prev_month} -> {curr_month}"

        all_movers.append(
            merged[
                [
                    merch_col,
                    "Rank Change",
                    "prev_spend",
                    "curr_spend",
                    "Spend Change",
                    "Spend Change %",
                    "Period",
                ]
            ].rename(
                columns={merch_col: "Merchant", "prev_spend": "Prev $", "curr_spend": "Curr $"}
            )
        )

    if not all_movers:
        return None

    mover_df = pd.concat(all_movers, ignore_index=True)

    # Classify direction
    mover_df["Direction"] = np.where(
        mover_df["Rank Change"] > 0,
        "Climber",
        np.where(mover_df["Rank Change"] < 0, "Faller", "Stable"),
    )

    # --- Top 30 Climbers ---
    climbers = mover_df.sort_values("Rank Change", ascending=False).head(30)
    climbers_plot = climbers.iloc[::-1]
    climbers_label = climbers_plot.apply(lambda r: f"{r['Merchant'][:25]} ({r['Period']})", axis=1)

    climb_fig = go.Figure()
    climb_fig.add_trace(
        go.Bar(
            x=climbers_plot["Rank Change"],
            y=climbers_label,
            orientation="h",
            marker_color=COLORS["positive"],
            text=climbers_plot["Rank Change"].apply(lambda v: f"+{v}"),
            textposition="outside",
            textfont=dict(size=9),
        )
    )
    climb_fig.update_layout(
        title=f"Top 30 {label} Rank Climbers (Positions Gained)",
        xaxis_title="Rank Positions Gained",
        yaxis=dict(automargin=True, tickfont=dict(size=9)),
        height=max(500, 30 * 22),
        margin=dict(l=10),
    )
    climb_fig = apply_theme(climb_fig)

    # --- Top 30 Fallers ---
    fallers = mover_df.sort_values("Rank Change").head(30)
    fallers_plot = fallers.copy()
    fallers_label = fallers_plot.apply(lambda r: f"{r['Merchant'][:25]} ({r['Period']})", axis=1)

    fall_fig = go.Figure()
    fall_fig.add_trace(
        go.Bar(
            x=fallers_plot["Rank Change"],
            y=fallers_label,
            orientation="h",
            marker_color=COLORS["negative"],
            text=fallers_plot["Rank Change"].apply(lambda v: f"{v}"),
            textposition="outside",
            textfont=dict(size=9),
        )
    )
    fall_fig.update_layout(
        title=f"Top 30 {label} Rank Fallers (Positions Lost)",
        xaxis_title="Rank Positions Lost",
        yaxis=dict(automargin=True, tickfont=dict(size=9)),
        height=max(500, 30 * 22),
        margin=dict(l=10),
    )
    fall_fig = apply_theme(fall_fig)

    # Sort output by absolute rank change for the sheet
    mover_df = mover_df.sort_values("Rank Change", key=lambda s: s.abs(), ascending=False)

    return mover_df, climb_fig, fall_fig


# =============================================================================
# Personal Account Rank Movers (M5F)
# =============================================================================


def _personal_rank_movers(subset_df, merch_col):
    """Personal account rank movers with an additional spend-increase chart.

    Returns: (mover_df, climb_fig, fall_fig, spend_increase_fig)
    The spend_increase_fig shows the top 30 merchants by absolute spend
    increase across consecutive months.
    """
    base = _account_rank_movers(subset_df, merch_col, label="Personal")
    if base is None:
        return None

    mover_df, climb_fig, fall_fig = base

    # Compute absolute spend changes for the spend-increase chart
    if "year_month" not in subset_df.columns:
        return None

    sorted_months = sorted(subset_df["year_month"].unique())
    monthly_spend = subset_df.groupby([merch_col, "year_month"])["amount"].sum().reset_index()

    spend_rows = []
    for i in range(len(sorted_months) - 1):
        prev_month = sorted_months[i]
        curr_month = sorted_months[i + 1]

        prev = monthly_spend[monthly_spend["year_month"] == prev_month].set_index(merch_col)[
            "amount"
        ]
        curr = monthly_spend[monthly_spend["year_month"] == curr_month].set_index(merch_col)[
            "amount"
        ]

        all_merchants = set(prev.index) | set(curr.index)
        for merchant in all_merchants:
            prev_val = prev.get(merchant, 0)
            curr_val = curr.get(merchant, 0)
            change = curr_val - prev_val
            if change > 0:
                spend_rows.append(
                    {
                        "Merchant": merchant,
                        "Period": f"{prev_month} -> {curr_month}",
                        "Spend Change": round(change, 2),
                    }
                )

    if not spend_rows:
        empty_fig = go.Figure()
        empty_fig = apply_theme(empty_fig)
        return mover_df, climb_fig, fall_fig, empty_fig

    spend_df = pd.DataFrame(spend_rows).sort_values("Spend Change", ascending=False).head(30)

    spend_plot = spend_df.iloc[::-1]
    spend_label = spend_plot.apply(lambda r: f"{r['Merchant'][:25]} ({r['Period']})", axis=1)

    spend_fig = go.Figure()
    spend_fig.add_trace(
        go.Bar(
            x=spend_plot["Spend Change"],
            y=spend_label,
            orientation="h",
            marker_color=COLORS["accent"],
            text=spend_plot["Spend Change"].apply(lambda v: f"+{format_currency(v)}"),
            textposition="outside",
            textfont=dict(size=9),
        )
    )
    spend_fig.update_layout(
        title="Top 30 Personal Spend Increases (Absolute $)",
        xaxis_title="Spend Increase ($)",
        xaxis_tickprefix="$",
        xaxis_tickformat=",",
        yaxis=dict(automargin=True, tickfont=dict(size=9)),
        height=max(500, 30 * 22),
        margin=dict(l=10),
    )
    spend_fig = apply_theme(spend_fig)

    return mover_df, climb_fig, fall_fig, spend_fig
