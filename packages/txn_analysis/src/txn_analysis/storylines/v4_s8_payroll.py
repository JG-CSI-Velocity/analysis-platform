# v4_s8_payroll.py  --  Storyline 8: Payroll & Circular Economy
# Payroll detection, employer analysis, generational demographics, trends,
# and debit-spend recapture rate.
from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go

from txn_analysis.charts.builders import (
    donut_chart,
    grouped_bar,
    horizontal_bar,
    insight_title,
    line_trend,
)
from txn_analysis.charts.theme import (
    COLORS,
    GENERATION_COLORS,
    apply_theme,
    format_currency,
)

_KNOWN_PROCESSORS = {
    "ADP",
    "PAYCHEX",
    "INTUIT",
    "BAMBOOHR",
    "GUSTO",
    "PAYLOCITY",
    "PAYCOM",
    "CERIDIAN",
    "WORKDAY",
    "RIPPLING",
    "NAMELY",
}
_GEN_ORDER = ["Gen Z", "Millennial", "Gen X", "Boomer", "Silent"]

_NOISE_PATTERNS = [
    r"QUICKBOOKS",
    r"XXXXX\d+",
    r"IC[A-Z]{2}\d+",
    r"DIR DEP",
    r"DEPOSIT",
    r"REIMBURSEM",
    r"TAXIMPOUND",
    r"DBA",
    r"FEES",
    r"\d{8,}",
]

_NOISE_WORDS = {"THE", "INC", "LLC", "CO", "AND", "FOR", "TAX", "DIR", "DEP"}

_GENERIC_SKIP_TERMS = {
    "CAPITAL",
    "CONSTRUCTION",
    "GREATER",
    "ASSOCIATION",
    "SERVICES",
    "MANAGEMENT",
}


def _extract_business_name(payroll_string: str) -> str | None:
    """Extract clean business name from a raw payroll merchant string.

    Strips known processor names, noise patterns, special characters,
    and noise words, then returns the first 3 meaningful words (min 2
    chars each).  Returns None if nothing usable remains.
    """
    cleaned = str(payroll_string).upper()

    # Remove known processor names
    for proc in _KNOWN_PROCESSORS:
        cleaned = cleaned.replace(proc, "")
    cleaned = cleaned.replace("PAYROLL", "")

    # Remove noise patterns
    for pat in _NOISE_PATTERNS:
        cleaned = re.sub(pat, "", cleaned)

    # Keep only letters, spaces, &, apostrophes, hyphens
    cleaned = re.sub(r"[^A-Z\s&'\-]", " ", cleaned)

    # Extract meaningful words (min 2 chars, not noise)
    words = [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]
    words = [w for w in words if w not in _NOISE_WORDS]

    if len(words) >= 2:
        return " ".join(words[:3]).strip()
    if len(words) == 1:
        return words[0].strip()
    return None


def _detect_payroll(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Identify payroll transactions via merchant name pattern matching."""
    pay_cfg = config.get("payroll", {})
    processors: list[str] = pay_cfg.get("processors", ["PAYROLL"])
    skip_terms = [t.upper() for t in pay_cfg.get("skip_terms", [])]
    min_spend: float = pay_cfg.get("min_spend", 10_000)
    max_match: int = pay_cfg.get("max_match_count", 1_000)

    merch_upper = df["merchant_consolidated"].str.upper()
    matched = pd.Series(False, index=df.index)
    labels = pd.Series("", index=df.index)

    for pattern in processors:
        pat = pattern.upper()
        hits = merch_upper.str.contains(pat, na=False, regex=False)
        is_known = any(kp in pat for kp in _KNOWN_PROCESSORS)
        if not is_known and skip_terms:
            residual = merch_upper.str.replace(pat, "", regex=False).str.strip()
            skip = pd.Series(False, index=df.index)
            for term in skip_terms:
                skip = skip | residual.str.contains(term, na=False, regex=False)
            hits = hits & ~skip
        matched = matched | hits
        labels = labels.where(~hits, merch_upper)

    payroll_df = df.loc[matched].copy()
    payroll_df["payroll_employer"] = labels.loc[matched]

    if min_spend > 0:
        stats = df.groupby("merchant_consolidated").agg(
            total=("amount", "sum"),
            accts=("primary_account_num", "nunique"),
        )
        cands = stats[(stats["total"] >= min_spend) & (stats["accts"] <= max_match)].index
        extra_mask = df["merchant_consolidated"].isin(cands) & ~df.index.isin(payroll_df.index)
        if extra_mask.any():
            extra = df.loc[extra_mask].copy()
            extra["payroll_employer"] = extra["merchant_consolidated"].str.upper()
            payroll_df = pd.concat([payroll_df, extra], ignore_index=True)
    return payroll_df


def run(ctx: dict) -> dict:
    """Run Payroll & Circular Economy analyses."""
    df = ctx["combined_df"]
    config = ctx.get("config", {})
    sections: list[dict] = []
    sheets: list[dict] = []
    payroll_df = _detect_payroll(df, config)
    empty_result = {
        "title": "S8: Payroll & Circular Economy",
        "description": "Payroll detection, employer analysis, workforce demographics, recapture rate",
        "sections": sections,
        "sheets": sheets,
    }
    if payroll_df.empty:
        sections.append(
            {
                "heading": "Payroll Detection",
                "narrative": "No payroll transactions were detected.",
                "figures": [],
                "tables": [],
            }
        )
        return empty_result

    s, sh = _payroll_summary(df, payroll_df)
    sections.append(s)
    sheets.append(sh)
    s, sh = _top_employers(payroll_df)
    sections.append(s)
    sheets.append(sh)
    if "generation" in payroll_df.columns:
        s, sh = _payroll_by_generation(payroll_df)
        sections.append(s)
        sheets.append(sh)
    if "year_month" in payroll_df.columns:
        s, sh = _monthly_trends(payroll_df)
        sections.append(s)
        sheets.append(sh)
    circ = _circular_economy(df, payroll_df)
    if circ[0] is not None:
        sections.append(circ[0])
        sheets.append(circ[1])

    # --- New analyses ported from 11_payroll.py ---
    clean_result = _clean_employer_list(payroll_df)
    if clean_result[0] is not None:
        sections.append(clean_result[0])
        sheets.append(clean_result[1])

    personal_df = ctx.get("personal_df")
    if personal_df is not None and not payroll_df.empty:
        circ_detail = _circular_economy_detail(payroll_df, personal_df, config)
        if circ_detail[0] is not None:
            sections.append(circ_detail[0])
            sheets.append(circ_detail[1])

    if "year_month" in payroll_df.columns:
        mom = _payroll_mom_growth(payroll_df)
        if mom[0] is not None:
            sections.append(mom[0])
            sheets.append(mom[1])

    return empty_result  # sections/sheets already mutated into it


def _payroll_summary(df: pd.DataFrame, pay: pd.DataFrame):
    total_pay = pay["amount"].sum()
    total_all = df["amount"].sum()
    n_employers = pay["payroll_employer"].nunique()
    n_accounts = pay["primary_account_num"].nunique()
    pct = (total_pay / total_all * 100) if total_all > 0 else 0

    fig = donut_chart(
        labels=["Payroll Spend", "Non-Payroll Spend"],
        values=[total_pay, max(total_all - total_pay, 0)],
        title="Payroll vs Non-Payroll Spend",
        colors=[COLORS["primary"], COLORS["neutral"]],
    )
    apply_theme(fig)

    narrative = (
        (
            f"Detected <b>{format_currency(total_pay)}</b> in payroll transactions "
            f"across <b>{n_employers:,}</b> employers and <b>{n_accounts:,}</b> accounts. "
            f"Payroll represents <b>{pct:.1f}%</b> of total debit card spend."
        )
        if total_all > 0
        else f"Detected {format_currency(total_pay)} in payroll transactions."
    )

    tbl = pd.DataFrame(
        [
            {"Metric": "Total Payroll Spend", "Value": round(total_pay, 2)},
            {"Metric": "Unique Employers", "Value": n_employers},
            {"Metric": "Unique Accounts", "Value": n_accounts},
            {"Metric": "Payroll % of Total", "Value": round(pct, 1)},
        ]
    )
    section = {
        "heading": "Payroll Summary",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Payroll Summary", tbl)],
    }
    sheet = {
        "name": "S8 Payroll Summary",
        "df": tbl,
        "currency_cols": [],
        "pct_cols": [],
        "number_cols": [],
    }
    return section, sheet


def _top_employers(pay: pd.DataFrame):
    agg = (
        pay.groupby("payroll_employer")
        .agg(
            total=("amount", "sum"),
            employees=("primary_account_num", "nunique"),
            txns=("amount", "count"),
        )
        .sort_values("total", ascending=False)
        .head(20)
        .reset_index()
    )
    agg["avg"] = (agg["total"] / agg["employees"].replace(0, 1)).round(2)
    agg.columns = [
        "Employer",
        "Total Payroll",
        "Unique Employees",
        "Transactions",
        "Avg per Employee",
    ]

    fig = horizontal_bar(
        agg,
        x_col="Total Payroll",
        y_col="Employer",
        title="Top 20 Employers by Payroll Spend",
        top_n=20,
    )
    apply_theme(fig)

    top = agg.iloc[0] if not agg.empty else None
    narrative = (
        (
            f"The top employer is <b>{top['Employer']}</b> with "
            f"{format_currency(top['Total Payroll'])} across "
            f"<b>{int(top['Unique Employees']):,}</b> employees."
        )
        if top is not None
        else ""
    )

    section = {
        "heading": "Top Employers",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Top Employers", agg)],
    }
    sheet = {
        "name": "S8 Top Employers",
        "df": agg,
        "currency_cols": ["Total Payroll", "Avg per Employee"],
        "pct_cols": [],
        "number_cols": ["Unique Employees", "Transactions"],
    }
    return section, sheet


def _payroll_by_generation(pay: pd.DataFrame):
    agg = (
        pay.groupby("generation")
        .agg(total=("amount", "sum"), accts=("primary_account_num", "nunique"))
        .reindex(_GEN_ORDER)
        .dropna(how="all")
        .fillna(0)
        .reset_index()
    )
    agg.columns = ["Generation", "Total Payroll", "Unique Accounts"]
    colors = [GENERATION_COLORS.get(g, COLORS["neutral"]) for g in agg["Generation"]]

    fig = go.Figure(
        go.Bar(
            x=agg["Generation"],
            y=agg["Total Payroll"],
            marker_color=colors,
            text=agg["Total Payroll"].apply(format_currency),
            textposition="outside",
            textfont=dict(size=10),
            hovertemplate="%{x}: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=insight_title(
            "Payroll Volume by Generation", "Workforce demographics across credit union members"
        ),
        yaxis=dict(title=None, tickprefix="$", tickformat=","),
        showlegend=False,
        height=500,
    )
    apply_theme(fig)

    total = agg["Total Payroll"].sum()
    if total > 0:
        top = agg.loc[agg["Total Payroll"].idxmax()]
        narrative = (
            f"<b>{top['Generation']}</b> leads payroll volume at "
            f"{format_currency(top['Total Payroll'])} "
            f"({top['Total Payroll'] / total * 100:.1f}% of total), "
            f"with <b>{int(top['Unique Accounts']):,}</b> accounts."
        )
    else:
        narrative = "No payroll volume to break down by generation."

    section = {
        "heading": "Payroll by Generation",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Payroll by Generation", agg)],
    }
    sheet = {
        "name": "S8 Payroll by Gen",
        "df": agg,
        "currency_cols": ["Total Payroll"],
        "pct_cols": [],
        "number_cols": ["Unique Accounts"],
    }
    return section, sheet


def _monthly_trends(pay: pd.DataFrame):
    m = (
        pay.groupby("year_month")
        .agg(total=("amount", "sum"), accts=("primary_account_num", "nunique"))
        .reset_index()
    )
    m["year_month"] = m["year_month"].astype(str)
    m.columns = ["Month", "Total Payroll", "Accounts"]

    fig = line_trend(
        m,
        x_col="Month",
        y_cols=["Total Payroll"],
        title="Monthly Payroll Trends",
        colors=[COLORS["primary"]],
        y_format="$,.0f",
    )
    apply_theme(fig)

    if len(m) >= 2:
        f_val, l_val = m.iloc[0]["Total Payroll"], m.iloc[-1]["Total Payroll"]
        chg = ((l_val - f_val) / f_val * 100) if f_val > 0 else 0
        direction = "increased" if chg > 0 else "decreased"
        narrative = (
            f"Monthly payroll has <b>{direction} {abs(chg):.1f}%</b> from "
            f"{format_currency(f_val)} to {format_currency(l_val)} over "
            f"{len(m)} months."
        )
    else:
        narrative = "Insufficient months for trend analysis."

    section = {
        "heading": "Monthly Payroll Trends",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Monthly Payroll", m)],
    }
    sheet = {
        "name": "S8 Payroll Trends",
        "df": m,
        "currency_cols": ["Total Payroll"],
        "pct_cols": [],
        "number_cols": ["Accounts"],
    }
    return section, sheet


def _circular_economy(df: pd.DataFrame, pay: pd.DataFrame):
    """Recapture rate: debit spend / payroll received for payroll recipients."""
    pay_accts = pay["primary_account_num"].unique()
    pay_by_acct = pay.groupby("primary_account_num")["amount"].sum()
    non_pay = df[df["primary_account_num"].isin(pay_accts) & ~df.index.isin(pay.index)]
    deb_by_acct = non_pay.groupby("primary_account_num")["amount"].sum()

    combo = pd.DataFrame({"payroll_received": pay_by_acct, "debit_spend": deb_by_acct}).fillna(0)
    combo = combo[combo["payroll_received"] > 0]
    if combo.empty:
        return (None, None)

    combo["recapture_pct"] = (combo["debit_spend"] / combo["payroll_received"] * 100).clip(
        upper=500
    )
    avg_recap = combo["recapture_pct"].mean()

    has_gen = "generation" in df.columns
    if has_gen:
        acct_gen = (
            df.loc[df["primary_account_num"].isin(pay_accts)]
            .drop_duplicates("primary_account_num")[["primary_account_num", "generation"]]
            .set_index("primary_account_num")
        )
        combo = combo.join(acct_gen, how="left")
        gr = (
            combo.groupby("generation")["recapture_pct"]
            .mean()
            .reindex(_GEN_ORDER)
            .dropna()
            .reset_index()
        )
        gr.columns = ["Generation", "Avg Recapture %"]
        gr["Avg Recapture %"] = gr["Avg Recapture %"].round(1)
        colors = [GENERATION_COLORS.get(g, COLORS["neutral"]) for g in gr["Generation"]]
        fig = go.Figure(
            go.Bar(
                x=gr["Generation"],
                y=gr["Avg Recapture %"],
                marker_color=colors,
                text=gr["Avg Recapture %"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside",
                textfont=dict(size=10),
                hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
            )
        )
        fig.update_layout(
            title=insight_title(
                f"Avg Recapture Rate: {avg_recap:.1f}%",
                "Debit spend as % of payroll received, by generation",
            ),
            yaxis=dict(title=None, ticksuffix="%"),
            showlegend=False,
            height=500,
        )
        apply_theme(fig)
        tbl = gr
    else:
        tbl = pd.DataFrame([{"Metric": "Avg Recapture Rate", "Value": f"{avg_recap:.1f}%"}])
        fig = donut_chart(
            labels=["Recaptured via Debit", "Not Recaptured"],
            values=[min(avg_recap, 100), max(100 - avg_recap, 0)],
            title=f"Average Recapture Rate: {avg_recap:.1f}%",
            colors=[COLORS["positive"], COLORS["neutral"]],
        )
        apply_theme(fig)

    narrative = (
        f"Members who receive payroll spend an average of "
        f"<b>{avg_recap:.1f}%</b> of their deposited payroll back through "
        f"the credit union's debit card. A higher recapture rate indicates "
        f"stronger member engagement and primary financial institution (PFI) status."
    )
    pct_cols = ["Avg Recapture %"] if "Avg Recapture %" in tbl.columns else []
    section = {
        "heading": "Circular Economy: Debit Spend Recapture",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Recapture Rate", tbl)],
    }
    sheet = {
        "name": "S8 Circular Economy",
        "df": tbl,
        "currency_cols": [],
        "pct_cols": pct_cols,
        "number_cols": [],
    }
    return (section, sheet)


# =========================================================================
# NEW ANALYSIS 1: Clean Employer List & Business Name Extraction
# =========================================================================


def _clean_employer_list(pay: pd.DataFrame):
    """Extract clean business names from raw payroll employer strings.

    Groups payroll spend by clean employer name and produces a ranked
    table and horizontal bar chart of the top employers.
    """
    if pay.empty or "payroll_employer" not in pay.columns:
        return (None, None)

    # Build mapping: raw employer -> clean name
    raw_employers = pay["payroll_employer"].dropna().unique()
    employer_map: dict[str, str] = {}
    for raw in raw_employers:
        clean = _extract_business_name(raw)
        if clean and len(clean) >= 3:
            employer_map[raw] = clean

    if not employer_map:
        return (None, None)

    # Apply clean names to payroll_df
    pay_with_clean = pay.copy()
    pay_with_clean["clean_employer"] = pay_with_clean["payroll_employer"].map(employer_map)
    pay_with_clean = pay_with_clean.dropna(subset=["clean_employer"])

    if pay_with_clean.empty:
        return (None, None)

    # Aggregate by clean employer
    agg = (
        pay_with_clean.groupby("clean_employer")
        .agg(
            total=("amount", "sum"),
            employees=("primary_account_num", "nunique"),
            txns=("amount", "count"),
        )
        .sort_values("total", ascending=False)
        .head(30)
        .reset_index()
    )
    agg["avg_per_employee"] = (agg["total"] / agg["employees"].replace(0, 1)).round(2)
    agg.columns = [
        "Clean Employer",
        "Total Payroll",
        "Unique Employees",
        "Transactions",
        "Avg per Employee",
    ]

    # Horizontal bar chart -- top 20
    fig = horizontal_bar(
        agg,
        x_col="Total Payroll",
        y_col="Clean Employer",
        title="Top 20 Clean Employers by Payroll Spend",
        top_n=20,
    )
    apply_theme(fig)

    top = agg.iloc[0] if not agg.empty else None
    n_clean = len(agg)
    narrative = (
        (
            f"Business name extraction identified <b>{n_clean}</b> unique employers. "
            f"The largest is <b>{top['Clean Employer']}</b> with "
            f"{format_currency(top['Total Payroll'])} in payroll spend across "
            f"<b>{int(top['Unique Employees']):,}</b> employees."
        )
        if top is not None
        else "No clean employer names could be extracted."
    )

    # Mapping table for the Excel sheet
    mapping_rows = []
    for raw, clean in sorted(employer_map.items(), key=lambda kv: kv[1]):
        mapping_rows.append({"Raw Employer": raw, "Clean Employer": clean})
    mapping_df = pd.DataFrame(mapping_rows)

    section = {
        "heading": "Clean Employer List",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Top Clean Employers", agg), ("Employer Mapping", mapping_df)],
    }
    sheet = {
        "name": "S8 Clean Employers",
        "df": agg,
        "currency_cols": ["Total Payroll", "Avg per Employee"],
        "pct_cols": [],
        "number_cols": ["Unique Employees", "Transactions"],
    }
    return (section, sheet)


# =========================================================================
# NEW ANALYSIS 2: Circular Economy Detail by Employer
# =========================================================================


def _circular_economy_detail(
    pay: pd.DataFrame,
    personal_df: pd.DataFrame,
    config: dict,
):
    """Per-employer circular economy analysis.

    For each top-30 payroll employer, searches for the business in
    personal (consumer) transactions and calculates a per-business
    recapture rate.
    """
    if pay.empty or personal_df.empty:
        return (None, None)

    max_match: int = config.get("payroll", {}).get("max_match_count", 1_000)

    # Build employer spend ranking with clean names
    employer_spend = (
        pay.groupby("payroll_employer")
        .agg(total=("amount", "sum"))
        .sort_values("total", ascending=False)
        .head(30)
    )

    circular_records: list[dict] = []

    for raw_employer, row in employer_spend.iterrows():
        payroll_spend = row["total"]
        clean_name = _extract_business_name(str(raw_employer))
        if not clean_name or len(clean_name) < 3:
            continue

        words = clean_name.split()
        search_term = " ".join(words[:2]) if len(words) >= 2 else words[0]

        # Skip generic terms that cause false-positive matches
        if search_term.upper() in _GENERIC_SKIP_TERMS:
            continue
        if any(g in search_term.upper() for g in _GENERIC_SKIP_TERMS):
            continue

        merch_col = "merchant_consolidated"
        if merch_col not in personal_df.columns:
            merch_col = "merchant_name"
            if merch_col not in personal_df.columns:
                continue

        matches = personal_df[
            personal_df[merch_col].str.contains(
                search_term,
                case=False,
                na=False,
                regex=False,
            )
        ]

        if len(matches) == 0 or len(matches) >= max_match:
            continue

        consumer_spend = matches["amount"].sum()
        consumer_accounts = matches["primary_account_num"].nunique()
        consumer_merchants = matches[merch_col].nunique()
        recapture_pct = (consumer_spend / payroll_spend * 100) if payroll_spend > 0 else 0

        circular_records.append(
            {
                "Business Name": clean_name,
                "Payroll Spend": round(payroll_spend, 2),
                "Consumer Spend": round(consumer_spend, 2),
                "Recapture %": round(recapture_pct, 1),
                "Consumer Accounts": consumer_accounts,
                "Consumer Merchants": consumer_merchants,
            }
        )

    if not circular_records:
        return (None, None)

    detail_df = (
        pd.DataFrame(circular_records)
        .sort_values("Consumer Spend", ascending=False)
        .reset_index(drop=True)
    )

    # Horizontal bar chart -- top 15 by consumer spend, colored by recapture
    chart_df = detail_df.head(15).copy()
    # Reverse for bottom-to-top Plotly ordering
    chart_df = chart_df.sort_values("Consumer Spend", ascending=True)

    # Color scale: low recapture = accent, high recapture = positive
    max_recap = chart_df["Recapture %"].max() if not chart_df.empty else 1
    normed = chart_df["Recapture %"] / max(max_recap, 1)
    bar_colors = [_blend_color(COLORS["accent"], COLORS["positive"], v) for v in normed]

    fig = go.Figure(
        go.Bar(
            x=chart_df["Consumer Spend"],
            y=chart_df["Business Name"],
            orientation="h",
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=chart_df.apply(
                lambda r: f"{format_currency(r['Consumer Spend'])} ({r['Recapture %']:.1f}%)",
                axis=1,
            ),
            textposition="outside",
            textfont=dict(size=10),
            hovertemplate=(
                "%{y}<br>Consumer Spend: %{x:$,.0f}<br>Recapture: %{customdata:.1f}%<extra></extra>"
            ),
            customdata=chart_df["Recapture %"],
        )
    )

    row_height = max(22, 500 // max(len(chart_df), 1))
    chart_height = max(400, len(chart_df) * row_height + 120)

    fig.update_layout(
        title=insight_title(
            "Circular Economy by Employer",
            "Consumer spend at payroll employers (color intensity = recapture rate)",
        ),
        xaxis=dict(visible=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        margin=dict(l=200, r=120, t=80, b=40),
        height=chart_height,
        showlegend=False,
    )
    apply_theme(fig)

    total_payroll = detail_df["Payroll Spend"].sum()
    total_consumer = detail_df["Consumer Spend"].sum()
    overall_recap = (total_consumer / total_payroll * 100) if total_payroll > 0 else 0
    narrative = (
        f"Matched <b>{len(detail_df)}</b> payroll employers to consumer spending. "
        f"Total consumer spend at these businesses is "
        f"<b>{format_currency(total_consumer)}</b> against "
        f"{format_currency(total_payroll)} in payroll, yielding an overall "
        f"recapture rate of <b>{overall_recap:.1f}%</b>."
    )

    section = {
        "heading": "Circular Economy: Employer Detail",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Circular Economy Detail", detail_df)],
    }
    sheet = {
        "name": "S8 Circ Detail",
        "df": detail_df,
        "currency_cols": ["Payroll Spend", "Consumer Spend"],
        "pct_cols": ["Recapture %"],
        "number_cols": ["Consumer Accounts", "Consumer Merchants"],
    }
    return (section, sheet)


def _blend_color(hex_a: str, hex_b: str, t: float) -> str:
    """Linearly interpolate between two hex colors. t=0 -> hex_a, t=1 -> hex_b."""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = int(hex_a[1:3], 16), int(hex_a[3:5], 16), int(hex_a[5:7], 16)
    rb, gb, bb = int(hex_b[1:3], 16), int(hex_b[3:5], 16), int(hex_b[5:7], 16)
    r = int(ra + (rb - ra) * t)
    g = int(ga + (gb - ga) * t)
    b = int(ba + (bb - ba) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# =========================================================================
# NEW ANALYSIS 3: Payroll MoM Growth by Employer
# =========================================================================


def _payroll_mom_growth(pay: pd.DataFrame):
    """Month-over-month payroll growth analysis by employer.

    For top-20 employers by total payroll, computes first-3-month vs
    last-3-month averages, growth %, coefficient of variation, and a
    growth classification (Growing / Declining / Stable).
    """
    if pay.empty or "year_month" not in pay.columns:
        return (None, None)

    # Top 20 employers by total payroll spend
    top_employers = (
        pay.groupby("payroll_employer")["amount"].sum().sort_values(ascending=False).head(20).index
    )
    pay_top = pay[pay["payroll_employer"].isin(top_employers)].copy()

    if pay_top.empty:
        return (None, None)

    # Monthly totals per employer
    monthly = pay_top.groupby(["payroll_employer", "year_month"])["amount"].sum().reset_index()
    monthly = monthly.sort_values(["payroll_employer", "year_month"])

    growth_rows: list[dict] = []
    for employer, grp in monthly.groupby("payroll_employer"):
        grp = grp.sort_values("year_month")
        n_months = len(grp)
        if n_months < 2:
            continue

        values = grp["amount"].values
        total = values.sum()
        avg_monthly = values.mean()
        std_dev = values.std()
        cv = (std_dev / avg_monthly * 100) if avg_monthly > 0 else 0

        # First-3 and last-3 month averages
        first_window = min(3, n_months)
        last_window = min(3, n_months)
        first_3_avg = values[:first_window].mean()
        last_3_avg = values[-last_window:].mean()

        growth_pct = ((last_3_avg - first_3_avg) / first_3_avg * 100) if first_3_avg > 0 else 0

        if growth_pct > 20:
            classification = "Growing"
        elif growth_pct < -20:
            classification = "Declining"
        else:
            classification = "Stable"

        clean_name = _extract_business_name(str(employer))
        display_name = clean_name if clean_name else str(employer)[:40]

        growth_rows.append(
            {
                "Employer": display_name,
                "Months": n_months,
                "Total Payroll": round(total, 2),
                "Avg Monthly": round(avg_monthly, 2),
                "First 3M Avg": round(first_3_avg, 2),
                "Last 3M Avg": round(last_3_avg, 2),
                "Growth %": round(growth_pct, 1),
                "CV %": round(cv, 1),
                "Classification": classification,
            }
        )

    if not growth_rows:
        return (None, None)

    growth_df = (
        pd.DataFrame(growth_rows)
        .sort_values("Total Payroll", ascending=False)
        .reset_index(drop=True)
    )

    # Grouped bar chart: first-3 vs last-3 avg for top 15
    chart_df = growth_df.head(15).copy()
    fig = grouped_bar(
        chart_df,
        x_col="Employer",
        y_cols=["First 3M Avg", "Last 3M Avg"],
        title="Payroll Growth: First 3 Months vs Last 3 Months (Top 15)",
        colors=[COLORS["neutral"], COLORS["primary"]],
    )
    fig.update_layout(
        yaxis=dict(tickprefix="$", tickformat=","),
        height=550,
    )
    apply_theme(fig)

    n_growing = sum(1 for r in growth_rows if r["Classification"] == "Growing")
    n_declining = sum(1 for r in growth_rows if r["Classification"] == "Declining")
    n_stable = sum(1 for r in growth_rows if r["Classification"] == "Stable")
    narrative = (
        f"Among the top {len(growth_rows)} payroll employers, "
        f"<b>{n_growing}</b> are growing (>20%), "
        f"<b>{n_stable}</b> are stable, and "
        f"<b>{n_declining}</b> are declining (<-20%) "
        f"based on first-3-month vs last-3-month average comparison."
    )

    section = {
        "heading": "Payroll MoM Growth by Employer",
        "narrative": narrative,
        "figures": [fig],
        "tables": [("Employer Growth", growth_df)],
    }
    sheet = {
        "name": "S8 Payroll Growth",
        "df": growth_df,
        "currency_cols": ["Total Payroll", "Avg Monthly", "First 3M Avg", "Last 3M Avg"],
        "pct_cols": ["Growth %", "CV %"],
        "number_cols": ["Months"],
    }
    return (section, sheet)
