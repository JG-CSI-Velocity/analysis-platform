# v4_s3_threat_analysis.py
# Storyline 3B: Competitive Threat Intelligence
# =============================================================================
# Threat scoring, bank threats, non-bank threats, top per category
# Runs AFTER v4_s3_competition.py which stores ctx["s3_tagged_df"] and
# ctx["s3_competitor_df"]

import numpy as np
import pandas as pd

from txn_analysis.v4_themes import (
    COLORS,
    COMPETITOR_COLORS,
    apply_theme,
    format_currency,
    horizontal_bar,
    insight_title,
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
BANK_CATEGORIES = ["big_nationals", "regionals", "credit_unions", "digital_banks"]
NON_BANK_CATEGORIES = ["wallets_p2p", "bnpl", "alt_finance"]


def run(ctx: dict) -> dict:
    """Run Competitive Threat Intelligence analyses."""
    comp = ctx.get("s3_competitor_df")
    df = ctx.get("s3_tagged_df")
    if comp is None or comp.empty or df is None:
        return {
            "title": "S3B: Threat Intelligence",
            "description": "No competitor data",
            "sections": [],
            "sheets": [],
        }

    total_accounts = df["primary_account_num"].nunique()
    merch_col = (
        "merchant_consolidated" if "merchant_consolidated" in comp.columns else "merchant_name"
    )
    sections, sheets = [], []

    # Build per-competitor summary (foundation for threat scoring)
    comp_summary = _build_competitor_summary(comp, merch_col, total_accounts)
    if comp_summary.empty:
        return {
            "title": "S3B: Threat Intelligence",
            "description": "No competitor data",
            "sections": [],
            "sheets": [],
        }

    _top_per_category(comp_summary, sections, sheets)
    _threat_score(comp_summary, sections, sheets)
    _threat_by_penetration(comp_summary, sections, sheets)
    _threat_by_spend(comp_summary, sections, sheets)
    _fastest_growing(comp_summary, sections, sheets)
    _material_threats(comp_summary, sections, sheets)
    _nonbank_threats(comp_summary, sections, sheets)

    return {
        "title": "S3B: Threat Intelligence",
        "description": "Threat scoring, bank penetration, momentum, material threats, non-bank threats",
        "sections": sections,
        "sheets": sheets,
    }


def _build_competitor_summary(comp, merch_col, total_accounts):
    """Build per-competitor metrics including growth rate."""
    per_comp = (
        comp.groupby([merch_col, "competitor_category"])
        .agg(
            total_spend=("amount", "sum"),
            txn_count=("amount", "count"),
            unique_accounts=("primary_account_num", "nunique"),
        )
        .reset_index()
        .rename(columns={merch_col: "competitor"})
    )
    per_comp["penetration_pct"] = (per_comp["unique_accounts"] / total_accounts * 100).round(2)

    # Growth rate: last 3 months vs previous 3 months
    if "year_month" in comp.columns:
        sorted_months = sorted(comp["year_month"].unique())
        if len(sorted_months) >= 6:
            recent_3 = sorted_months[-3:]
            prev_3 = sorted_months[-6:-3]
            recent = (
                comp[comp["year_month"].isin(recent_3)]
                .groupby(merch_col)["amount"]
                .sum()
                .rename("recent_spend")
            )
            prev = (
                comp[comp["year_month"].isin(prev_3)]
                .groupby(merch_col)["amount"]
                .sum()
                .rename("prev_spend")
            )
            growth = pd.concat([recent, prev], axis=1).fillna(0)
            growth["growth_rate"] = np.where(
                growth["prev_spend"] > 0,
                (growth["recent_spend"] - growth["prev_spend"]) / growth["prev_spend"] * 100,
                0,
            )
            per_comp = per_comp.merge(
                growth[["growth_rate"]].reset_index().rename(columns={merch_col: "competitor"}),
                on="competitor",
                how="left",
            )
        else:
            per_comp["growth_rate"] = 0.0
    else:
        per_comp["growth_rate"] = 0.0

    per_comp["growth_rate"] = per_comp["growth_rate"].fillna(0.0)
    per_comp["category_label"] = (
        per_comp["competitor_category"].map(CATEGORY_LABELS).fillna(per_comp["competitor_category"])
    )
    return per_comp


def _top_per_category(summary, sections, sheets):
    """Dominant competitor within each category."""
    idx = summary.groupby("competitor_category")["total_spend"].idxmax()
    top = summary.loc[idx].copy()
    cat_totals = summary.groupby("competitor_category")["total_spend"].sum()
    top["category_total"] = top["competitor_category"].map(cat_totals)
    top["market_share"] = (top["total_spend"] / top["category_total"] * 100).round(1)
    top = top.sort_values("total_spend", ascending=False)

    tbl = top[
        ["category_label", "competitor", "total_spend", "unique_accounts", "market_share"]
    ].copy()
    tbl.columns = ["Category", "Top Competitor", "Total Spend", "Accounts", "% of Category"]
    sections.append(
        {
            "heading": "Top Competitor per Category",
            "narrative": (
                f"The dominant competitor overall is <b>{tbl.iloc[0]['Top Competitor']}</b> "
                f"({tbl.iloc[0]['Category']}) with {format_currency(tbl.iloc[0]['Total Spend'])} "
                f"({tbl.iloc[0]['% of Category']:.1f}% of its category)."
            ),
            "figures": [],
            "tables": [("Top per Category", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S3B Top per Category",
            "df": tbl,
            "currency_cols": ["Total Spend"],
            "pct_cols": ["% of Category"],
            "number_cols": ["Accounts"],
        }
    )


def _threat_score(summary, sections, sheets):
    """Composite threat score: 40% penetration + 30% spend + 30% growth."""
    banks = summary[summary["competitor_category"].isin(BANK_CATEGORIES)].copy()
    if banks.empty:
        return

    max_spend = banks["total_spend"].max()
    spend_norm = max_spend if max_spend > 0 else 1

    banks["threat_score"] = (
        banks["penetration_pct"] * 4
        + (banks["total_spend"] / spend_norm * 100) * 3
        + banks["growth_rate"].clip(lower=0) / 10 * 3
    ).round(1)
    banks = banks.sort_values("threat_score", ascending=False).head(15)

    tbl = banks[
        [
            "competitor",
            "category_label",
            "total_spend",
            "unique_accounts",
            "penetration_pct",
            "growth_rate",
            "threat_score",
        ]
    ].copy()
    tbl.columns = [
        "Bank",
        "Category",
        "Total Spend",
        "Accounts",
        "Penetration %",
        "Growth (6mo) %",
        "Threat Score",
    ]
    tbl = tbl.reset_index(drop=True)

    fig = apply_theme(
        horizontal_bar(
            tbl,
            "Threat Score",
            "Bank",
            "Top 15 Bank Competitive Threats",
            top_n=15,
            color=COLORS["negative"],
        )
    )
    fig.update_layout(
        title=insight_title(
            "Bank Competitive Threat Assessment",
            "Score = 40% Penetration + 30% Spend + 30% Growth",
        )
    )

    top = tbl.iloc[0]
    sections.append(
        {
            "heading": "Bank Competitive Threat Score",
            "narrative": (
                f"<b>{top['Bank']}</b> is the highest-scoring threat with a score of "
                f"<b>{top['Threat Score']:.1f}</b> -- {top['Penetration %']:.2f}% account penetration, "
                f"{format_currency(top['Total Spend'])} spend, {top['Growth (6mo) %']:+.1f}% growth. "
                f"Threat Score = 40% Penetration + 30% Spend + 30% Growth."
            ),
            "figures": [fig],
            "tables": [("Threat Scores", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S3B Threat Scores",
            "df": tbl,
            "currency_cols": ["Total Spend"],
            "pct_cols": ["Penetration %", "Growth (6mo) %"],
            "number_cols": ["Accounts", "Threat Score"],
        }
    )


def _threat_by_penetration(summary, sections, sheets):
    """Top 15 banks ranked by account penetration %."""
    banks = summary[summary["competitor_category"].isin(BANK_CATEGORIES)].copy()
    if banks.empty:
        return
    banks = banks.sort_values("penetration_pct", ascending=False).head(15)
    tbl = banks[["competitor", "category_label", "unique_accounts", "penetration_pct"]].copy()
    tbl.columns = ["Bank", "Category", "Accounts", "Penetration %"]
    tbl = tbl.reset_index(drop=True)

    fig = apply_theme(
        horizontal_bar(
            tbl,
            "Penetration %",
            "Bank",
            "Top 15 Banks by Account Penetration",
            top_n=15,
            value_format="{:.2f}%",
        )
    )
    sections.append(
        {
            "heading": "Threats by Account Penetration",
            "narrative": (
                f"<b>{tbl.iloc[0]['Bank']}</b> has the highest account penetration at "
                f"<b>{tbl.iloc[0]['Penetration %']:.2f}%</b> ({int(tbl.iloc[0]['Accounts']):,} accounts)."
            ),
            "figures": [fig],
            "tables": [],
        }
    )


def _threat_by_spend(summary, sections, sheets):
    """Top 15 banks ranked by absolute dollar spend."""
    banks = summary[summary["competitor_category"].isin(BANK_CATEGORIES)].copy()
    if banks.empty:
        return
    banks = banks.sort_values("total_spend", ascending=False).head(15)
    tbl = banks[["competitor", "category_label", "total_spend", "unique_accounts"]].copy()
    tbl.columns = ["Bank", "Category", "Total Spend", "Accounts"]
    tbl = tbl.reset_index(drop=True)

    fig = apply_theme(
        horizontal_bar(
            tbl,
            "Total Spend",
            "Bank",
            "Top 15 Banks by Total Spend",
            top_n=15,
        )
    )
    sections.append(
        {
            "heading": "Threats by Total Spend",
            "narrative": (
                f"<b>{tbl.iloc[0]['Bank']}</b> captures the most spend at "
                f"{format_currency(tbl.iloc[0]['Total Spend'])} across "
                f"{int(tbl.iloc[0]['Accounts']):,} accounts."
            ),
            "figures": [fig],
            "tables": [],
        }
    )


def _fastest_growing(summary, sections, sheets):
    """Top 15 banks with highest 6-month spend growth rate."""
    banks = summary[summary["competitor_category"].isin(BANK_CATEGORIES)].copy()
    if banks.empty:
        return
    banks = banks[banks["growth_rate"] > 0].sort_values("growth_rate", ascending=False).head(15)
    if banks.empty:
        return
    tbl = banks[["competitor", "category_label", "growth_rate", "total_spend"]].copy()
    tbl.columns = ["Bank", "Category", "Growth %", "Total Spend"]
    tbl = tbl.reset_index(drop=True)

    fig = apply_theme(
        horizontal_bar(
            tbl,
            "Growth %",
            "Bank",
            "Fastest Growing Banks (6-Month)",
            top_n=15,
            color=COLORS["accent"],
            value_format="{:.1f}%",
        )
    )
    sections.append(
        {
            "heading": "Fastest Growing Competitors",
            "narrative": (
                f"<b>{tbl.iloc[0]['Bank']}</b> shows the highest momentum at "
                f"<b>{tbl.iloc[0]['Growth %']:+.1f}%</b> 6-month growth "
                f"({format_currency(tbl.iloc[0]['Total Spend'])} total spend). "
                f"Growing competitors represent emerging threats that may require preemptive action."
            ),
            "figures": [fig],
            "tables": [],
        }
    )


def _material_threats(summary, sections, sheets):
    """Banks with 100+ accounts AND $50K+ spend (material threats only)."""
    MIN_ACCOUNTS, MIN_SPEND = 100, 50_000
    banks = summary[summary["competitor_category"].isin(BANK_CATEGORIES)].copy()
    if banks.empty:
        return
    material = banks[
        (banks["unique_accounts"] >= MIN_ACCOUNTS) & (banks["total_spend"] >= MIN_SPEND)
    ]
    if material.empty:
        sections.append(
            {
                "heading": "Material Threats",
                "narrative": (
                    f"No banks meet the material threat thresholds "
                    f"({MIN_ACCOUNTS:,} accounts AND ${MIN_SPEND:,} spend)."
                ),
                "figures": [],
                "tables": [],
            }
        )
        return

    max_spend = material["total_spend"].max() or 1
    material = material.copy()
    material["material_score"] = (
        material["penetration_pct"] * 5 + (material["total_spend"] / max_spend * 100) * 5
    ).round(1)
    material = material.sort_values("material_score", ascending=False).head(15)

    tbl = material[
        [
            "competitor",
            "category_label",
            "unique_accounts",
            "penetration_pct",
            "total_spend",
            "growth_rate",
            "material_score",
        ]
    ].copy()
    tbl.columns = [
        "Bank",
        "Category",
        "Accounts",
        "Penetration %",
        "Total Spend",
        "Growth %",
        "Material Score",
    ]
    tbl = tbl.reset_index(drop=True)

    fig = apply_theme(
        horizontal_bar(
            tbl,
            "Material Score",
            "Bank",
            f"Material Threats ({MIN_ACCOUNTS}+ Accts, ${MIN_SPEND:,}+ Spend)",
            top_n=15,
            color=COLORS["negative"],
        )
    )
    fig.update_layout(
        title=insight_title(
            f"{len(material)} Material Threats Identified",
            f"Minimum: {MIN_ACCOUNTS:,} accounts AND ${MIN_SPEND:,} spend",
        )
    )

    sections.append(
        {
            "heading": "Material Threats (Balanced View)",
            "narrative": (
                f"<b>{len(material)}</b> banks meet the material threat thresholds. "
                f"<b>{tbl.iloc[0]['Bank']}</b> scores highest with "
                f"{int(tbl.iloc[0]['Accounts']):,} accounts and "
                f"{format_currency(tbl.iloc[0]['Total Spend'])} in spend."
            ),
            "figures": [fig],
            "tables": [("Material Threats", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S3B Material Threats",
            "df": tbl,
            "currency_cols": ["Total Spend"],
            "pct_cols": ["Penetration %", "Growth %"],
            "number_cols": ["Accounts", "Material Score"],
        }
    )


def _nonbank_threats(summary, sections, sheets):
    """Wallets/P2P/BNPL isolated as threats to traditional banking."""
    nonbank = summary[summary["competitor_category"].isin(NON_BANK_CATEGORIES)].copy()
    if nonbank.empty:
        sections.append(
            {
                "heading": "Non-Bank Threats",
                "narrative": "No wallet, P2P, or BNPL transactions detected.",
                "figures": [],
                "tables": [],
            }
        )
        return

    nonbank = nonbank.sort_values("total_spend", ascending=False)
    tbl = nonbank[
        [
            "competitor",
            "category_label",
            "total_spend",
            "unique_accounts",
            "txn_count",
            "penetration_pct",
        ]
    ].copy()
    tbl.columns = ["Service", "Type", "Total Spend", "Accounts", "Transactions", "Penetration %"]
    tbl = tbl.reset_index(drop=True)

    fig = apply_theme(
        horizontal_bar(
            tbl,
            "Total Spend",
            "Service",
            "Non-Bank Threats to Banking Relationship",
            top_n=20,
            color=COMPETITOR_COLORS.get("wallets_p2p", COLORS["neutral"]),
        )
    )

    total_nb_spend = tbl["Total Spend"].sum()
    total_nb_accts = tbl["Accounts"].sum()
    sections.append(
        {
            "heading": "Non-Bank Threats to Banking",
            "narrative": (
                f"<b>{len(tbl)}</b> non-bank services (wallets, P2P, BNPL) account for "
                f"{format_currency(total_nb_spend)} in spend across <b>{total_nb_accts:,}</b> "
                f"account relationships. These services replace traditional banking functions -- "
                f"high penetration signals customers finding alternatives to core banking."
            ),
            "figures": [fig],
            "tables": [("Non-Bank Threats", tbl)],
        }
    )
    sheets.append(
        {
            "name": "S3B Non-Bank Threats",
            "df": tbl,
            "currency_cols": ["Total Spend"],
            "pct_cols": ["Penetration %"],
            "number_cols": ["Accounts", "Transactions"],
        }
    )
