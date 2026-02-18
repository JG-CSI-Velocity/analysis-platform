# v4_s3_competition.py
# Storyline 3: Competitive Landscape
# =============================================================================
# Competitor detection, spend analysis, generational penetration, trends

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from txn_analysis.v4_themes import (
    COLORS,
    COMPETITOR_COLORS,
    apply_theme,
    donut_chart,
    format_currency,
    grouped_bar,
    horizontal_bar,
    line_trend,
    stacked_bar,
)

CATEGORY_LABELS = {
    "big_nationals": "Big Nationals",
    "regionals": "Regionals",
    "credit_unions": "Credit Unions",
    "digital_banks": "Digital Banks",
    "wallets_p2p": "Wallets & P2P",
    "bnpl": "BNPL",
    "alt_finance": "Alt Finance",
}

FINANCIAL_MCC_CODES = [6010, 6011, 6012, 6051, 6211, 6300]

FINANCIAL_KEYWORDS = [
    "BANK",
    "CREDIT UNION",
    "CU ",
    "FCU",
    "SAVINGS BANK",
    "FINANCIAL",
    "LENDING",
    "MORTGAGE",
]


def _detect_competitors(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Tag transactions with competitor_category using YAML config rules.

    Matching priority: exact -> starts_with -> contains.
    False positives from config are excluded before categorizing.
    """
    competitors = config.get("competitors", {})
    false_positives = [fp.upper() for fp in config.get("false_positives", [])]
    merch_col = (
        "merchant_consolidated" if "merchant_consolidated" in df.columns else "merchant_name"
    )
    if merch_col not in df.columns:
        df = df.copy()
        df["competitor_category"] = None
        return df

    df = df.copy()
    names = df[merch_col].fillna("").str.upper().str.strip()

    is_fp = pd.Series(False, index=df.index)
    for fp in false_positives:
        is_fp = is_fp | names.str.contains(fp, regex=False)

    categories = pd.Series(np.nan, index=df.index, dtype=object)

    for cat, rules in competitors.items():
        for pattern in rules.get("exact", []):
            mask = (names == pattern.upper()) & categories.isna() & ~is_fp
            categories[mask] = cat

    for cat, rules in competitors.items():
        for pattern in rules.get("starts_with", []):
            mask = names.str.startswith(pattern.upper()) & categories.isna() & ~is_fp
            categories[mask] = cat

    for cat, rules in competitors.items():
        for pattern in rules.get("contains", []):
            mask = names.str.contains(pattern.upper(), regex=False) & categories.isna() & ~is_fp
            categories[mask] = cat

    df["competitor_category"] = categories
    return df


def run(ctx: dict) -> dict:
    """Run Competitive Landscape analyses."""
    df = ctx["combined_df"]
    config = ctx["config"]
    sections, sheets = [], []

    df = _detect_competitors(df, config)
    comp = df[df["competitor_category"].notna()].copy()

    # Store for sub-modules (threat analysis, segmentation)
    ctx["s3_tagged_df"] = df
    ctx["s3_competitor_df"] = comp

    if comp.empty:
        sections.append(
            {
                "heading": "Competitor Detection",
                "narrative": "No competitor transactions detected with the current configuration.",
                "figures": [],
                "tables": [],
            }
        )
        return {
            "title": "S3: Competitive Landscape",
            "description": "No competitor transactions detected",
            "sections": sections,
            "sheets": [],
        }

    merch_col = (
        "merchant_consolidated" if "merchant_consolidated" in comp.columns else "merchant_name"
    )

    # --- 1. Competitor Summary Dashboard ---
    total_spend = df["amount"].sum()
    comp_spend = comp["amount"].sum()
    comp_pct = (comp_spend / total_spend * 100) if total_spend > 0 else 0
    comp_txn = len(comp)
    comp_accounts = comp["primary_account_num"].nunique()
    total_accounts = df["primary_account_num"].nunique()
    acct_pct = (comp_accounts / total_accounts * 100) if total_accounts > 0 else 0

    cat_spend = comp.groupby("competitor_category")["amount"].sum().sort_values(ascending=False)
    donut_labels = [CATEGORY_LABELS.get(c, c) for c in cat_spend.index]
    donut_colors = [COMPETITOR_COLORS.get(c, COLORS["neutral"]) for c in cat_spend.index]
    donut_fig = apply_theme(
        donut_chart(
            donut_labels,
            cat_spend.values.tolist(),
            "Competitor Spend by Category",
            colors=donut_colors,
        )
    )

    sections.append(
        {
            "heading": "Competitor Summary Dashboard",
            "narrative": (
                f"<b>{format_currency(comp_spend)}</b> in competitor spend detected "
                f"({comp_pct:.1f}% of {format_currency(total_spend)} total spend). "
                f"<b>{comp_txn:,}</b> transactions across <b>{comp_accounts:,}</b> unique accounts "
                f"({acct_pct:.1f}% of {total_accounts:,} total) show activity at competing "
                f"financial institutions and alternative payment platforms."
            ),
            "figures": [donut_fig],
            "tables": [],
        }
    )

    # --- 2. Top Competitors by Spend ---
    top_comp = (
        comp.groupby(merch_col)
        .agg(
            Total_Spend=("amount", "sum"),
            Transactions=("amount", "count"),
            Unique_Accounts=("primary_account_num", "nunique"),
            Category=("competitor_category", "first"),
        )
        .sort_values("Total_Spend", ascending=False)
        .head(25)
        .reset_index()
        .rename(
            columns={
                merch_col: "Merchant",
                "Total_Spend": "Total Spend",
                "Unique_Accounts": "Unique Accounts",
            }
        )
    )
    top_comp["Category Label"] = (
        top_comp["Category"].map(CATEGORY_LABELS).fillna(top_comp["Category"])
    )
    top_fig = apply_theme(
        horizontal_bar(
            top_comp,
            "Total Spend",
            "Merchant",
            "Top 25 Competitor Merchants by Spend",
            top_n=25,
        )
    )

    sections.append(
        {
            "heading": "Top Competitors by Spend",
            "narrative": (
                f"The top competitor is <b>{top_comp.iloc[0]['Merchant']}</b> with "
                f"{format_currency(top_comp.iloc[0]['Total Spend'])} in spend. "
                f"The top 25 competitors account for "
                f"{format_currency(top_comp['Total Spend'].sum())} in total leakage."
            ),
            "figures": [top_fig],
            "tables": [("Top Competitors", top_comp)],
        }
    )
    sheets.append(
        {
            "name": "S3 Top Competitors",
            "df": top_comp,
            "currency_cols": ["Total Spend"],
            "pct_cols": [],
            "number_cols": ["Transactions", "Unique Accounts"],
        }
    )

    # --- 3. Competitor Category Breakdown ---
    cat_agg = (
        comp.groupby("competitor_category")
        .agg(
            Spend=("amount", "sum"),
            Transactions=("amount", "count"),
            Unique_Accounts=("primary_account_num", "nunique"),
        )
        .sort_values("Spend", ascending=False)
        .reset_index()
    )
    cat_agg["Category"] = (
        cat_agg["competitor_category"].map(CATEGORY_LABELS).fillna(cat_agg["competitor_category"])
    )
    cat_agg["Spend %"] = (cat_agg["Spend"] / cat_agg["Spend"].sum() * 100).round(1)
    cat_agg = cat_agg.rename(columns={"Unique_Accounts": "Unique Accounts"})

    top_cat = cat_agg.iloc[0]
    cat_narrative = (
        f"<b>{top_cat['Category']}</b> dominates competitor spend with "
        f"{format_currency(top_cat['Spend'])} ({top_cat['Spend %']:.1f}% of competitor total). "
    )
    if len(cat_agg) > 1:
        second = cat_agg.iloc[1]
        cat_narrative += (
            f"<b>{second['Category']}</b> follows at "
            f"{format_currency(second['Spend'])} ({second['Spend %']:.1f}%)."
        )

    cat_colors = [
        COMPETITOR_COLORS.get(c, COLORS["neutral"]) for c in cat_agg["competitor_category"]
    ]
    cat_fig = go.Figure()
    cat_fig.add_trace(
        go.Bar(
            x=cat_agg["Category"],
            y=cat_agg["Spend"],
            marker_color=cat_colors,
            text=cat_agg["Spend"].apply(format_currency),
            textposition="outside",
            textfont=dict(size=10),
            name="Spend",
        )
    )
    cat_fig.update_layout(
        title="Competitor Spend by Category",
        yaxis_title="Total Spend ($)",
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        showlegend=False,
        height=500,
    )
    cat_fig = apply_theme(cat_fig)

    cat_export = cat_agg[["Category", "Spend", "Transactions", "Unique Accounts", "Spend %"]]
    sections.append(
        {
            "heading": "Competitor Category Breakdown",
            "narrative": cat_narrative,
            "figures": [cat_fig],
            "tables": [("Category Breakdown", cat_export)],
        }
    )
    sheets.append(
        {
            "name": "S3 Category Breakdown",
            "df": cat_export,
            "currency_cols": ["Spend"],
            "pct_cols": ["Spend %"],
            "number_cols": ["Transactions", "Unique Accounts"],
        }
    )

    # --- 4. Competitor Penetration by Generation ---
    if "generation" in comp.columns and comp["generation"].notna().any():
        _add_generation_section(comp, cat_agg, sections, sheets)

    # --- 5. Monthly Competitor Trend ---
    if "year_month" in comp.columns:
        _add_monthly_trend(comp, cat_agg, sections, sheets)

    # --- 6. Branch-Level Competitor Exposure ---
    if "Branch" in comp.columns and comp["Branch"].notna().any():
        _add_branch_exposure(comp, sections, sheets)

    # --- 7. Competitor Penetration by Account Type ---
    biz = ctx.get("business_df", pd.DataFrame())
    per = ctx.get("personal_df", pd.DataFrame())
    if len(biz) > 0 and len(per) > 0:
        _add_account_type_penetration(biz, per, config, sections, sheets)

    # --- 8. Unmatched Financial Merchant Discovery ---
    _add_unmatched_financial(df, merch_col, sections, sheets)

    return {
        "title": "S3: Competitive Landscape",
        "description": (
            "Competitor detection, spend analysis, category breakdown, "
            "generational penetration, trends, branch exposure, "
            "account type penetration, unmatched financial merchants"
        ),
        "sections": sections,
        "sheets": sheets,
    }


# =============================================================================
# Section Builders (extracted for readability)
# =============================================================================


def _add_generation_section(comp, cat_agg, sections, sheets):
    gen_order = ["Gen Z", "Millennial", "Gen X", "Boomer", "Silent"]
    gen_cats = [c for c in cat_agg["competitor_category"] if c in COMPETITOR_COLORS]

    gen_pivot = (
        comp.groupby(["generation", "competitor_category"])["amount"].sum().unstack(fill_value=0)
    )
    gen_totals = gen_pivot.sum(axis=1).replace(0, 1)
    gen_pct = gen_pivot.div(gen_totals, axis=0) * 100
    gen_pct = gen_pct.reindex(index=[g for g in gen_order if g in gen_pct.index])
    gen_pct = gen_pct.reindex(columns=[c for c in gen_cats if c in gen_pct.columns], fill_value=0)
    gen_pct = gen_pct.reset_index().rename(columns={"generation": "Generation"})

    y_cols = [c for c in gen_pct.columns if c != "Generation"]
    renamed = {c: CATEGORY_LABELS.get(c, c) for c in y_cols}
    gen_pct = gen_pct.rename(columns=renamed)
    gen_colors = [COMPETITOR_COLORS.get(c, COLORS["neutral"]) for c in y_cols]

    gen_fig = stacked_bar(
        gen_pct,
        "Generation",
        list(renamed.values()),
        "Competitor Spend Mix by Generation",
        colors=gen_colors,
        as_percentage=False,
    )
    gen_fig.update_layout(
        yaxis_title="% of Competitor Spend", yaxis_ticksuffix="%", yaxis_range=[0, 100]
    )
    gen_fig = apply_theme(gen_fig)

    digital_cols = [
        CATEGORY_LABELS.get(c, c) for c in ["digital_banks", "wallets_p2p", "bnpl"] if c in y_cols
    ]
    gen_narrative = "Competitor usage varies by generation. "
    if digital_cols:
        digital_sums = gen_pct[digital_cols].sum(axis=1)
        if not digital_sums.empty:
            idx = digital_sums.idxmax()
            gen_narrative += (
                f"<b>{gen_pct.loc[idx, 'Generation']}</b> shows the highest digital/fintech "
                f"penetration ({digital_sums.loc[idx]:.1f}% of their competitor spend)."
            )

    sections.append(
        {
            "heading": "Competitor Penetration by Generation",
            "narrative": gen_narrative,
            "figures": [gen_fig],
            "tables": [],
        }
    )
    sheets.append(
        {
            "name": "S3 Generation Mix",
            "df": gen_pct.round(1),
            "currency_cols": [],
            "pct_cols": list(renamed.values()),
            "number_cols": [],
        }
    )


def _add_monthly_trend(comp, cat_agg, sections, sheets):
    monthly = (
        comp.groupby(["year_month", "competitor_category"])["amount"].sum().unstack(fill_value=0)
    )
    if len(monthly) < 2:
        return

    monthly = monthly.sort_index()
    monthly.index = monthly.index.astype(str)
    present_cats = [c for c in cat_agg["competitor_category"] if c in monthly.columns]
    monthly = monthly[present_cats]
    renamed = {c: CATEGORY_LABELS.get(c, c) for c in present_cats}
    monthly = monthly.rename(columns=renamed).reset_index().rename(columns={"year_month": "Month"})

    trend_colors = [COMPETITOR_COLORS.get(c, COLORS["neutral"]) for c in present_cats]
    trend_fig = apply_theme(
        line_trend(
            monthly,
            "Month",
            list(renamed.values()),
            "Monthly Competitor Spend by Category",
            colors=trend_colors,
            y_format="$,.0f",
        )
    )

    val_cols = list(renamed.values())
    first_total = monthly[val_cols].iloc[0].sum()
    last_total = monthly[val_cols].iloc[-1].sum()
    direction = "increased" if last_total > first_total else "decreased"
    change_pct = abs((last_total - first_total) / first_total * 100) if first_total > 0 else 0

    sections.append(
        {
            "heading": "Monthly Competitor Trend",
            "narrative": (
                f"Competitor spend has <b>{direction} {change_pct:.1f}%</b> over the analysis period "
                f"(from {format_currency(first_total)} to {format_currency(last_total)} per month)."
            ),
            "figures": [trend_fig],
            "tables": [],
        }
    )
    sheets.append(
        {
            "name": "S3 Monthly Trend",
            "df": monthly,
            "currency_cols": val_cols,
            "pct_cols": [],
            "number_cols": [],
        }
    )


def _add_branch_exposure(comp, sections, sheets):
    branch_agg = (
        comp.groupby("Branch")
        .agg(
            Competitor_Spend=("amount", "sum"),
            Transactions=("amount", "count"),
            Accounts=("primary_account_num", "nunique"),
        )
        .sort_values("Competitor_Spend", ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"Competitor_Spend": "Competitor Spend"})
    )
    branch_agg["Avg per Account"] = (
        branch_agg["Competitor Spend"] / branch_agg["Accounts"].replace(0, 1)
    ).round(2)

    branch_fig = apply_theme(
        horizontal_bar(
            branch_agg,
            "Competitor Spend",
            "Branch",
            "Top 10 Branches by Competitor Spend",
            color=COLORS["negative"],
            top_n=10,
        )
    )

    top_branch = branch_agg.iloc[0]
    sections.append(
        {
            "heading": "Branch-Level Competitor Exposure",
            "narrative": (
                f"<b>{top_branch['Branch']}</b> has the highest competitor leakage at "
                f"{format_currency(top_branch['Competitor Spend'])} across "
                f"{int(top_branch['Accounts']):,} accounts. "
                f"Targeted retention campaigns at these branches may reduce outflow."
            ),
            "figures": [branch_fig],
            "tables": [("Branch Exposure", branch_agg)],
        }
    )
    sheets.append(
        {
            "name": "S3 Branch Exposure",
            "df": branch_agg,
            "currency_cols": ["Competitor Spend", "Avg per Account"],
            "pct_cols": [],
            "number_cols": ["Transactions", "Accounts"],
        }
    )


def _add_account_type_penetration(biz, per, config, sections, sheets):
    """Compare competitor leakage across Business vs Personal account types."""
    biz_tagged = _detect_competitors(biz, config)
    per_tagged = _detect_competitors(per, config)

    biz_comp = biz_tagged[biz_tagged["competitor_category"].notna()]
    per_comp = per_tagged[per_tagged["competitor_category"].notna()]

    if biz_comp.empty and per_comp.empty:
        return

    biz_cat = (
        biz_comp.groupby("competitor_category").agg(
            Business_Spend=("amount", "sum"),
            Business_Accounts=("primary_account_num", "nunique"),
        )
        if not biz_comp.empty
        else pd.DataFrame(columns=["Business_Spend", "Business_Accounts"])
    )
    per_cat = (
        per_comp.groupby("competitor_category").agg(
            Personal_Spend=("amount", "sum"),
            Personal_Accounts=("primary_account_num", "nunique"),
        )
        if not per_comp.empty
        else pd.DataFrame(columns=["Personal_Spend", "Personal_Accounts"])
    )

    acct_type = biz_cat.join(per_cat, how="outer").fillna(0)
    acct_type = acct_type.reset_index().rename(columns={"competitor_category": "Category Key"})
    acct_type["Category"] = (
        acct_type["Category Key"].map(CATEGORY_LABELS).fillna(acct_type["Category Key"])
    )
    acct_type = acct_type.rename(
        columns={
            "Business_Spend": "Business Spend",
            "Personal_Spend": "Personal Spend",
            "Business_Accounts": "Business Accounts",
            "Personal_Accounts": "Personal Accounts",
        }
    )
    acct_type = acct_type.sort_values(
        by=["Business Spend", "Personal Spend"],
        ascending=False,
    ).reset_index(drop=True)

    acct_fig = apply_theme(
        grouped_bar(
            acct_type,
            "Category",
            ["Business Spend", "Personal Spend"],
            "Competitor Spend: Business vs Personal Accounts",
            colors=[COLORS.get("secondary", COLORS["primary"]), COLORS["primary"]],
        )
    )
    acct_fig.update_layout(
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        yaxis_title="Total Spend ($)",
    )

    biz_total = acct_type["Business Spend"].sum()
    per_total = acct_type["Personal Spend"].sum()
    if biz_total > per_total:
        leader, trailer = "Business", "Personal"
        leader_val, trailer_val = biz_total, per_total
    else:
        leader, trailer = "Personal", "Business"
        leader_val, trailer_val = per_total, biz_total

    ratio = (leader_val / trailer_val) if trailer_val > 0 else 0
    narrative = (
        f"<b>{leader}</b> accounts show more competitor leakage "
        f"({format_currency(leader_val)}) compared to {trailer} accounts "
        f"({format_currency(trailer_val)})"
    )
    if trailer_val > 0:
        narrative += f" -- a {ratio:.1f}x ratio."
    else:
        narrative += "."

    export = acct_type[
        ["Category", "Business Spend", "Personal Spend", "Business Accounts", "Personal Accounts"]
    ]
    sections.append(
        {
            "heading": "Competitor Penetration by Account Type",
            "narrative": narrative,
            "figures": [acct_fig],
            "tables": [("Account Type Penetration", export)],
        }
    )
    sheets.append(
        {
            "name": "S3 Account Type",
            "df": export,
            "currency_cols": ["Business Spend", "Personal Spend"],
            "pct_cols": [],
            "number_cols": ["Business Accounts", "Personal Accounts"],
        }
    )


def _add_unmatched_financial(df, merch_col, sections, sheets):
    """Discover financial merchants not captured by competitor config.

    Uses MCC codes when available, otherwise falls back to keyword matching.
    """
    untagged = df[df["competitor_category"].isna()].copy()
    if untagged.empty:
        return

    mcc_col = "mcc_code"
    if mcc_col in untagged.columns:
        financial = untagged[untagged[mcc_col].isin(FINANCIAL_MCC_CODES)]
    else:
        names_upper = untagged[merch_col].fillna("").str.upper()
        mask = pd.Series(False, index=untagged.index)
        for kw in FINANCIAL_KEYWORDS:
            mask = mask | names_upper.str.contains(kw, regex=False)
        financial = untagged[mask]

    if financial.empty:
        sections.append(
            {
                "heading": "Unmatched Financial Merchant Discovery",
                "narrative": (
                    "No unmatched financial merchants found. "
                    "The competitor configuration appears comprehensive."
                ),
                "figures": [],
                "tables": [],
            }
        )
        return

    summary = (
        financial.groupby(merch_col)
        .agg(
            Total_Spend=("amount", "sum"),
            Transactions=("amount", "count"),
            Unique_Accounts=("primary_account_num", "nunique"),
        )
        .sort_values("Total_Spend", ascending=False)
        .head(20)
        .reset_index()
        .rename(
            columns={
                merch_col: "Merchant",
                "Total_Spend": "Total Spend",
                "Unique_Accounts": "Unique Accounts",
            }
        )
    )

    fig = apply_theme(
        horizontal_bar(
            summary,
            "Total Spend",
            "Merchant",
            "Top 20 Unmatched Financial Merchants",
            color=COLORS.get("warning", COLORS["neutral"]),
            top_n=20,
        )
    )

    total_unmatched_spend = summary["Total Spend"].sum()
    top_merchant = summary.iloc[0]["Merchant"]
    top_spend = summary.iloc[0]["Total Spend"]

    narrative = (
        f"<b>{len(summary)}</b> merchants with financial MCC codes or financial keywords "
        f"are not in the competitor configuration, totaling "
        f"{format_currency(total_unmatched_spend)} in spend. "
        f"The largest is <b>{top_merchant}</b> at {format_currency(top_spend)}. "
        f"These merchants may warrant addition to the competitor config."
    )

    sections.append(
        {
            "heading": "Unmatched Financial Merchant Discovery",
            "narrative": narrative,
            "figures": [fig],
            "tables": [("Unmatched Financial Merchants", summary)],
        }
    )
    sheets.append(
        {
            "name": "S3 Unmatched Financial",
            "df": summary,
            "currency_cols": ["Total Spend"],
            "pct_cols": [],
            "number_cols": ["Transactions", "Unique Accounts"],
        }
    )
