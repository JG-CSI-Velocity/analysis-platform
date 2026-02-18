# v4_s3_segmentation.py
# Storyline 3C: Account Segmentation & At-Risk Analysis
# =============================================================================
# Account segmentation (CU-Focused/Balanced/Competitor-Heavy), at-risk
# identification, scatter plots, marketing list exports.
# Runs AFTER v4_s3_competition.py which stores ctx["s3_tagged_df"] and
# ctx["s3_competitor_df"]

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from txn_analysis.v4_themes import (
    COLORS, COMPETITOR_COLORS, apply_theme, format_currency, format_pct,
    horizontal_bar, stacked_bar, heatmap, scatter_plot, insight_title,
)

CATEGORY_LABELS = {
    "big_nationals": "Big Nationals", "regionals": "Regionals",
    "credit_unions": "Credit Unions", "digital_banks": "Digital Banks",
    "wallets_p2p": "Wallets & P2P", "bnpl": "BNPL", "alt_finance": "Alt Finance",
}

SEG_COLORS = {
    "Competitor-Heavy": COLORS["negative"],
    "Balanced": COLORS["accent"],
    "CU-Focused": COLORS["positive"],
}


def run(ctx: dict) -> dict:
    """Run Account Segmentation & At-Risk analyses."""
    comp = ctx.get("s3_competitor_df")
    df = ctx.get("s3_tagged_df")
    if comp is None or comp.empty or df is None:
        return {"title": "S3C: Account Segmentation", "description": "No competitor data",
                "sections": [], "sheets": []}

    merch_col = "merchant_consolidated" if "merchant_consolidated" in comp.columns else "merchant_name"
    sections, sheets = [], []

    # Build account-level segmentation foundation
    acct_totals = df.groupby("primary_account_num")["amount"].sum().rename("total_spend")
    comp_by_acct = comp.groupby(["primary_account_num", merch_col]).agg(
        comp_spend=("amount", "sum"),
    ).reset_index()
    comp_acct_total = comp.groupby("primary_account_num")["amount"].sum().rename("competitor_spend")

    acct_seg = pd.DataFrame({"total_spend": acct_totals}).join(comp_acct_total, how="left")
    acct_seg["competitor_spend"] = acct_seg["competitor_spend"].fillna(0)
    acct_seg["cu_spend"] = acct_seg["total_spend"] - acct_seg["competitor_spend"]
    acct_seg["competitor_pct"] = np.where(
        acct_seg["total_spend"] > 0,
        acct_seg["competitor_spend"] / acct_seg["total_spend"] * 100,
        0,
    )
    acct_seg["segment"] = pd.cut(
        acct_seg["competitor_pct"],
        bins=[-0.01, 25, 50, 100.01],
        labels=["CU-Focused", "Balanced", "Competitor-Heavy"],
    )

    # Store for downstream use (S9 lifecycle can reference)
    ctx["s3_account_segments"] = acct_seg

    _segmentation_overview(acct_seg, sections, sheets)
    _segmentation_by_competitor(comp, merch_col, acct_totals, sections, sheets)
    _segmentation_heatmap(comp, merch_col, acct_totals, sections, sheets)
    _at_risk_accounts(acct_seg, sections, sheets)
    _spend_scatter(acct_seg, sections, sheets)
    _spend_comparison(acct_seg, sections, sheets)
    _marketing_lists(acct_seg, ctx, sections, sheets)

    return {
        "title": "S3C: Account Segmentation & At-Risk",
        "description": "Account segmentation, at-risk identification, scatter analysis, marketing lists",
        "sections": sections,
        "sheets": sheets,
    }


def _segmentation_overview(acct_seg, sections, sheets):
    """Overall account segmentation distribution."""
    seg_counts = acct_seg["segment"].value_counts()
    total = len(acct_seg)
    tbl = pd.DataFrame({
        "Segment": ["CU-Focused", "Balanced", "Competitor-Heavy"],
        "Accounts": [int(seg_counts.get(s, 0)) for s in ["CU-Focused", "Balanced", "Competitor-Heavy"]],
    })
    tbl["% of Total"] = (tbl["Accounts"] / total * 100).round(1)
    tbl["Avg Competitor %"] = [
        round(acct_seg[acct_seg["segment"] == s]["competitor_pct"].mean(), 1) if seg_counts.get(s, 0) > 0 else 0
        for s in ["CU-Focused", "Balanced", "Competitor-Heavy"]
    ]
    tbl["Total Competitor Spend"] = [
        round(acct_seg[acct_seg["segment"] == s]["competitor_spend"].sum(), 2)
        for s in ["CU-Focused", "Balanced", "Competitor-Heavy"]
    ]

    colors = [SEG_COLORS[s] for s in tbl["Segment"]]
    fig = go.Figure(go.Bar(
        x=tbl["Segment"], y=tbl["Accounts"], marker_color=colors,
        text=[f"{a:,}<br>({p}%)" for a, p in zip(tbl["Accounts"], tbl["% of Total"])],
        textposition="outside",
    ))
    fig.update_layout(title="Account Segmentation Distribution", yaxis_tickformat=",",
                       showlegend=False, height=450)
    fig = apply_theme(fig)
    fig.update_layout(title=insight_title(
        "Account Segmentation Distribution",
        "CU-Focused (<25%), Balanced (25-50%), Competitor-Heavy (>50%)",
    ))

    heavy = seg_counts.get("Competitor-Heavy", 0)
    heavy_pct = heavy / total * 100 if total > 0 else 0
    sections.append({
        "heading": "Account Segmentation Overview",
        "narrative": (
            f"Of <b>{total:,}</b> accounts with debit card activity, "
            f"<b>{heavy:,}</b> ({heavy_pct:.1f}%) are <b>Competitor-Heavy</b> "
            f"(>50% of spend at competitors). "
            f"<b>{seg_counts.get('Balanced', 0):,}</b> are Balanced (25-50%) and "
            f"<b>{seg_counts.get('CU-Focused', 0):,}</b> are CU-Focused (<25%)."
        ),
        "figures": [fig], "tables": [("Segmentation Overview", tbl)],
    })
    sheets.append({
        "name": "S3C Segmentation", "df": tbl,
        "currency_cols": ["Total Competitor Spend"],
        "pct_cols": ["% of Total", "Avg Competitor %"],
        "number_cols": ["Accounts"],
    })


def _segmentation_by_competitor(comp, merch_col, acct_totals, sections, sheets):
    """Stacked bar of CU-Focused/Balanced/Competitor-Heavy per top 15 competitors."""
    per_comp_acct = comp.groupby([merch_col, "primary_account_num"])["amount"].sum().reset_index()
    per_comp_acct["total_spend"] = per_comp_acct["primary_account_num"].map(acct_totals)
    per_comp_acct["comp_pct"] = np.where(
        per_comp_acct["total_spend"] > 0,
        per_comp_acct["amount"] / per_comp_acct["total_spend"] * 100, 0,
    )
    per_comp_acct["segment"] = pd.cut(
        per_comp_acct["comp_pct"], bins=[-0.01, 25, 50, 100.01],
        labels=["CU-Focused", "Balanced", "Competitor-Heavy"],
    )

    comp_totals = per_comp_acct.groupby(merch_col)["primary_account_num"].nunique()
    top_15 = comp_totals.sort_values(ascending=False).head(15).index.tolist()
    filtered = per_comp_acct[per_comp_acct[merch_col].isin(top_15)]

    pivot = (filtered.groupby([merch_col, "segment"]).size()
             .unstack(fill_value=0).reindex(top_15))
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0).mul(100).round(1)
    for s in ["CU-Focused", "Balanced", "Competitor-Heavy"]:
        if s not in pivot_pct.columns:
            pivot_pct[s] = 0.0
    pivot_pct = pivot_pct[["Competitor-Heavy", "Balanced", "CU-Focused"]]

    chart_df = pivot_pct.reset_index().rename(columns={merch_col: "Competitor"})
    chart_df["Competitor"] = chart_df["Competitor"].astype(str).str[:35]

    fig = stacked_bar(
        chart_df, "Competitor", ["Competitor-Heavy", "Balanced", "CU-Focused"],
        "Account Segmentation by Top 15 Competitors",
        colors=[SEG_COLORS["Competitor-Heavy"], SEG_COLORS["Balanced"], SEG_COLORS["CU-Focused"]],
        as_percentage=False,
    )
    fig.update_layout(yaxis_title="% of Accounts", yaxis_ticksuffix="%", yaxis_range=[0, 100])
    fig = apply_theme(fig)

    sections.append({
        "heading": "Segmentation by Competitor",
        "narrative": (
            "The stacked bar shows account loyalty distribution for the top 15 competitors "
            "by account count. High <b>Competitor-Heavy</b> (red) bars indicate competitors "
            "with strong account capture -- priority targets for retention campaigns."
        ),
        "figures": [fig], "tables": [],
    })


def _segmentation_heatmap(comp, merch_col, acct_totals, sections, sheets):
    """Risk-colored heatmap: competitors x segments with account counts."""
    per_comp_acct = comp.groupby([merch_col, "primary_account_num"])["amount"].sum().reset_index()
    per_comp_acct["total_spend"] = per_comp_acct["primary_account_num"].map(acct_totals)
    per_comp_acct["comp_pct"] = np.where(
        per_comp_acct["total_spend"] > 0,
        per_comp_acct["amount"] / per_comp_acct["total_spend"] * 100, 0,
    )
    per_comp_acct["segment"] = pd.cut(
        per_comp_acct["comp_pct"], bins=[-0.01, 25, 50, 100.01],
        labels=["CU-Focused", "Balanced", "Competitor-Heavy"],
    )

    comp_totals = per_comp_acct.groupby(merch_col)["primary_account_num"].nunique()
    top_15 = comp_totals.sort_values(ascending=False).head(15).index.tolist()
    filtered = per_comp_acct[per_comp_acct[merch_col].isin(top_15)]

    pivot = (filtered.groupby([merch_col, "segment"]).size()
             .unstack(fill_value=0).reindex(top_15))
    for s in ["CU-Focused", "Balanced", "Competitor-Heavy"]:
        if s not in pivot.columns:
            pivot[s] = 0
    pivot = pivot[["Competitor-Heavy", "Balanced", "CU-Focused"]]
    pivot.index = [str(c)[:35] for c in pivot.index]

    fig = heatmap(pivot, "Account Segmentation Heatmap", colorscale="RdYlGn_r")
    fig = apply_theme(fig)

    sections.append({
        "heading": "Segmentation Heatmap",
        "narrative": (
            "The heatmap visualizes account counts by segment for each competitor. "
            "Red intensity indicates higher Competitor-Heavy concentrations -- "
            "these are the highest-risk relationships."
        ),
        "figures": [fig], "tables": [],
    })
    heatmap_df = pivot.reset_index().rename(columns={pivot.index.name or "index": "Competitor"})
    sheets.append({
        "name": "S3C Segmentation Heatmap", "df": heatmap_df,
        "currency_cols": [], "pct_cols": [],
        "number_cols": ["Competitor-Heavy", "Balanced", "CU-Focused"],
    })


def _at_risk_accounts(acct_seg, sections, sheets):
    """Accounts with 80%+ competitor spend (at-risk)."""
    at_risk = acct_seg[acct_seg["competitor_pct"] >= 80].copy()
    if at_risk.empty:
        sections.append({
            "heading": "At-Risk Accounts",
            "narrative": "No accounts have 80%+ of spend at competitors.",
            "figures": [], "tables": [],
        })
        return

    at_risk = at_risk.sort_values("competitor_spend", ascending=False)
    total = len(acct_seg)
    risk_count = len(at_risk)
    risk_spend = at_risk["competitor_spend"].sum()
    risk_pct = risk_count / total * 100 if total > 0 else 0

    # Bucket at-risk accounts by competitor %
    buckets = pd.cut(
        at_risk["competitor_pct"],
        bins=[79.99, 85, 90, 95, 100.01],
        labels=["80-85%", "85-90%", "90-95%", "95-100%"],
    )
    bucket_counts = buckets.value_counts().reindex(["80-85%", "85-90%", "90-95%", "95-100%"]).fillna(0)

    fig = go.Figure(go.Bar(
        x=bucket_counts.index.tolist(), y=bucket_counts.values.tolist(),
        marker_color=[COLORS["accent"], COLORS["accent"], COLORS["negative"], COLORS["negative"]],
        text=[f"{int(v):,}" for v in bucket_counts.values],
        textposition="outside",
    ))
    fig.update_layout(title="At-Risk Accounts by Competitor Spend %",
                       yaxis_tickformat=",", showlegend=False, height=400)
    fig = apply_theme(fig)
    fig.update_layout(title=insight_title(
        f"{risk_count:,} At-Risk Accounts Identified",
        f"{risk_pct:.1f}% of accounts, {format_currency(risk_spend)} competitor spend",
    ))

    top_20 = at_risk.head(20).reset_index()
    top_20.columns = ["Account", "Total Spend", "Competitor Spend", "CU Spend", "Competitor %", "Segment"]
    top_20 = top_20[["Account", "Total Spend", "Competitor Spend", "CU Spend", "Competitor %"]]

    sections.append({
        "heading": "At-Risk Accounts (80%+ Competitor Spend)",
        "narrative": (
            f"<b>{risk_count:,}</b> accounts ({risk_pct:.1f}%) have 80%+ of their spend at "
            f"competitors, representing {format_currency(risk_spend)} in competitor leakage. "
            f"These accounts are at highest risk of full attrition."
        ),
        "figures": [fig], "tables": [("At-Risk Top 20", top_20)],
    })
    sheets.append({
        "name": "S3C At-Risk Accounts", "df": at_risk.head(100).reset_index().rename(
            columns={"primary_account_num": "Account", "total_spend": "Total Spend",
                     "competitor_spend": "Competitor Spend", "cu_spend": "CU Spend",
                     "competitor_pct": "Competitor %", "segment": "Segment"}
        ),
        "currency_cols": ["Total Spend", "Competitor Spend", "CU Spend"],
        "pct_cols": ["Competitor %"], "number_cols": [],
    })


def _spend_scatter(acct_seg, sections, sheets):
    """CU spend vs competitor spend scatter with quadrant analysis."""
    # Sample for performance (scatter with millions of points is slow)
    plot_data = acct_seg.copy()
    if len(plot_data) > 5000:
        plot_data = plot_data.sample(5000, random_state=42)

    plot_data = plot_data.reset_index().rename(columns={
        "primary_account_num": "Account",
        "cu_spend": "CU Spend",
        "competitor_spend": "Competitor Spend",
    })

    fig = scatter_plot(
        plot_data, x_col="CU Spend", y_col="Competitor Spend",
        title="CU Spend vs Competitor Spend by Account",
        hover_col="Account",
    )

    # Add quadrant reference lines at medians
    med_cu = acct_seg["cu_spend"].median()
    med_comp = acct_seg["competitor_spend"].median()
    fig.add_hline(y=med_comp, line_dash="dash", line_color=COLORS["neutral"],
                   annotation_text="Median Comp Spend")
    fig.add_vline(x=med_cu, line_dash="dash", line_color=COLORS["neutral"],
                   annotation_text="Median CU Spend")

    # Quadrant annotations
    fig.add_annotation(x=med_cu * 2, y=med_comp * 2, text="HIGH RISK", showarrow=False,
                        font=dict(color=COLORS["negative"], size=12))
    fig.add_annotation(x=med_cu * 2, y=med_comp * 0.3, text="WINNING", showarrow=False,
                        font=dict(color=COLORS["positive"], size=12))
    fig = apply_theme(fig)

    sections.append({
        "heading": "CU Spend vs Competitor Spend",
        "narrative": (
            "Each point represents an account. Accounts in the upper-left quadrant "
            "(high competitor spend, low CU spend) are <b>high risk</b>. "
            "Accounts in the lower-right (high CU spend, low competitor) are "
            "<b>winning</b>. The dashed lines show median values."
        ),
        "figures": [fig], "tables": [],
    })


def _spend_comparison(acct_seg, sections, sheets):
    """Top 20 accounts: CU spend vs competitor spend stacked bar."""
    top_20 = acct_seg.sort_values("competitor_spend", ascending=False).head(20).copy()
    top_20 = top_20.reset_index()
    top_20["label"] = top_20["primary_account_num"].astype(str).str[:12]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Competitor Spend", y=top_20["label"], x=top_20["competitor_spend"],
        orientation="h", marker_color=COLORS["negative"],
    ))
    fig.add_trace(go.Bar(
        name="CU Spend", y=top_20["label"], x=top_20["cu_spend"],
        orientation="h", marker_color=COLORS["positive"],
    ))
    fig.update_layout(
        barmode="stack", title="Top 20 Accounts: CU vs Competitor Spend",
        xaxis_tickprefix="$", xaxis_tickformat=",",
        height=max(450, len(top_20) * 25 + 100),
    )
    fig = apply_theme(fig)

    sections.append({
        "heading": "Spend Comparison: Top 20 Accounts",
        "narrative": (
            "The stacked bar compares CU spend (green) vs competitor spend (red) for the "
            "20 accounts with highest competitor leakage. Long red bars indicate accounts "
            "where the competitor relationship dominates."
        ),
        "figures": [fig], "tables": [],
    })


def _marketing_lists(acct_seg, ctx, sections, sheets):
    """Generate AT-RISK and OPPORTUNITY account CSVs."""
    output_dir = ctx.get("output_dir", "")
    if not output_dir:
        sections.append({
            "heading": "Marketing Lists",
            "narrative": (
                "Marketing list export requires an output directory. "
                "Set output_dir in config to enable CSV export."
            ),
            "figures": [], "tables": [],
        })
        return

    # AT-RISK: 80%+ competitor spend
    at_risk = acct_seg[acct_seg["competitor_pct"] >= 80].copy()
    at_risk = at_risk.sort_values("competitor_spend", ascending=False).reset_index()
    at_risk.columns = ["Account", "Total Spend", "Competitor Spend", "CU Spend",
                        "Competitor %", "Segment"]

    # OPPORTUNITY: <20% competitor spend + >$500 total spend
    opportunity = acct_seg[
        (acct_seg["competitor_pct"] < 20) & (acct_seg["total_spend"] >= 500)
    ].copy()
    opportunity = opportunity.sort_values("total_spend", ascending=False).reset_index()
    opportunity.columns = ["Account", "Total Spend", "Competitor Spend", "CU Spend",
                            "Competitor %", "Segment"]

    files_written = []
    for name, list_df in [("AT_RISK", at_risk), ("OPPORTUNITY", opportunity)]:
        path = os.path.join(output_dir, f"S3_Marketing_{name}.csv")
        try:
            list_df.to_csv(path, index=False)
            files_written.append((name, len(list_df), path))
        except (OSError, PermissionError):
            pass

    if files_written:
        summary_lines = [f"<b>{n}</b>: {c:,} accounts ({p})" for n, c, p in files_written]
        sections.append({
            "heading": "Marketing List Exports",
            "narrative": (
                "Generated targeted marketing lists:<br>"
                + "<br>".join(summary_lines)
                + "<br><br>AT-RISK = 80%+ competitor spend (retention priority). "
                "OPPORTUNITY = <20% competitor, $500+ total spend (growth candidates)."
            ),
            "figures": [], "tables": [],
        })
