# v4_s7_campaigns.py
# Storyline 7: Campaign Effectiveness
# =============================================================================
# Response rates, spend lift, segmentation performance, balance tier response

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from txn_analysis.charts.builders import (
    donut_chart,
    grouped_bar,
    horizontal_bar,
    insight_title,
)
from txn_analysis.charts.theme import (
    CATEGORY_PALETTE,
    COLORS,
    GENERATION_COLORS,
    apply_theme,
    format_currency,
)

_MAIL_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Mail$")
_RESP_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Resp$")
_SEG_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Segmentation$")
_SPEND_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Spend$")
_SWIPE_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Swipes$")
_MIN_GROUP = 5

_MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
_INV_MONTH = {v: k for k, v in _MONTH_MAP.items()}


def _parse_month(label: str) -> tuple[int, int]:
    """Convert 'Apr25' -> (4, 2025)."""
    return _MONTH_MAP[label[:3]], 2000 + int(label[3:5])


def _month_sort_key(label: str) -> tuple[int, int]:
    m, y = _parse_month(label)
    return (y, m)


def _next_month(label: str) -> str:
    """Return the month label following *label* (e.g. 'Apr25' -> 'May25')."""
    m, y = _parse_month(label)
    m += 1
    if m > 12:
        m, y = 1, y + 1
    return f"{_INV_MONTH[m]}{y - 2000:02d}"


def _detect_spend_swipe_cols(odd: pd.DataFrame):
    """Return sorted month labels that have both Spend and Swipes columns."""
    spend_months = {c.replace(" Spend", "") for c in odd.columns if _SPEND_RE.match(c)}
    swipe_months = {c.replace(" Swipes", "") for c in odd.columns if _SWIPE_RE.match(c)}
    common = sorted(spend_months & swipe_months, key=_month_sort_key)
    return common


def _classify_responders(offer_accounts, resp_col, offer_val):
    """Split *offer_accounts* into (responders, non_responders) DataFrames.

    For NU offers, NU 1-4 counts as non-response.
    """
    if "NU" in str(offer_val):
        mask = offer_accounts[resp_col].notna() & ~offer_accounts[resp_col].astype(
            str
        ).str.contains(r"NU [1-4]", na=False, regex=True)
    else:
        mask = offer_accounts[resp_col].notna()
    return offer_accounts[mask], offer_accounts[~mask]


def _rate(num: int, den: int) -> float:
    """Percentage (0-100) with zero-division guard."""
    return round(num / den * 100, 1) if den else 0.0


def _has_campaign_data(odd: pd.DataFrame | None) -> bool:
    if odd is None or odd.empty:
        return False
    return "# of Offers" in odd.columns or any(_MAIL_RE.match(c) for c in odd.columns)


def _detect_cols(odd: pd.DataFrame):
    mail = sorted(c for c in odd.columns if _MAIL_RE.match(c))
    resp = sorted(c for c in odd.columns if _RESP_RE.match(c))
    seg = sorted(c for c in odd.columns if _SEG_RE.match(c))
    return mail, resp, seg


# -- Analysis 1: Campaign Overview -------------------------------------------


def _campaign_overview(odd):
    mailed = odd[odd["# of Offers"] > 0] if "# of Offers" in odd.columns else odd
    resp_mask = (
        odd["# of Responses"] > 0
        if "# of Responses" in odd.columns
        else pd.Series(False, index=odd.index)
    )
    mc, rc = len(mailed), int(resp_mask.sum())
    non_rc = mc - rc
    rate = _rate(rc, mc)

    df = pd.DataFrame(
        [
            {"Metric": "Total Accounts", "Value": len(odd)},
            {"Metric": "Accounts Mailed", "Value": mc},
            {"Metric": "Responders", "Value": rc},
            {"Metric": "Non-Responders", "Value": non_rc},
            {"Metric": "Response Rate (%)", "Value": rate},
        ]
    )
    fig = donut_chart(
        ["Responders", "Non-Responders"],
        [rc, max(non_rc, 0)],
        "Campaign Response Breakdown",
        colors=[COLORS["positive"], COLORS["neutral"]],
    )
    fig.update_layout(
        title=insight_title(
            f"{rate:.1f}% overall campaign response rate",
            f"{rc:,} responders out of {mc:,} mailed",
        )
    )
    narr = (
        f"Of <b>{mc:,}</b> accounts that received campaign offers, "
        f"<b>{rc:,}</b> responded (<b>{rate:.1f}%</b> response rate). "
        f"Non-responders total <b>{max(non_rc, 0):,}</b>."
    )
    return df, fig, narr


# -- Analysis 2: Response Rate by Generation ----------------------------------


def _response_by_generation(odd):
    need = {"generation", "# of Offers", "# of Responses"}
    if not need.issubset(odd.columns):
        return pd.DataFrame(), go.Figure(), ""

    offered = odd[odd["# of Offers"] > 0].copy()
    if offered.empty:
        return pd.DataFrame(), go.Figure(), ""

    gs = (
        offered.groupby("generation")
        .agg(
            mailed=("# of Offers", "count"),
            responders=("# of Responses", lambda s: (s > 0).sum()),
        )
        .reset_index()
    )
    gs = gs[gs["mailed"] >= _MIN_GROUP]
    gs["resp_rate"] = gs.apply(lambda r: _rate(r["responders"], r["mailed"]), axis=1)
    gs = gs.sort_values("resp_rate", ascending=False)
    gs.columns = ["Generation", "Mailed", "Responders", "Response Rate (%)"]

    colors = [GENERATION_COLORS.get(g, COLORS["neutral"]) for g in gs["Generation"]]
    fig = go.Figure(
        go.Bar(
            x=gs["Generation"],
            y=gs["Response Rate (%)"],
            marker_color=colors,
            text=[f"{v:.1f}%" for v in gs["Response Rate (%)"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=insight_title("Campaign response rate by generation"),
        yaxis=dict(title="Response Rate (%)", ticksuffix="%"),
        xaxis=dict(title=None),
        showlegend=False,
    )
    apply_theme(fig)

    top = gs.iloc[0]
    narr = (
        f"<b>{top['Generation']}</b> leads at <b>{top['Response Rate (%)']:.1f}%</b> "
        f"({int(top['Responders']):,} of {int(top['Mailed']):,} mailed)."
    )
    return gs, fig, narr


# -- Analysis 3: Spend Lift ---------------------------------------------------


def _spend_lift(odd):
    if "Total Spend" not in odd.columns or "# of Responses" not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""

    odd = odd.copy()
    odd["resp_flag"] = np.where(odd["# of Responses"] > 0, "Responder", "Non-Responder")

    base = (
        odd.groupby("resp_flag")
        .agg(
            accounts=("resp_flag", "count"),
            avg_spend=("Total Spend", "mean"),
        )
        .reset_index()
    )
    base["avg_spend"] = base["avg_spend"].round(2)
    base.columns = ["Group", "Accounts", "Avg Spend"]

    if "Response Grouping" in odd.columns:
        grp = (
            odd.groupby("Response Grouping")
            .agg(
                accounts=("Response Grouping", "count"),
                avg_spend=("Total Spend", "mean"),
            )
            .reset_index()
        )
        grp["avg_spend"] = grp["avg_spend"].round(2)
        grp.columns = ["Group", "Accounts", "Avg Spend"]
        combined = pd.concat([base, grp], ignore_index=True)
    else:
        combined = base.copy()

    fig = go.Figure(
        go.Bar(
            x=combined["Group"],
            y=combined["Avg Spend"],
            marker_color=CATEGORY_PALETTE[: len(combined)],
            text=[format_currency(v) for v in combined["Avg Spend"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=insight_title("Average spend: responders vs non-responders"),
        yaxis=dict(title="Avg Total Spend", tickprefix="$", tickformat=","),
        xaxis=dict(title=None),
        showlegend=False,
    )
    apply_theme(fig)

    r_row = base[base["Group"] == "Responder"]
    n_row = base[base["Group"] == "Non-Responder"]
    if not r_row.empty and not n_row.empty:
        rs, ns = r_row["Avg Spend"].iloc[0], n_row["Avg Spend"].iloc[0]
        lift = _rate(int(rs - ns), int(ns)) if ns else 0
        narr = (
            f"Responders average <b>{format_currency(rs)}</b> vs "
            f"<b>{format_currency(ns)}</b> for non-responders "
            f"(<b>{lift:.1f}%</b> lift)."
        )
    else:
        narr = "Insufficient data to compute spend lift."
    return combined, fig, narr


# -- Analysis 4: Monthly Mail & Response Tracking -----------------------------


def _monthly_tracking(odd):
    mail_cols, _, _ = _detect_cols(odd)
    if not mail_cols:
        return pd.DataFrame(), go.Figure(), ""

    rows = []
    for mc in mail_cols:
        label = mc.replace(" Mail", "")
        rc = f"{label} Resp"
        m = int((odd[mc] == 1).sum()) if mc in odd.columns else 0
        r = int((odd[rc] == 1).sum()) if rc in odd.columns else 0
        rows.append({"Month": label, "Mailed": m, "Responded": r, "Response Rate (%)": _rate(r, m)})

    tdf = pd.DataFrame(rows)
    if tdf.empty:
        return pd.DataFrame(), go.Figure(), ""

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=tdf["Month"],
            y=tdf["Mailed"],
            name="Mailed",
            marker_color=COLORS["primary"],
            opacity=0.7,
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=tdf["Month"],
            y=tdf["Response Rate (%)"],
            name="Response Rate %",
            mode="lines+markers",
            line=dict(color=COLORS["accent"], width=3),
            marker=dict(size=8),
            yaxis="y2",
        )
    )
    fig.update_layout(
        title=insight_title("Monthly campaign cadence & response rate"),
        yaxis=dict(title="Accounts Mailed", tickformat=","),
        yaxis2=dict(
            title="Response Rate (%)",
            overlaying="y",
            side="right",
            ticksuffix="%",
            range=[0, max(tdf["Response Rate (%)"].max() * 1.3, 10)],
        ),
        legend=dict(orientation="h", y=-0.15),
        hovermode="x unified",
    )
    apply_theme(fig)

    narr = (
        f"Campaign data spans <b>{len(tdf)}</b> months with an average "
        f"response rate of <b>{tdf['Response Rate (%)'].mean():.1f}%</b>."
    )
    return tdf, fig, narr


# -- Analysis 5: Campaign Segmentation Performance ----------------------------


def _segmentation_performance(odd):
    _, _, seg_cols = _detect_cols(odd)
    if not seg_cols:
        return pd.DataFrame(), go.Figure(), ""

    latest = seg_cols[-1]
    label = latest.replace(" Segmentation", "")
    rc = f"{label} Resp"

    sd = odd[[latest]].copy()
    sd["responded"] = (odd[rc] == 1).astype(int) if rc in odd.columns else 0
    sd["spend"] = odd["Total Spend"] if "Total Spend" in odd.columns else 0
    sd = sd.dropna(subset=[latest])
    sd = sd[sd[latest].astype(str).str.strip() != ""]
    if sd.empty:
        return pd.DataFrame(), go.Figure(), ""

    st = (
        sd.groupby(latest)
        .agg(
            accounts=(latest, "count"),
            responders=("responded", "sum"),
            avg_spend=("spend", "mean"),
        )
        .reset_index()
    )
    st = st[st["accounts"] >= _MIN_GROUP]
    st["resp_rate"] = st.apply(lambda r: _rate(int(r["responders"]), int(r["accounts"])), axis=1)
    st["avg_spend"] = st["avg_spend"].round(2)
    st = st.sort_values("resp_rate", ascending=True)
    st.columns = ["Segment", "Accounts", "Responders", "Avg Spend", "Response Rate (%)"]

    fig = horizontal_bar(
        st,
        x_col="Response Rate (%)",
        y_col="Segment",
        title=f"Response Rate by Segment ({label})",
        color=COLORS["secondary"],
        show_values=True,
        value_format="{:.1f}%",
        top_n=20,
    )
    fig.update_layout(
        title=insight_title(
            f"Segmentation performance for {label}",
            f"{len(st)} segments analyzed",
        )
    )

    narr = f"For <b>{label}</b>, <b>{len(st)}</b> segments identified. "
    if not st.empty:
        best = st.iloc[-1]
        narr += (
            f"Top segment: <b>{best['Segment']}</b> at "
            f"<b>{best['Response Rate (%)']:.1f}%</b> response rate."
        )
    return st, fig, narr


# -- Analysis 6: Response by Balance Tier -------------------------------------


def _response_by_balance_tier(odd):
    if "balance_tier" not in odd.columns or "# of Responses" not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""

    offered = odd[odd["# of Offers"] > 0].copy() if "# of Offers" in odd.columns else odd.copy()
    if offered.empty:
        return pd.DataFrame(), go.Figure(), ""

    offered["resp_flag"] = np.where(offered["# of Responses"] > 0, "Responder", "Non-Responder")
    ct = pd.crosstab(offered["balance_tier"], offered["resp_flag"])
    for col in ["Responder", "Non-Responder"]:
        if col not in ct.columns:
            ct[col] = 0
    ct = ct[["Responder", "Non-Responder"]]

    ct_pct = (ct.div(ct.sum(axis=1), axis=0) * 100).round(1).reset_index()

    summary = ct.copy()
    summary["Total"] = summary.sum(axis=1)
    summary["Response Rate (%)"] = (summary["Responder"] / summary["Total"] * 100).round(1)
    summary = summary.reset_index()
    summary.columns = ["Balance Tier", "Responders", "Non-Responders", "Total", "Response Rate (%)"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ct_pct["balance_tier"],
            y=ct_pct["Responder"],
            name="Responder",
            marker_color=COLORS["positive"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=ct_pct["balance_tier"],
            y=ct_pct["Non-Responder"],
            name="Non-Responder",
            marker_color=COLORS["neutral"],
        )
    )
    fig.update_layout(
        barmode="stack",
        title=insight_title("Response rate by balance tier"),
        yaxis=dict(title="% of Accounts", ticksuffix="%", range=[0, 100]),
        xaxis=dict(title=None),
    )
    apply_theme(fig)

    if not summary.empty:
        best = summary.loc[summary["Response Rate (%)"].idxmax()]
        narr = (
            f"<b>{best['Balance Tier']}</b> leads at "
            f"<b>{best['Response Rate (%)']:.1f}%</b> "
            f"({int(best['Responders']):,} responders)."
        )
    else:
        narr = ""
    return summary, fig, narr


# -- Analysis 7: Per-Offer Response Rates ------------------------------------


def _per_offer_response(odd):
    """Response rate breakdown by offer type across all campaign months."""
    mail_cols, _, _ = _detect_cols(odd)
    if not mail_cols:
        return pd.DataFrame(), go.Figure(), ""

    rows = []
    for mc in mail_cols:
        label = mc.replace(" Mail", "")
        rc = f"{label} Resp"
        if rc not in odd.columns:
            continue
        campaign_accts = odd[odd[mc].notna()].copy()
        for offer in sorted(campaign_accts[mc].dropna().unique()):
            offer_accts = campaign_accts[campaign_accts[mc] == offer]
            resp, _ = _classify_responders(offer_accts, rc, offer)
            rows.append(
                {
                    "Campaign": label,
                    "Offer": str(offer),
                    "Sent": len(offer_accts),
                    "Responded": len(resp),
                    "Response Rate (%)": _rate(len(resp), len(offer_accts)),
                }
            )

    if not rows:
        return pd.DataFrame(), go.Figure(), ""

    tdf = pd.DataFrame(rows)
    # Aggregate across campaigns: average rate per offer type
    agg = (
        tdf.groupby("Offer")
        .agg(
            total_sent=("Sent", "sum"),
            total_responded=("Responded", "sum"),
        )
        .reset_index()
    )
    agg["Response Rate (%)"] = agg.apply(
        lambda r: _rate(int(r["total_responded"]), int(r["total_sent"])), axis=1
    )
    agg = agg.sort_values("Response Rate (%)", ascending=False)
    agg.columns = ["Offer Type", "Total Sent", "Total Responded", "Response Rate (%)"]

    fig = apply_theme(
        horizontal_bar(
            agg,
            "Response Rate (%)",
            "Offer Type",
            "Response Rate by Offer Type",
            top_n=15,
            color=COLORS["primary"],
            value_format="{:.1f}%",
        )
    )
    fig.update_layout(
        title=insight_title(
            "Response rate varies significantly by offer type",
            f"{len(agg)} offer types across {len(mail_cols)} campaigns",
        )
    )

    if not agg.empty:
        best = agg.iloc[0]
        narr = (
            f"<b>{best['Offer Type']}</b> has the highest response rate at "
            f"<b>{best['Response Rate (%)']:.1f}%</b> "
            f"({int(best['Total Responded']):,} of {int(best['Total Sent']):,} sent). "
            f"Analysis covers {len(mail_cols)} campaign waves."
        )
    else:
        narr = ""
    return agg, fig, narr


# -- Analysis 8: Spend & Swipe Lift by Offer Type ---------------------------


def _offer_lift(odd):
    """Spend lift and swipe lift for responders vs non-responders per offer type."""
    mail_cols, _, _ = _detect_cols(odd)
    months = _detect_spend_swipe_cols(odd)
    if not mail_cols or not months:
        return pd.DataFrame(), go.Figure(), ""

    rows = []
    for mc in mail_cols:
        label = mc.replace(" Mail", "")
        rc = f"{label} Resp"
        measure = _next_month(label)
        spend_col = f"{measure} Spend"
        swipe_col = f"{measure} Swipes"
        if rc not in odd.columns or spend_col not in odd.columns:
            continue

        campaign_accts = odd[odd[mc].notna()].copy()
        for offer in sorted(campaign_accts[mc].dropna().unique()):
            offer_accts = campaign_accts[campaign_accts[mc] == offer]
            resp, non_resp = _classify_responders(offer_accts, rc, offer)
            if resp.empty or non_resp.empty:
                continue

            r_spend = resp[spend_col].mean()
            n_spend = non_resp[spend_col].mean()
            spend_lift = ((r_spend - n_spend) / n_spend * 100) if n_spend > 0 else 0

            r_swipes = resp[swipe_col].mean() if swipe_col in odd.columns else 0
            n_swipes = non_resp[swipe_col].mean() if swipe_col in odd.columns else 0
            swipe_lift = ((r_swipes - n_swipes) / n_swipes * 100) if n_swipes > 0 else 0

            rows.append(
                {
                    "Campaign": label,
                    "Offer": str(offer),
                    "Resp Avg Spend": round(r_spend, 2),
                    "Non-Resp Avg Spend": round(n_spend, 2),
                    "Spend Lift (%)": round(spend_lift, 1),
                    "Resp Avg Swipes": round(r_swipes, 1),
                    "Non-Resp Avg Swipes": round(n_swipes, 1),
                    "Swipe Lift (%)": round(swipe_lift, 1),
                }
            )

    if not rows:
        return pd.DataFrame(), go.Figure(), ""

    tdf = pd.DataFrame(rows)
    # Aggregate: weighted-average lifts per offer type
    agg = (
        tdf.groupby("Offer")
        .agg(
            spend_lift=("Spend Lift (%)", "mean"),
            swipe_lift=("Swipe Lift (%)", "mean"),
        )
        .reset_index()
        .round(1)
    )
    agg.columns = ["Offer Type", "Avg Spend Lift (%)", "Avg Swipe Lift (%)"]
    agg = agg.sort_values("Avg Spend Lift (%)", ascending=False)

    fig = apply_theme(
        grouped_bar(
            agg,
            "Offer Type",
            ["Avg Spend Lift (%)", "Avg Swipe Lift (%)"],
            "Spend & Swipe Lift by Offer Type",
            colors=[COLORS["positive"], COLORS["accent"]],
        )
    )
    fig.update_layout(
        title=insight_title(
            "Responder lift by offer type",
            "Measurement month spend and swipe increases",
        ),
        yaxis=dict(title="Lift (%)", ticksuffix="%"),
    )

    narr = f"Across {len(mail_cols)} campaigns, <b>{len(agg)}</b> offer types analyzed. "
    pos = agg[agg["Avg Spend Lift (%)"] > 0]
    if not pos.empty:
        best = pos.iloc[0]
        narr += (
            f"<b>{best['Offer Type']}</b> delivers the highest spend lift at "
            f"<b>{best['Avg Spend Lift (%)']:+.1f}%</b>."
        )
    return tdf, fig, narr


# -- Analysis 9: Before/After Campaign Trends -------------------------------


def _before_after_trends(odd):
    """3-month before + 3-month after spending trends with campaign marker."""
    mail_cols, _, _ = _detect_cols(odd)
    months = _detect_spend_swipe_cols(odd)
    if not mail_cols or len(months) < 4:
        return pd.DataFrame(), go.Figure(), ""

    # Use the latest campaign month
    latest_mail = mail_cols[-1]
    label = latest_mail.replace(" Mail", "")
    rc = f"{label} Resp"
    if rc not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""

    campaign_accts = odd[odd[latest_mail].notna()].copy()
    resp_mask = campaign_accts[rc].notna()
    if "NU" in str(campaign_accts[latest_mail].iloc[0] if not campaign_accts.empty else ""):
        resp_mask = resp_mask & ~campaign_accts[rc].astype(str).str.contains(
            r"NU [1-4]", na=False, regex=True
        )
    responders = campaign_accts[resp_mask]
    non_responders = campaign_accts[~resp_mask]

    # Window: 3 before + campaign + 3 after
    try:
        camp_idx = months.index(label)
    except ValueError:
        return pd.DataFrame(), go.Figure(), ""

    start = max(0, camp_idx - 3)
    end = min(len(months), camp_idx + 4)
    window = months[start:end]

    rows = []
    for m in window:
        sc = f"{m} Spend"
        if sc not in odd.columns:
            continue
        r_avg = responders[sc].mean() if not responders.empty else 0
        n_avg = non_responders[sc].mean() if not non_responders.empty else 0
        rows.append(
            {
                "Month": m,
                "Responder Avg Spend": round(r_avg, 2),
                "Non-Resp Avg Spend": round(n_avg, 2),
            }
        )

    if not rows:
        return pd.DataFrame(), go.Figure(), ""

    tdf = pd.DataFrame(rows)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=tdf["Month"],
            y=tdf["Responder Avg Spend"],
            name=f"Responders (n={len(responders):,})",
            marker_color=COLORS["primary"],
            opacity=0.85,
        )
    )
    fig.add_trace(
        go.Bar(
            x=tdf["Month"],
            y=tdf["Non-Resp Avg Spend"],
            name=f"Non-Responders (n={len(non_responders):,})",
            marker_color=COLORS["neutral"],
            opacity=0.65,
        )
    )
    # Vertical campaign marker
    camp_pos = window.index(label) if label in window else None
    if camp_pos is not None:
        fig.add_vline(
            x=camp_pos,
            line_dash="dash",
            line_color=COLORS["negative"],
            annotation_text="Campaign Month",
            annotation_position="top",
        )
    fig.update_layout(
        barmode="group",
        title=insight_title(
            f"{label} campaign: before & after spending",
            f"Responders vs non-responders across {len(window)} months",
        ),
        yaxis=dict(title="Avg Spend ($)", tickprefix="$", tickformat=","),
        xaxis=dict(title=None),
        legend=dict(orientation="h", y=-0.15),
    )
    apply_theme(fig)

    # Compute lift in measurement month
    measure = _next_month(label)
    m_row = tdf[tdf["Month"] == measure]
    if not m_row.empty:
        rs = m_row["Responder Avg Spend"].iloc[0]
        ns = m_row["Non-Resp Avg Spend"].iloc[0]
        lift = ((rs - ns) / ns * 100) if ns > 0 else 0
        narr = (
            f"In the measurement month (<b>{measure}</b>), responders averaged "
            f"<b>{format_currency(rs)}</b> vs <b>{format_currency(ns)}</b> "
            f"for non-responders (<b>{lift:+.1f}%</b> lift)."
        )
    else:
        narr = f"Before/after analysis for <b>{label}</b> campaign across {len(window)} months."
    return tdf, fig, narr


# -- Analysis 10: Transaction Size Distribution (Responders vs Non) ----------


def _txn_size_buckets(odd):
    """Transaction size bucket comparison between responders and non-responders."""
    mail_cols, _, _ = _detect_cols(odd)
    months = _detect_spend_swipe_cols(odd)
    if not mail_cols or not months:
        return pd.DataFrame(), go.Figure(), ""

    latest_mail = mail_cols[-1]
    label = latest_mail.replace(" Mail", "")
    rc = f"{label} Resp"
    measure = _next_month(label)
    spend_col = f"{measure} Spend"
    swipe_col = f"{measure} Swipes"

    if rc not in odd.columns or spend_col not in odd.columns or swipe_col not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""

    campaign_accts = odd[odd[latest_mail].notna()].copy()
    resp, non_resp = _classify_responders(
        campaign_accts, rc, campaign_accts[latest_mail].iloc[0] if not campaign_accts.empty else ""
    )

    # Avg transaction size = spend / swipes
    def _avg_txn(grp):
        s = grp[spend_col].fillna(0)
        w = grp[swipe_col].fillna(0).replace(0, np.nan)
        return (s / w).dropna()

    resp_sizes = _avg_txn(resp)
    non_resp_sizes = _avg_txn(non_resp)

    if resp_sizes.empty and non_resp_sizes.empty:
        return pd.DataFrame(), go.Figure(), ""

    bins = [0, 5, 10, 25, 50, 100, 500, float("inf")]
    labels = ["< $5", "$5-10", "$10-25", "$25-50", "$50-100", "$100-500", "$500+"]

    r_cut = pd.cut(resp_sizes, bins=bins, labels=labels)
    n_cut = pd.cut(non_resp_sizes, bins=bins, labels=labels)

    r_pct = (r_cut.value_counts(normalize=True) * 100).reindex(labels, fill_value=0).round(1)
    n_pct = (n_cut.value_counts(normalize=True) * 100).reindex(labels, fill_value=0).round(1)

    tdf = pd.DataFrame(
        {
            "Amount Range": labels,
            "Responders (%)": r_pct.values,
            "Non-Responders (%)": n_pct.values,
        }
    )
    tdf["Difference (pp)"] = (tdf["Responders (%)"] - tdf["Non-Responders (%)"]).round(1)

    fig = apply_theme(
        grouped_bar(
            tdf,
            "Amount Range",
            ["Responders (%)", "Non-Responders (%)"],
            f"Transaction Size Distribution ({measure})",
            colors=[COLORS["primary"], COLORS["neutral"]],
        )
    )
    fig.update_layout(
        title=insight_title(
            f"Transaction size patterns in {measure}",
            "Avg txn size = spend / swipes per account",
        ),
        yaxis=dict(title="% of Accounts", ticksuffix="%"),
    )

    biggest_diff = tdf.loc[tdf["Difference (pp)"].abs().idxmax()]
    narr = (
        f"In <b>{measure}</b>, the largest difference is in the "
        f"<b>{biggest_diff['Amount Range']}</b> bucket "
        f"({biggest_diff['Difference (pp)']:+.1f} pp)."
    )
    return tdf, fig, narr


# -- Analysis 11: Avg Txn Size & Swipe Counts by Offer Type -----------------


def _offer_txn_detail(odd):
    """Average transaction size and swipe counts per offer type."""
    mail_cols, _, _ = _detect_cols(odd)
    months = _detect_spend_swipe_cols(odd)
    if not mail_cols or not months:
        return pd.DataFrame(), go.Figure(), ""

    rows = []
    for mc in mail_cols:
        label = mc.replace(" Mail", "")
        rc = f"{label} Resp"
        measure = _next_month(label)
        spend_col = f"{measure} Spend"
        swipe_col = f"{measure} Swipes"
        if rc not in odd.columns or spend_col not in odd.columns or swipe_col not in odd.columns:
            continue

        campaign_accts = odd[odd[mc].notna()].copy()
        for offer in sorted(campaign_accts[mc].dropna().unique()):
            offer_accts = campaign_accts[campaign_accts[mc] == offer]
            resp, non_resp = _classify_responders(offer_accts, rc, offer)
            if resp.empty or non_resp.empty:
                continue

            r_total_spend = resp[spend_col].sum()
            r_total_swipes = resp[swipe_col].sum()
            r_avg_txn = r_total_spend / r_total_swipes if r_total_swipes > 0 else 0

            n_total_spend = non_resp[spend_col].sum()
            n_total_swipes = non_resp[swipe_col].sum()
            n_avg_txn = n_total_spend / n_total_swipes if n_total_swipes > 0 else 0

            rows.append(
                {
                    "Campaign": label,
                    "Offer": str(offer),
                    "Resp Avg Txn Size": round(r_avg_txn, 2),
                    "Non-Resp Avg Txn Size": round(n_avg_txn, 2),
                    "Resp Avg Swipes": round(resp[swipe_col].mean(), 1),
                    "Non-Resp Avg Swipes": round(non_resp[swipe_col].mean(), 1),
                }
            )

    if not rows:
        return pd.DataFrame(), go.Figure(), ""

    tdf = pd.DataFrame(rows)
    agg = (
        tdf.groupby("Offer")
        .agg(
            resp_txn=("Resp Avg Txn Size", "mean"),
            non_resp_txn=("Non-Resp Avg Txn Size", "mean"),
            resp_swipes=("Resp Avg Swipes", "mean"),
            non_resp_swipes=("Non-Resp Avg Swipes", "mean"),
        )
        .reset_index()
        .round(1)
    )
    agg.columns = [
        "Offer Type",
        "Resp Avg Txn ($)",
        "Non-Resp Avg Txn ($)",
        "Resp Avg Swipes",
        "Non-Resp Avg Swipes",
    ]
    agg = agg.sort_values("Resp Avg Swipes", ascending=False)

    fig = apply_theme(
        grouped_bar(
            agg,
            "Offer Type",
            ["Resp Avg Swipes", "Non-Resp Avg Swipes"],
            "Average Swipes by Offer Type",
            colors=[COLORS["primary"], COLORS["neutral"]],
        )
    )
    fig.update_layout(
        title=insight_title(
            "Swipe behavior by offer type",
            "Responders consistently swipe more often",
        )
    )

    narr = (
        f"Across <b>{len(mail_cols)}</b> campaigns, responders average "
        f"<b>{agg['Resp Avg Swipes'].mean():.1f}</b> swipes vs "
        f"<b>{agg['Non-Resp Avg Swipes'].mean():.1f}</b> for non-responders."
    )
    return agg, fig, narr


# -- Analysis 12: Business vs Personal Campaign Performance ------------------


def _biz_personal_campaigns(odd):
    """Response rates split by Business vs Personal accounts."""
    if "Business?" not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""
    if "# of Offers" not in odd.columns or "# of Responses" not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""

    offered = odd[odd["# of Offers"] > 0].copy()
    if offered.empty:
        return pd.DataFrame(), go.Figure(), ""

    grp = (
        offered.groupby("Business?")
        .agg(
            mailed=("# of Offers", "count"),
            responders=("# of Responses", lambda s: (s > 0).sum()),
            avg_spend=("Total Spend", "mean")
            if "Total Spend" in offered.columns
            else ("# of Offers", "count"),
        )
        .reset_index()
    )
    grp = grp[grp["mailed"] >= _MIN_GROUP]
    grp["resp_rate"] = grp.apply(lambda r: _rate(int(r["responders"]), int(r["mailed"])), axis=1)
    grp["avg_spend"] = grp["avg_spend"].round(2) if "Total Spend" in offered.columns else 0
    grp.columns = ["Account Type", "Mailed", "Responders", "Avg Spend", "Response Rate (%)"]
    grp["Account Type"] = (
        grp["Account Type"].map({"Yes": "Business", "No": "Personal"}).fillna(grp["Account Type"])
    )

    fig = apply_theme(
        grouped_bar(
            grp,
            "Account Type",
            ["Response Rate (%)", "Mailed"],
            "Campaign Performance: Business vs Personal",
            colors=[COLORS["primary"], COLORS["neutral"]],
        )
    )
    fig.update_layout(
        title=insight_title(
            "Business vs personal campaign response",
            f"{len(grp)} account types compared",
        )
    )

    narr = ""
    if len(grp) >= 2:
        best = grp.loc[grp["Response Rate (%)"].idxmax()]
        narr = (
            f"<b>{best['Account Type']}</b> accounts respond at "
            f"<b>{best['Response Rate (%)']:.1f}%</b> "
            f"({int(best['Responders']):,} of {int(best['Mailed']):,})."
        )
    return grp, fig, narr


# -- Analysis 13: Response by Age Bucket & Tenure ---------------------------


def _response_by_age_tenure(odd):
    """Response rates by age buckets and tenure buckets."""
    if "# of Offers" not in odd.columns or "# of Responses" not in odd.columns:
        return pd.DataFrame(), go.Figure(), ""

    offered = odd[odd["# of Offers"] > 0].copy()
    if offered.empty:
        return pd.DataFrame(), go.Figure(), ""

    rows = []
    # Age buckets (if available)
    if "Account Holder Age" in offered.columns:
        ages = offered["Account Holder Age"].dropna()
        if not ages.empty:
            bins = [0, 25, 35, 45, 55, 65, 200]
            labels = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]
            offered["age_bucket"] = pd.cut(ages, bins=bins, labels=labels, right=True)
            for bucket in labels:
                grp = offered[offered["age_bucket"] == bucket]
                if len(grp) < _MIN_GROUP:
                    continue
                resp_count = int((grp["# of Responses"] > 0).sum())
                rows.append(
                    {
                        "Dimension": "Age",
                        "Bucket": bucket,
                        "Mailed": len(grp),
                        "Responders": resp_count,
                        "Response Rate (%)": _rate(resp_count, len(grp)),
                    }
                )

    # Tenure buckets (if available)
    if "tenure_years" in offered.columns:
        tenure = offered["tenure_years"].dropna()
        if not tenure.empty:
            bins = [0, 1, 3, 5, 10, 100]
            labels = ["< 1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
            offered["tenure_bucket"] = pd.cut(tenure, bins=bins, labels=labels, right=True)
            for bucket in labels:
                grp = offered[offered["tenure_bucket"] == bucket]
                if len(grp) < _MIN_GROUP:
                    continue
                resp_count = int((grp["# of Responses"] > 0).sum())
                rows.append(
                    {
                        "Dimension": "Tenure",
                        "Bucket": bucket,
                        "Mailed": len(grp),
                        "Responders": resp_count,
                        "Response Rate (%)": _rate(resp_count, len(grp)),
                    }
                )

    if not rows:
        return pd.DataFrame(), go.Figure(), ""

    tdf = pd.DataFrame(rows)

    # Chart: show the dimension with more data
    age_rows = tdf[tdf["Dimension"] == "Age"]
    tenure_rows = tdf[tdf["Dimension"] == "Tenure"]

    chart_df = age_rows if len(age_rows) >= len(tenure_rows) else tenure_rows
    if chart_df.empty:
        chart_df = tdf

    fig = apply_theme(
        horizontal_bar(
            chart_df,
            "Response Rate (%)",
            "Bucket",
            f"Response Rate by {chart_df.iloc[0]['Dimension']}",
            color=COLORS["accent"],
            value_format="{:.1f}%",
            top_n=15,
        )
    )
    fig.update_layout(
        title=insight_title(
            f"Campaign response by {chart_df.iloc[0]['Dimension'].lower()} bucket",
            f"{len(chart_df)} buckets analyzed",
        )
    )

    best = tdf.loc[tdf["Response Rate (%)"].idxmax()]
    narr = (
        f"<b>{best['Bucket']}</b> ({best['Dimension']}) has the highest response rate at "
        f"<b>{best['Response Rate (%)']:.1f}%</b> "
        f"({int(best['Responders']):,} of {int(best['Mailed']):,})."
    )
    return tdf, fig, narr


# =============================================================================
# Main Runner
# =============================================================================


def _add(sections, sheets, heading, df, fig, narr, sheet_name, **col_spec):
    """Append a section+sheet pair only when data is present."""
    if df.empty:
        return
    sections.append(
        {
            "heading": heading,
            "narrative": narr,
            "figures": [fig],
            "tables": [(heading, df)],
        }
    )
    sheets.append({"name": sheet_name, "df": df, **col_spec})


def run(ctx: dict) -> dict:
    """Run Campaign Effectiveness analyses and return storyline payload."""
    odd = ctx.get("odd_df")

    if not _has_campaign_data(odd):
        return {
            "title": "S7: Campaign Effectiveness",
            "description": "No campaign data available in the ODD file.",
            "sections": [
                {
                    "heading": "Campaign Effectiveness",
                    "narrative": (
                        "No campaign data available. The ODD file does not contain "
                        "campaign-related columns (# of Offers, MmmYY Mail)."
                    ),
                    "figures": [],
                    "tables": [],
                }
            ],
            "sheets": [],
        }

    sections, sheets = [], []

    # 1 - Campaign Overview (always appended when campaign data exists)
    ov_df, ov_fig, ov_narr = _campaign_overview(odd)
    sections.append(
        {
            "heading": "Campaign Overview",
            "narrative": ov_narr,
            "figures": [ov_fig],
            "tables": [("Campaign Overview", ov_df)],
        }
    )
    sheets.append(
        {
            "name": "S7 Campaign Overview",
            "df": ov_df,
            "currency_cols": [],
            "pct_cols": [],
            "number_cols": ["Value"],
        }
    )

    # 2 - Response by Generation
    _add(
        sections,
        sheets,
        "Response Rate by Generation",
        *_response_by_generation(odd),
        "S7 Response by Gen",
        currency_cols=[],
        pct_cols=["Response Rate (%)"],
        number_cols=["Mailed", "Responders"],
    )

    # 3 - Spend Lift
    _add(
        sections,
        sheets,
        "Spend Lift: Responders vs Non-Responders",
        *_spend_lift(odd),
        "S7 Spend Lift",
        currency_cols=["Avg Spend"],
        pct_cols=[],
        number_cols=["Accounts"],
    )

    # 4 - Monthly Tracking
    _add(
        sections,
        sheets,
        "Monthly Mail & Response Tracking",
        *_monthly_tracking(odd),
        "S7 Monthly Tracking",
        currency_cols=[],
        pct_cols=["Response Rate (%)"],
        number_cols=["Mailed", "Responded"],
    )

    # 5 - Segmentation
    _add(
        sections,
        sheets,
        "Campaign Segmentation Performance",
        *_segmentation_performance(odd),
        "S7 Segmentation",
        currency_cols=["Avg Spend"],
        pct_cols=["Response Rate (%)"],
        number_cols=["Accounts", "Responders"],
    )

    # 6 - Balance Tier
    _add(
        sections,
        sheets,
        "Response by Balance Tier",
        *_response_by_balance_tier(odd),
        "S7 Balance Tier Resp",
        currency_cols=[],
        pct_cols=["Response Rate (%)"],
        number_cols=["Responders", "Non-Responders", "Total"],
    )

    # 7 - Per-Offer Response Rates
    _add(
        sections,
        sheets,
        "Response Rate by Offer Type",
        *_per_offer_response(odd),
        "S7 Per-Offer Rates",
        currency_cols=[],
        pct_cols=["Response Rate (%)"],
        number_cols=["Total Sent", "Total Responded"],
    )

    # 8 - Spend & Swipe Lift by Offer Type
    _add(
        sections,
        sheets,
        "Spend & Swipe Lift by Offer Type",
        *_offer_lift(odd),
        "S7 Offer Lift",
        currency_cols=["Resp Avg Spend", "Non-Resp Avg Spend"],
        pct_cols=["Spend Lift (%)", "Swipe Lift (%)"],
        number_cols=[],
    )

    # 9 - Before/After Campaign Trends
    _add(
        sections,
        sheets,
        "Before/After Campaign Spending Trends",
        *_before_after_trends(odd),
        "S7 Before After",
        currency_cols=["Responder Avg Spend", "Non-Resp Avg Spend"],
        pct_cols=[],
        number_cols=[],
    )

    # 10 - Transaction Size Distribution
    _add(
        sections,
        sheets,
        "Transaction Size Distribution",
        *_txn_size_buckets(odd),
        "S7 Txn Buckets",
        currency_cols=[],
        pct_cols=["Responders (%)", "Non-Responders (%)"],
        number_cols=["Difference (pp)"],
    )

    # 11 - Avg Transaction Size & Swipes by Offer Type
    _add(
        sections,
        sheets,
        "Transaction Detail by Offer Type",
        *_offer_txn_detail(odd),
        "S7 Offer Txn Detail",
        currency_cols=["Resp Avg Txn ($)", "Non-Resp Avg Txn ($)"],
        pct_cols=[],
        number_cols=["Resp Avg Swipes", "Non-Resp Avg Swipes"],
    )

    # 12 - Business vs Personal Campaign Performance
    _add(
        sections,
        sheets,
        "Business vs Personal Campaign Response",
        *_biz_personal_campaigns(odd),
        "S7 Biz vs Personal",
        currency_cols=["Avg Spend"],
        pct_cols=["Response Rate (%)"],
        number_cols=["Mailed", "Responders"],
    )

    # 13 - Response by Age & Tenure
    _add(
        sections,
        sheets,
        "Response Rate by Age & Tenure",
        *_response_by_age_tenure(odd),
        "S7 Age Tenure Resp",
        currency_cols=[],
        pct_cols=["Response Rate (%)"],
        number_cols=["Mailed", "Responders"],
    )

    return {
        "title": "S7: Campaign Effectiveness",
        "description": (
            "Campaign response rates, per-offer analysis, spend/swipe lift, "
            "before/after trends, transaction size patterns, balance-tier response"
        ),
        "sections": sections,
        "sheets": sheets,
    }
