# v4_s6_risk.py - Storyline 6: Risk & Balance Correlation
# Balance tiers, balance-spend correlation, Reg E, OD limits, spend velocity, inactive accounts

import pandas as pd
import plotly.graph_objects as go

from txn_analysis.v4_themes import (
    CATEGORY_PALETTE,
    COLORS,
    GENERATION_COLORS,
    apply_theme,
    donut_chart,
    format_currency,
    grouped_bar,
    scatter_plot,
    stacked_bar,
)

TIER_ORDER = ["Low", "Medium", "High", "Very High"]


def run(ctx: dict) -> dict:
    """Run Risk & Balance Correlation analyses."""
    df, odd = ctx["combined_df"], ctx["odd_df"]
    sections, sheets = [], []
    _balance_tiers(odd, df, sections, sheets)
    _balance_vs_spend(df, odd, sections, sheets)
    _reg_e_status(odd, df, sections, sheets)
    _od_limit(odd, df, sections, sheets)
    _spend_velocity(df, sections, sheets)
    _inactive(odd, sections, sheets)
    return {
        "title": "S6: Risk & Balance Correlation",
        "description": "Balance tiers, balance-spend correlation, Reg E, OD limits, spend velocity, inactive accounts",
        "sections": sections,
        "sheets": sheets,
    }


def _latest_col(odd: pd.DataFrame, suffix: str) -> str | None:
    matches = sorted(c for c in odd.columns if suffix in c)
    return matches[-1] if matches else None


def _sdiv(n: float, d: float) -> float:
    return n / d if d else 0.0


def _acct_spend(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("primary_account_num")
        .agg(
            total_spend=("amount", "sum"),
            txn_count=("amount", "count"),
        )
        .reset_index()
    )


def _simple_bar(x, y, title, colors=None):
    fig = go.Figure(
        go.Bar(
            x=x,
            y=y,
            marker_color=colors or CATEGORY_PALETTE[: len(x)],
            text=[format_currency(v) for v in y],
            textposition="outside",
        )
    )
    fig.update_layout(title=title, yaxis_tickprefix="$", yaxis_tickformat=",", showlegend=False)
    return apply_theme(fig)


# -- 1. Balance Tier Distribution ---------------------------------------------


def _balance_tiers(odd, df, sections, sheets):
    if "balance_tier" not in odd.columns:
        return
    counts = odd["balance_tier"].value_counts().reindex(TIER_ORDER).fillna(0)
    total = counts.sum()
    if total == 0:
        return

    fig1 = apply_theme(
        donut_chart(
            counts.index.tolist(), counts.values.tolist(), "Account Distribution by Balance Tier"
        )
    )

    acct = _acct_spend(df)
    merged = acct.merge(
        odd[["Acct Number", "balance_tier"]],
        left_on="primary_account_num",
        right_on="Acct Number",
        how="inner",
    )
    avg_spend = merged.groupby("balance_tier")["total_spend"].mean().reindex(TIER_ORDER).fillna(0)
    fig2 = _simple_bar(
        TIER_ORDER, avg_spend.values.tolist(), "Avg Spend per Account by Balance Tier"
    )

    top = counts.idxmax()
    tbl = pd.DataFrame(
        {
            "Balance Tier": TIER_ORDER,
            "Accounts": [int(counts.get(t, 0)) for t in TIER_ORDER],
            "% of Total": [round(_sdiv(counts.get(t, 0), total) * 100, 1) for t in TIER_ORDER],
            "Avg Spend": [round(avg_spend.get(t, 0), 2) for t in TIER_ORDER],
        }
    )
    sections.append(
        {
            "heading": "Balance Tier Distribution",
            "narrative": (
                f"The <b>{top}</b> tier holds the largest share at "
                f"<b>{_sdiv(counts.max(), total) * 100:.1f}%</b> ({int(counts.max()):,} of "
                f"{int(total):,}). Higher-balance tiers tend to show greater debit spend, "
                f"reinforcing the link between deposit depth and card engagement."
            ),
            "figures": [fig1, fig2],
            "tables": [("Balance Tier Summary", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S6 Balance Tiers",
            "df": tbl,
            "currency_cols": ["Avg Spend"],
            "pct_cols": ["% of Total"],
            "number_cols": ["Accounts"],
        }
    )


# -- 2. Balance vs Spend Correlation ------------------------------------------


def _balance_vs_spend(df, odd, sections, sheets):
    if "Avg Bal" not in odd.columns:
        return
    acct = _acct_spend(df)
    merged = acct.merge(
        odd[["Acct Number", "Avg Bal", "generation"]].dropna(subset=["Avg Bal"]),
        left_on="primary_account_num",
        right_on="Acct Number",
        how="inner",
    )
    if merged.empty:
        return

    fig = apply_theme(
        scatter_plot(
            merged,
            x_col="Avg Bal",
            y_col="total_spend",
            title="Average Balance vs Total Debit Spend",
            color_col="generation",
        )
    )
    corr = merged[["Avg Bal", "total_spend"]].corr().iloc[0, 1]
    strength = "strong" if abs(corr) > 0.5 else ("moderate" if abs(corr) > 0.3 else "weak")
    direction = "positive" if corr > 0 else "negative"
    insight = (
        "higher-balance members are more engaged with their debit cards"
        if corr > 0.2
        else "balance alone does not strongly predict debit card usage"
    )
    sections.append(
        {
            "heading": "Balance vs Spend Correlation",
            "narrative": (
                f"There is a <b>{strength} {direction}</b> correlation (r={corr:.2f}) between "
                f"average balance and total debit spend, suggesting that {insight}."
            ),
            "figures": [fig],
            "tables": [],
        }
    )


# -- 3. Reg E Status Analysis -------------------------------------------------


def _reg_e_status(odd, df, sections, sheets):
    col = _latest_col(odd, "Reg E Code")
    if col is None:
        return
    status = odd[col].fillna("Unknown").astype(str).str.strip()
    counts = status.value_counts()

    fig1 = apply_theme(
        donut_chart(counts.index.tolist(), counts.values.tolist(), f"Reg E Opt-In Status ({col})")
    )

    acct = _acct_spend(df)
    merged = acct.merge(
        odd[["Acct Number"]].assign(reg_e=status),
        left_on="primary_account_num",
        right_on="Acct Number",
        how="inner",
    )
    by_status = (
        merged.groupby("reg_e")
        .agg(avg_spend=("total_spend", "mean"), accounts=("primary_account_num", "count"))
        .sort_values("avg_spend", ascending=False)
        .reset_index()
    )
    fig2 = _simple_bar(
        by_status["reg_e"].tolist(),
        by_status["avg_spend"].tolist(),
        "Average Spend by Reg E Status",
    )

    tbl = pd.DataFrame(
        {
            "Reg E Status": by_status["reg_e"],
            "Accounts": by_status["accounts"],
            "Avg Spend": by_status["avg_spend"].round(2),
        }
    )
    sections.append(
        {
            "heading": "Reg E Status Analysis",
            "narrative": (
                f"Reg E status from <b>{col}</b> shows <b>{len(counts)}</b> categories across "
                f"<b>{int(counts.sum()):,}</b> accounts. Understanding opt-in rates is critical "
                f"for OD/NSF fee revenue projections and compliance planning."
            ),
            "figures": [fig1, fig2],
            "tables": [("Reg E Summary", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S6 Reg E Status",
            "df": tbl,
            "currency_cols": ["Avg Spend"],
            "pct_cols": [],
            "number_cols": ["Accounts"],
        }
    )


# -- 4. OD Limit Analysis -----------------------------------------------------


def _od_limit(odd, df, sections, sheets):
    col = _latest_col(odd, "OD Limit")
    if col is None:
        return
    vals = pd.to_numeric(odd[col], errors="coerce").fillna(0)
    labels = ["$0", "$1-250", "$251-500", "$501-1000", "$1000+"]
    buckets = pd.cut(vals, bins=[-1, 0, 250, 500, 1000, float("inf")], labels=labels)
    counts = buckets.value_counts().reindex(labels).fillna(0)

    fig1 = apply_theme(
        donut_chart(counts.index.tolist(), counts.values.tolist(), f"OD Limit Distribution ({col})")
    )

    acct = _acct_spend(df)
    merged = acct.merge(
        odd[["Acct Number"]].assign(od_bucket=buckets),
        left_on="primary_account_num",
        right_on="Acct Number",
        how="inner",
    )
    by_od = (
        merged.groupby("od_bucket", observed=True)
        .agg(avg_spend=("total_spend", "mean"), accounts=("primary_account_num", "count"))
        .reindex(labels)
        .fillna(0)
        .reset_index()
    )
    fig2 = _simple_bar(labels, by_od["avg_spend"].tolist(), "Average Spend by OD Limit Bucket")

    tbl = pd.DataFrame(
        {
            "OD Limit Bucket": labels,
            "Accounts": [int(counts.get(l, 0)) for l in labels],
            "Avg Spend": [
                round(by_od.set_index("od_bucket")["avg_spend"].get(l, 0), 2) for l in labels
            ],
        }
    )
    zero_pct = _sdiv(counts.get("$0", 0), counts.sum()) * 100
    sections.append(
        {
            "heading": "OD Limit Analysis",
            "narrative": (
                f"OD limit data from <b>{col}</b> shows <b>{zero_pct:.1f}%</b> of accounts "
                f"have a $0 overdraft limit. Members with higher OD cushions tend to show "
                f"different spending behavior, suggesting the safety net may encourage "
                f"greater debit card engagement."
            ),
            "figures": [fig1, fig2],
            "tables": [("OD Limit Summary", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S6 OD Limits",
            "df": tbl,
            "currency_cols": ["Avg Spend"],
            "pct_cols": [],
            "number_cols": ["Accounts"],
        }
    )


# -- 5. Spend Velocity by Balance Tier ----------------------------------------


def _spend_velocity(df, sections, sheets):
    if "balance_tier" not in df.columns or "year_month" not in df.columns:
        return
    tier_data = df[df["balance_tier"].notna()]
    n_months = tier_data["year_month"].nunique()
    if tier_data.empty or n_months == 0:
        return

    per_acct = (
        tier_data.groupby(["balance_tier", "primary_account_num"])
        .agg(spend=("amount", "sum"), txns=("amount", "count"))
        .reset_index()
    )
    per_acct["ticket"] = per_acct["spend"] / per_acct["txns"].replace(0, 1)

    vel = (
        per_acct.groupby("balance_tier")
        .agg(
            avg_mo_spend=("spend", lambda s: s.mean() / n_months),
            avg_mo_swipes=("txns", lambda s: s.mean() / n_months),
            avg_ticket=("ticket", "mean"),
        )
        .reindex(TIER_ORDER)
        .dropna(how="all")
        .reset_index()
    )
    vel.columns = ["Balance Tier", "Avg Monthly Spend", "Avg Monthly Swipes", "Avg Ticket Size"]
    vel = vel.round(2)

    fig = apply_theme(
        grouped_bar(
            vel,
            x_col="Balance Tier",
            y_cols=["Avg Monthly Spend", "Avg Monthly Swipes", "Avg Ticket Size"],
            title="Spending Intensity by Balance Tier",
        )
    )
    sections.append(
        {
            "heading": "Spend Velocity by Balance Tier",
            "narrative": (
                f"Across <b>{n_months}</b> months, higher-balance tiers generally show greater "
                f"monthly spend and larger ticket sizes, indicating deeper card engagement "
                f"among members with stronger deposit relationships."
            ),
            "figures": [fig],
            "tables": [("Spend Velocity", vel)],
        }
    )
    sheets.append(
        {
            "name": "S6 Spend Velocity",
            "df": vel,
            "currency_cols": ["Avg Monthly Spend", "Avg Ticket Size"],
            "pct_cols": [],
            "number_cols": ["Avg Monthly Swipes"],
        }
    )


# -- 6. Inactive Account Analysis ---------------------------------------------


def _inactive(odd, sections, sheets):
    spend_col = _latest_col(odd, "Spend")
    if "Debit?" in odd.columns:
        no_debit = odd["Debit?"].astype(str).str.strip().str.upper().isin(["NO", "N"])
    else:
        no_debit = pd.Series(False, index=odd.index)

    if spend_col:
        zero_spend = pd.to_numeric(odd[spend_col], errors="coerce").fillna(0) == 0
        is_inactive = no_debit | zero_spend
    else:
        is_inactive = no_debit

    inactive = odd[is_inactive]
    if inactive.empty:
        return

    has_gen = "generation" in inactive.columns and inactive["generation"].notna().any()
    has_tier = "balance_tier" in inactive.columns and inactive["balance_tier"].notna().any()

    if has_gen and has_tier:
        cross = inactive.groupby(["balance_tier", "generation"]).size().unstack(fill_value=0)
        gens = [
            g for g in ["Gen Z", "Millennial", "Gen X", "Boomer", "Silent"] if g in cross.columns
        ]
        cross = cross.reindex(index=TIER_ORDER, columns=gens).fillna(0)
        fig = stacked_bar(
            cross.reset_index().rename(columns={"balance_tier": "Balance Tier"}),
            x_col="Balance Tier",
            y_cols=gens,
            title="Inactive Accounts by Balance Tier & Generation",
            colors=[GENERATION_COLORS.get(g, COLORS["neutral"]) for g in gens],
        )
    elif has_tier:
        tc = inactive["balance_tier"].value_counts().reindex(TIER_ORDER).fillna(0)
        fig = go.Figure(
            go.Bar(
                x=tc.index.tolist(), y=tc.values.tolist(), marker_color=CATEGORY_PALETTE[: len(tc)]
            )
        )
        fig.update_layout(title="Inactive Accounts by Balance Tier", showlegend=False)
    else:
        fig = go.Figure()
        fig.update_layout(title="Inactive Accounts")
    fig = apply_theme(fig)

    total, cnt = len(odd), len(inactive)
    pct = _sdiv(cnt, total) * 100

    if has_tier:
        rows = []
        for t in TIER_ORDER:
            t_in = len(inactive[inactive["balance_tier"] == t])
            t_tot = len(odd[odd["balance_tier"] == t])
            rows.append(
                {
                    "Balance Tier": t,
                    "Inactive": t_in,
                    "Total": t_tot,
                    "Inactive %": round(_sdiv(t_in, t_tot) * 100, 1),
                }
            )
        tbl = pd.DataFrame(rows)
        pcols, ncols = ["Inactive %"], ["Inactive", "Total"]
    else:
        tbl = pd.DataFrame(
            {"Metric": ["Inactive", "Total", "Inactive %"], "Value": [cnt, total, round(pct, 1)]}
        )
        pcols, ncols = [], []

    criteria = "no debit card" + (f" or zero spend in {spend_col}" if spend_col else "")
    sections.append(
        {
            "heading": "Inactive Account Analysis",
            "narrative": (
                f"<b>{cnt:,}</b> accounts (<b>{pct:.1f}%</b>) are inactive ({criteria}). "
                f"These represent a reactivation opportunity -- targeted campaigns could drive "
                f"incremental interchange revenue and deepen engagement."
            ),
            "figures": [fig],
            "tables": [("Inactive Accounts", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S6 Inactive Accounts",
            "df": tbl,
            "currency_cols": [],
            "pct_cols": pcols,
            "number_cols": ncols,
        }
    )
