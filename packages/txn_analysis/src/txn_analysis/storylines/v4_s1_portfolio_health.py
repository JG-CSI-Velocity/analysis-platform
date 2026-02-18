# v4_s1_portfolio_health.py
# Storyline 1: Portfolio Health Dashboard
# =============================================================================
# Monthly trends, transaction distribution, PIN/Sig mix, activation, balances

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from txn_analysis.v4_themes import (
    COLORS, CATEGORY_PALETTE, apply_theme, format_currency,
    horizontal_bar, line_trend, stacked_bar, donut_chart,
)
from txn_analysis.v4_html_report import build_kpi_html


def run(ctx: dict) -> dict:
    """
    Run Portfolio Health analyses.

    Parameters
    ----------
    ctx : dict with 'combined_df', 'business_df', 'personal_df', 'odd_df', 'config'

    Returns
    -------
    dict with 'title', 'sections' (for HTML), 'sheets' (for Excel)
    """
    df = ctx["combined_df"]
    odd = ctx["odd_df"]
    config = ctx["config"]

    sections = []
    sheets = []

    # --- KPI Summary ---
    kpis = _build_kpis(df, odd)
    sections.append({
        "heading": "Key Performance Indicators",
        "narrative": build_kpi_html(kpis),
        "figures": [],
        "tables": [],
    })

    # --- Monthly Summary ---
    monthly_df, monthly_fig = _monthly_summary(df)
    sections.append({
        "heading": "Monthly Transaction Summary",
        "narrative": _monthly_narrative(monthly_df),
        "figures": [monthly_fig],
        "tables": [("Monthly Summary", monthly_df.head(24))],
    })
    sheets.append({
        "name": "S1 Monthly Summary",
        "df": monthly_df,
        "currency_cols": ["Total Spend", "Avg Transaction", "Median Transaction"],
        "pct_cols": ["Spend Growth %", "Transaction Growth %"],
        "number_cols": ["Accounts", "Transactions", "Unique Merchants"],
    })

    # --- Transaction Distribution ---
    dist_df, dist_fig = _transaction_distribution(df)
    sections.append({
        "heading": "Transaction Distribution by Amount",
        "narrative": _distribution_narrative(dist_df),
        "figures": [dist_fig],
        "tables": [("Distribution", dist_df)],
    })
    sheets.append({
        "name": "S1 Transaction Dist",
        "df": dist_df,
        "currency_cols": ["Total Value"],
        "pct_cols": ["Trans %", "Value %"],
        "number_cols": ["Transactions"],
    })

    # --- Monthly Distribution Variance ---
    if "year_month" in df.columns:
        variance_df, variance_fig = _monthly_distribution_variance(df)
        if variance_df is not None and not variance_df.empty:
            sections.append({
                "heading": "Monthly Transaction Distribution Variance",
                "narrative": _variance_narrative(variance_df),
                "figures": [variance_fig],
                "tables": [("Monthly Bracket %", variance_df)],
            })
            sheets.append({
                "name": "S1 Monthly Dist Var",
                "df": variance_df,
                "currency_cols": [],
                "pct_cols": [c for c in variance_df.columns if c != "Month"],
                "number_cols": [],
            })

            # --- Bracket Volatility Analysis ---
            vol_df = _bracket_volatility(variance_df)
            if vol_df is not None and not vol_df.empty:
                sections.append({
                    "heading": "Bracket Volatility Analysis",
                    "narrative": _volatility_narrative(vol_df),
                    "figures": [],
                    "tables": [("Bracket Volatility", vol_df)],
                })
                sheets.append({
                    "name": "S1 Bracket Volatil",
                    "df": vol_df,
                    "currency_cols": [],
                    "pct_cols": ["Mean %", "Std Dev", "Min %", "Max %", "Range"],
                    "number_cols": [],
                })

    # --- PIN vs Signature Mix ---
    pin_sig_df, pin_sig_fig = _pin_sig_mix(df)
    if pin_sig_df is not None:
        sections.append({
            "heading": "PIN vs Signature Transaction Mix",
            "narrative": (
                "PIN transactions are typically lower-margin but higher-volume. "
                "Signature transactions generate higher interchange revenue."
            ),
            "figures": [pin_sig_fig],
            "tables": [("PIN/Sig Mix", pin_sig_df)],
        })
        sheets.append({
            "name": "S1 PIN Sig Mix",
            "df": pin_sig_df,
            "currency_cols": [],
            "pct_cols": ["PIN %", "Sig %"],
            "number_cols": ["PIN Count", "Sig Count"],
        })

    # --- Balance Distribution ---
    if odd is not None and "Avg Bal" in odd.columns:
        bal_df, bal_fig = _balance_distribution(odd)
        sections.append({
            "heading": "Account Balance Distribution",
            "narrative": _balance_narrative(bal_df),
            "figures": [bal_fig],
            "tables": [("Balance Tiers", bal_df)],
        })
        sheets.append({
            "name": "S1 Balance Dist",
            "df": bal_df,
            "currency_cols": ["Avg Balance", "Total Balance"],
            "pct_cols": ["% of Accounts"],
            "number_cols": ["Accounts"],
        })

    # --- Account Activation ---
    if odd is not None and "Debit?" in odd.columns:
        act_df, act_fig = _activation_analysis(odd)
        sections.append({
            "heading": "Debit Card Activation",
            "narrative": _activation_narrative(act_df),
            "figures": [act_fig],
            "tables": [("Activation", act_df)],
        })
        sheets.append({
            "name": "S1 Activation",
            "df": act_df,
            "currency_cols": [],
            "pct_cols": ["% of Total"],
            "number_cols": ["Accounts"],
        })

    # --- Overall Summary Statistics ---
    summary_df = _summary_statistics(df, odd)
    sections.append({
        "heading": "Overall Summary Statistics",
        "narrative": "Key portfolio-level scalar metrics.",
        "figures": [],
        "tables": [("Summary Statistics", summary_df)],
    })
    sheets.append({
        "name": "S1 Summary Stats", "df": summary_df,
        "currency_cols": [], "number_cols": ["Value"],
    })

    # --- Card Present vs Card Not Present ---
    if "card_present" in df.columns:
        cp_df, cp_fig = _card_present_analysis(df)
        if cp_df is not None:
            sections.append({
                "heading": "Card Present vs Card Not Present",
                "narrative": _cp_narrative(cp_df),
                "figures": [cp_fig],
                "tables": [("CP vs CNP", cp_df)],
            })
            sheets.append({
                "name": "S1 CP vs CNP", "df": cp_df,
                "currency_cols": ["Total Spend"],
                "pct_cols": ["% of Transactions", "% of Spend"],
                "number_cols": ["Transactions"],
            })

    return {
        "title": "S1: Portfolio Health Dashboard",
        "description": (
            "Monthly trends, transaction distribution, PIN/Sig mix, "
            "balance tiers, activation, summary stats, card present/not present"
        ),
        "sections": sections,
        "sheets": sheets,
    }


# =============================================================================
# KPI Builder
# =============================================================================

def _build_kpis(df, odd):
    total_spend = df["amount"].sum()
    total_txn = len(df)
    unique_accounts = df["primary_account_num"].nunique()
    unique_merchants = df["merchant_consolidated"].nunique() if "merchant_consolidated" in df.columns else df["merchant_name"].nunique()
    months = df["year_month"].nunique() if "year_month" in df.columns else 1

    kpis = [
        {"label": "Total Spend", "value": format_currency(total_spend)},
        {"label": "Total Transactions", "value": f"{total_txn:,}"},
        {"label": "Active Accounts", "value": f"{unique_accounts:,}"},
        {"label": "Unique Merchants", "value": f"{unique_merchants:,}"},
        {"label": "Months Analyzed", "value": str(months)},
    ]

    # Add avg monthly spend with MoM change
    if "year_month" in df.columns:
        monthly = df.groupby("year_month")["amount"].sum()
        if len(monthly) >= 2:
            last = monthly.iloc[-1]
            prev = monthly.iloc[-2]
            change = ((last - prev) / prev) * 100 if prev > 0 else 0
            kpis.append({
                "label": "Latest Month Spend",
                "value": format_currency(last),
                "change": change,
            })

    return kpis


# =============================================================================
# Monthly Summary
# =============================================================================

def _monthly_summary(df):
    monthly = df.groupby("year_month").agg({
        "primary_account_num": "nunique",
        "transaction_date": "count",
        "amount": ["sum", "mean", "median"],
        "merchant_name": "nunique",
    }).round(2)

    monthly.columns = [
        "Accounts", "Transactions", "Total Spend",
        "Avg Transaction", "Median Transaction", "Unique Merchants",
    ]

    monthly["Spend Growth %"] = monthly["Total Spend"].pct_change() * 100
    monthly["Transaction Growth %"] = monthly["Transactions"].pct_change() * 100
    monthly = monthly.reset_index()
    monthly["year_month"] = monthly["year_month"].astype(str)
    monthly = monthly.rename(columns={"year_month": "Month"})

    # Chart: dual-axis line (spend + transactions)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["Month"],
        y=monthly["Total Spend"],
        name="Total Spend",
        marker_color=COLORS["primary"],
        opacity=0.7,
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=monthly["Month"],
        y=monthly["Transactions"],
        name="Transactions",
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=3),
        marker=dict(size=8),
        yaxis="y2",
    ))
    fig.update_layout(
        title="Monthly Spend & Transaction Volume",
        yaxis=dict(title="Total Spend ($)", tickprefix="$", tickformat=","),
        yaxis2=dict(title="Transactions", overlaying="y", side="right", tickformat=","),
        legend=dict(orientation="h", y=-0.15),
        hovermode="x unified",
    )
    fig = apply_theme(fig)

    return monthly, fig


def _monthly_narrative(monthly_df):
    if len(monthly_df) < 2:
        return "Insufficient data for trend analysis."

    latest = monthly_df.iloc[-1]
    first = monthly_df.iloc[0]
    spend_change = ((latest["Total Spend"] - first["Total Spend"]) / first["Total Spend"]) * 100

    direction = "grown" if spend_change > 0 else "declined"
    return (
        f"Over the {len(monthly_df)}-month analysis period, total monthly spend has "
        f"<b>{direction} {abs(spend_change):.1f}%</b> from "
        f"{format_currency(first['Total Spend'])} to {format_currency(latest['Total Spend'])}. "
        f"The most recent month shows <b>{int(latest['Accounts']):,}</b> active accounts "
        f"generating <b>{int(latest['Transactions']):,}</b> transactions."
    )


# =============================================================================
# Transaction Distribution
# =============================================================================

AMOUNT_BINS = [0, 1, 5, 10, 25, 50, 100, 500, float("inf")]
AMOUNT_LABELS = ["< $1", "$1-5", "$5-10", "$10-25", "$25-50", "$50-100", "$100-500", "$500+"]
BRACKET_COLORS = [
    COLORS["primary"], COLORS["secondary"], COLORS["accent"],
    COLORS["positive"], "#A23B72", COLORS["negative"], "#5C6B73", COLORS["neutral"],
]


def _transaction_distribution(df):
    df = df.copy()
    df["bracket"] = pd.cut(df["amount"], bins=AMOUNT_BINS, labels=AMOUNT_LABELS, right=False)

    stats = []
    for bracket in AMOUNT_LABELS:
        bracket_data = df[df["bracket"] == bracket]
        count = len(bracket_data)
        total_val = bracket_data["amount"].sum()
        stats.append({
            "Amount Range": bracket,
            "Transactions": count,
            "Trans %": round((count / len(df)) * 100, 1) if len(df) > 0 else 0,
            "Total Value": round(total_val, 2),
            "Value %": round((total_val / df["amount"].sum()) * 100, 1) if df["amount"].sum() > 0 else 0,
        })

    dist_df = pd.DataFrame(stats)

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dist_df["Amount Range"],
        y=dist_df["Transactions"],
        marker_color=BRACKET_COLORS[:len(dist_df)],
        text=[f"{t:,}<br>({p}%)" for t, p in zip(dist_df["Transactions"], dist_df["Trans %"])],
        textposition="outside",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        title="Transaction Volume by Amount Range",
        xaxis_title="Amount Range",
        yaxis_title="Number of Transactions",
        yaxis_tickformat=",",
        showlegend=False,
    )
    fig = apply_theme(fig)

    return dist_df, fig


def _distribution_narrative(dist_df):
    if dist_df.empty:
        return ""
    top_bracket = dist_df.loc[dist_df["Transactions"].idxmax()]
    top_value = dist_df.loc[dist_df["Total Value"].idxmax()]
    small_pct = dist_df[dist_df["Amount Range"].isin(["< $1", "$1-5", "$5-10"])]["Trans %"].sum()
    large_pct = dist_df[dist_df["Amount Range"].isin(["$100-500", "$500+"])]["Value %"].sum()

    return (
        f"The most common transaction range is <b>{top_bracket['Amount Range']}</b> "
        f"({int(top_bracket['Transactions']):,} transactions, {top_bracket['Trans %']}%). "
        f"Small transactions (&lt;$10) account for <b>{small_pct:.1f}%</b> of volume, "
        f"while large transactions (&gt;$100) represent <b>{large_pct:.1f}%</b> of total value. "
        f"The highest-value bracket is <b>{top_value['Amount Range']}</b> "
        f"({format_currency(top_value['Total Value'])})."
    )


# =============================================================================
# Monthly Transaction Distribution Variance
# =============================================================================

def _monthly_distribution_variance(df):
    """Compute bracket percentage distribution per month and build a stacked bar chart."""
    df = df.copy()
    df["bracket"] = pd.cut(
        df["amount"], bins=AMOUNT_BINS, labels=AMOUNT_LABELS, right=False,
    )

    # Crosstab: rows = year_month, columns = bracket, values = % of row total
    crosstab = pd.crosstab(
        df["year_month"], df["bracket"], normalize="index",
    ) * 100

    # Ensure all brackets are present as columns in the correct order
    for label in AMOUNT_LABELS:
        if label not in crosstab.columns:
            crosstab[label] = 0.0
    crosstab = crosstab[AMOUNT_LABELS].round(2)

    if crosstab.empty:
        return None, None

    # Build output DataFrame
    variance_df = crosstab.reset_index()
    variance_df["year_month"] = variance_df["year_month"].astype(str)
    variance_df = variance_df.rename(columns={"year_month": "Month"})

    # Stacked bar chart (100% mode) -- data is already in percentages
    fig = go.Figure()
    for idx, bracket in enumerate(AMOUNT_LABELS):
        color = BRACKET_COLORS[idx % len(BRACKET_COLORS)]
        fig.add_trace(go.Bar(
            x=variance_df["Month"],
            y=variance_df[bracket],
            name=bracket,
            marker_color=color,
            hovertemplate=(
                "%{x}<br>" + bracket + ": %{y:.1f}%<extra></extra>"
            ),
        ))

    fig.update_layout(
        barmode="stack",
        title="Monthly Transaction Distribution by Amount Bracket",
        xaxis=dict(
            title=None,
            tickangle=-45 if len(variance_df) > 8 else 0,
        ),
        yaxis=dict(
            title="% of Transactions",
            ticksuffix="%",
            range=[0, 100],
        ),
        height=500,
    )
    fig = apply_theme(fig)

    return variance_df, fig


def _variance_narrative(variance_df):
    """Summarize how the distribution has shifted over the analysis period."""
    if variance_df is None or len(variance_df) < 2:
        return "Insufficient monthly data for distribution variance analysis."

    bracket_cols = [c for c in variance_df.columns if c != "Month"]
    first_month = variance_df.iloc[0]
    last_month = variance_df.iloc[-1]

    # Find the bracket with the largest absolute shift
    shifts = {}
    for col in bracket_cols:
        shifts[col] = last_month[col] - first_month[col]

    biggest_shift_bracket = max(shifts, key=lambda k: abs(shifts[k]))
    biggest_shift_val = shifts[biggest_shift_bracket]
    shift_dir = "increased" if biggest_shift_val > 0 else "decreased"

    # Find most dominant bracket in the latest month
    dominant = max(bracket_cols, key=lambda c: last_month[c])
    dominant_pct = last_month[dominant]

    return (
        f"Across <b>{len(variance_df)}</b> months, the <b>{biggest_shift_bracket}</b> bracket "
        f"showed the largest shift, having {shift_dir} by "
        f"<b>{abs(biggest_shift_val):.1f} percentage points</b> from "
        f"{first_month[biggest_shift_bracket]:.1f}% to {last_month[biggest_shift_bracket]:.1f}%. "
        f"In the most recent month, the dominant bracket is <b>{dominant}</b> "
        f"at <b>{dominant_pct:.1f}%</b> of all transactions."
    )


# =============================================================================
# Bracket Volatility Analysis
# =============================================================================

VOLATILITY_STABLE_THRESHOLD = 1.0
VOLATILITY_MODERATE_THRESHOLD = 2.0


def _bracket_volatility(variance_df):
    """Compute mean, std, min, max, range, and classification for each bracket."""
    if variance_df is None or len(variance_df) < 2:
        return None

    bracket_cols = [c for c in variance_df.columns if c != "Month"]
    rows = []
    for col in bracket_cols:
        series = variance_df[col]
        mean_val = series.mean()
        std_val = series.std()
        min_val = series.min()
        max_val = series.max()
        range_val = max_val - min_val

        if std_val < VOLATILITY_STABLE_THRESHOLD:
            classification = "Stable"
        elif std_val <= VOLATILITY_MODERATE_THRESHOLD:
            classification = "Moderate"
        else:
            classification = "Volatile"

        rows.append({
            "Bracket": col,
            "Mean %": round(mean_val, 2),
            "Std Dev": round(std_val, 2),
            "Min %": round(min_val, 2),
            "Max %": round(max_val, 2),
            "Range": round(range_val, 2),
            "Classification": classification,
        })

    return pd.DataFrame(rows)


def _volatility_narrative(vol_df):
    """Summarize the most stable and most volatile brackets."""
    if vol_df is None or vol_df.empty:
        return ""

    most_stable = vol_df.loc[vol_df["Std Dev"].idxmin()]
    most_volatile = vol_df.loc[vol_df["Std Dev"].idxmax()]

    stable_count = (vol_df["Classification"] == "Stable").sum()
    moderate_count = (vol_df["Classification"] == "Moderate").sum()
    volatile_count = (vol_df["Classification"] == "Volatile").sum()

    parts = []
    if stable_count > 0:
        parts.append(f"<b>{stable_count}</b> Stable")
    if moderate_count > 0:
        parts.append(f"<b>{moderate_count}</b> Moderate")
    if volatile_count > 0:
        parts.append(f"<b>{volatile_count}</b> Volatile")
    summary = ", ".join(parts)

    return (
        f"Bracket volatility classification: {summary}. "
        f"The most stable bracket is <b>{most_stable['Bracket']}</b> "
        f"(Std Dev: {most_stable['Std Dev']:.2f}%, "
        f"range: {most_stable['Min %']:.1f}%-{most_stable['Max %']:.1f}%). "
        f"The most volatile bracket is <b>{most_volatile['Bracket']}</b> "
        f"(Std Dev: {most_volatile['Std Dev']:.2f}%, "
        f"range: {most_volatile['Min %']:.1f}%-{most_volatile['Max %']:.1f}%), "
        f"suggesting month-over-month fluctuation in this spending segment."
    )


# =============================================================================
# PIN vs Signature Mix
# =============================================================================

def _pin_sig_mix(df):
    if "transaction_type" not in df.columns:
        return None, None

    type_col = df["transaction_type"].str.upper().str.strip()
    has_pin = type_col.isin(["PIN"]).any()
    has_sig = type_col.isin(["SIG", "SIGNATURE"]).any()

    if not (has_pin or has_sig):
        return None, None

    monthly = df.copy()
    monthly["type_clean"] = type_col
    monthly = monthly[monthly["type_clean"].isin(["PIN", "SIG", "SIGNATURE"])]
    monthly["type_clean"] = monthly["type_clean"].replace("SIGNATURE", "SIG")

    pivot = monthly.groupby(["year_month", "type_clean"]).size().unstack(fill_value=0)
    if "PIN" not in pivot.columns:
        pivot["PIN"] = 0
    if "SIG" not in pivot.columns:
        pivot["SIG"] = 0

    result = pd.DataFrame({
        "Month": pivot.index.astype(str),
        "PIN Count": pivot["PIN"].values,
        "Sig Count": pivot["SIG"].values,
    })
    result["Total"] = result["PIN Count"] + result["Sig Count"]
    result["PIN %"] = (result["PIN Count"] / result["Total"] * 100).round(1)
    result["Sig %"] = (result["Sig Count"] / result["Total"] * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=result["Month"], y=result["PIN %"],
        name="PIN", marker_color=COLORS["primary"],
    ))
    fig.add_trace(go.Bar(
        x=result["Month"], y=result["Sig %"],
        name="Signature", marker_color=COLORS["secondary"],
    ))
    fig.update_layout(
        title="PIN vs Signature Mix Over Time",
        barmode="stack",
        yaxis_title="% of Transactions",
        yaxis_range=[0, 100],
        legend=dict(orientation="h", y=-0.15),
    )
    fig = apply_theme(fig)

    return result, fig


# =============================================================================
# Balance Distribution
# =============================================================================

def _balance_distribution(odd):
    bal = odd["Avg Bal"].dropna()
    if bal.empty:
        return pd.DataFrame(), go.Figure()

    bins = [float("-inf"), 0, 500, 2000, 10000, 50000, float("inf")]
    labels = ["Negative", "$0-500", "$500-2K", "$2K-10K", "$10K-50K", "$50K+"]

    odd = odd.copy()
    odd["Balance Tier"] = pd.cut(odd["Avg Bal"], bins=bins, labels=labels)

    tier_stats = odd.groupby("Balance Tier", observed=True).agg({
        "Acct Number": "count",
        "Avg Bal": "mean",
    }).reset_index()
    tier_stats.columns = ["Balance Tier", "Accounts", "Avg Balance"]
    tier_stats["% of Accounts"] = (tier_stats["Accounts"] / tier_stats["Accounts"].sum() * 100).round(1)
    tier_stats["Total Balance"] = tier_stats["Accounts"] * tier_stats["Avg Balance"]
    tier_stats["Avg Balance"] = tier_stats["Avg Balance"].round(2)
    tier_stats["Total Balance"] = tier_stats["Total Balance"].round(2)

    colors = [COLORS["negative"], COLORS["neutral"], COLORS["secondary"],
              COLORS["primary"], COLORS["positive"], COLORS["accent"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tier_stats["Balance Tier"],
        y=tier_stats["Accounts"],
        marker_color=colors[:len(tier_stats)],
        text=[f"{a:,}<br>({p}%)" for a, p in zip(tier_stats["Accounts"], tier_stats["% of Accounts"])],
        textposition="outside",
    ))
    fig.update_layout(
        title="Account Distribution by Average Balance",
        xaxis_title="Balance Tier",
        yaxis_title="Number of Accounts",
        yaxis_tickformat=",",
        showlegend=False,
    )
    fig = apply_theme(fig)

    return tier_stats, fig


def _balance_narrative(bal_df):
    if bal_df.empty:
        return ""
    total = bal_df["Accounts"].sum()
    low = bal_df[bal_df["Balance Tier"].isin(["Negative", "$0-500"])]["Accounts"].sum()
    high = bal_df[bal_df["Balance Tier"].isin(["$10K-50K", "$50K+"])]["Accounts"].sum()
    low_pct = (low / total * 100) if total > 0 else 0
    high_pct = (high / total * 100) if total > 0 else 0
    return (
        f"<b>{low_pct:.1f}%</b> of accounts have balances under $500 (potential attrition risk), "
        f"while <b>{high_pct:.1f}%</b> have balances above $10K (high-value segment). "
        f"Total accounts analyzed: <b>{total:,}</b>."
    )


# =============================================================================
# Activation Analysis
# =============================================================================

def _activation_analysis(odd):
    debit_counts = odd["Debit?"].value_counts()
    total = len(odd)

    result = pd.DataFrame({
        "Status": debit_counts.index,
        "Accounts": debit_counts.values,
        "% of Total": (debit_counts.values / total * 100).round(1),
    })

    colors = [COLORS["positive"], COLORS["negative"], COLORS["neutral"]]
    fig = go.Figure(data=[go.Pie(
        labels=result["Status"],
        values=result["Accounts"],
        hole=0.45,
        marker_colors=colors[:len(result)],
        textinfo="label+percent",
        textfont_size=13,
    )])
    fig.update_layout(title="Debit Card Activation Status", showlegend=True)
    fig = apply_theme(fig)

    return result, fig


def _activation_narrative(act_df):
    if act_df.empty:
        return ""
    total = act_df["Accounts"].sum()
    active_row = act_df[act_df["Status"].astype(str).str.upper().isin(["Y", "YES", "TRUE", "1"])]
    if active_row.empty:
        return f"Total accounts: {total:,}. Unable to determine activation rate."
    active = active_row["Accounts"].iloc[0]
    rate = (active / total * 100) if total > 0 else 0
    inactive = total - active
    return (
        f"<b>{rate:.1f}%</b> of accounts ({active:,}) have an active debit card. "
        f"<b>{inactive:,}</b> accounts without debit cards represent an opportunity "
        f"for activation campaigns."
    )


# =============================================================================
# Summary Statistics Table
# =============================================================================

def _summary_statistics(df, odd):
    total_spend = df["amount"].sum()
    total_txn = len(df)
    unique_accts = df["primary_account_num"].nunique()
    merch_col = "merchant_consolidated" if "merchant_consolidated" in df.columns else "merchant_name"
    unique_merchants = df[merch_col].nunique()
    avg_ticket = df["amount"].mean()
    median_ticket = df["amount"].median()
    months = df["year_month"].nunique() if "year_month" in df.columns else 1

    rows = [
        {"Metric": "Total Spend", "Value": round(total_spend, 2)},
        {"Metric": "Total Transactions", "Value": total_txn},
        {"Metric": "Unique Accounts", "Value": unique_accts},
        {"Metric": "Unique Merchants", "Value": unique_merchants},
        {"Metric": "Months of Data", "Value": months},
        {"Metric": "Avg Transaction", "Value": round(avg_ticket, 2)},
        {"Metric": "Median Transaction", "Value": round(median_ticket, 2)},
        {"Metric": "Avg Txns/Account", "Value": round(total_txn / unique_accts, 1) if unique_accts else 0},
        {"Metric": "Avg Spend/Account", "Value": round(total_spend / unique_accts, 2) if unique_accts else 0},
    ]

    if odd is not None:
        rows.append({"Metric": "ODD Accounts", "Value": len(odd)})
        if "Avg Bal" in odd.columns:
            avg_bal = odd["Avg Bal"].mean()
            rows.append({"Metric": "Avg Balance", "Value": round(avg_bal, 2)})

    return pd.DataFrame(rows)


# =============================================================================
# Card Present vs Card Not Present
# =============================================================================

def _card_present_analysis(df):
    cp_col = df["card_present"].astype(str).str.strip().str.upper()
    cp_map = {
        "Y": "Card Present", "YES": "Card Present", "TRUE": "Card Present", "1": "Card Present",
        "N": "Card Not Present", "NO": "Card Not Present", "FALSE": "Card Not Present", "0": "Card Not Present",
    }
    df = df.copy()
    df["cp_label"] = cp_col.map(cp_map).fillna("Unknown")

    agg = df.groupby("cp_label").agg(
        txn_count=("amount", "count"),
        total_spend=("amount", "sum"),
    ).reset_index()
    total_txn = agg["txn_count"].sum()
    total_spend = agg["total_spend"].sum()
    agg["% of Transactions"] = (agg["txn_count"] / total_txn * 100).round(1) if total_txn else 0
    agg["% of Spend"] = (agg["total_spend"] / total_spend * 100).round(1) if total_spend else 0
    agg.columns = ["Channel", "Transactions", "Total Spend", "% of Transactions", "% of Spend"]
    agg = agg.sort_values("Transactions", ascending=False)

    fig = donut_chart(
        agg["Channel"], agg["Transactions"],
        "Card Present vs Not Present",
        colors=[COLORS["primary"], COLORS["accent"], COLORS["neutral"]],
    )
    fig = apply_theme(fig)
    return agg, fig


def _cp_narrative(cp_df):
    if cp_df.empty:
        return ""
    cp_row = cp_df[cp_df["Channel"] == "Card Present"]
    cnp_row = cp_df[cp_df["Channel"] == "Card Not Present"]
    if cp_row.empty or cnp_row.empty:
        return ""
    cp_pct = cp_row["% of Transactions"].iloc[0]
    cnp_pct = cnp_row["% of Transactions"].iloc[0]
    cnp_spend_pct = cnp_row["% of Spend"].iloc[0]
    return (
        f"Card-present transactions make up <b>{cp_pct:.1f}%</b> of volume. "
        f"Card-not-present (online/e-commerce) accounts for <b>{cnp_pct:.1f}%</b> "
        f"of transactions and <b>{cnp_spend_pct:.1f}%</b> of total spend."
    )
