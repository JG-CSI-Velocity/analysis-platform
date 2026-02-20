"""Market Impact Analysis -- A15.

Slide IDs: A15.1, A15.2, A15.3, A15.4.
Ported from mailer_impact.py (609 lines).
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.mailer._helpers import (
    MAILED_SEGMENTS,
    RESPONSE_SEGMENTS,
    _safe,
    build_mailed_mask,
    build_responder_mask,
    discover_metric_cols,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.pipeline.context import PipelineContext

# Chart colors
COLOR_OUTER = "#3498DB"  # blue - eligible w/ card
COLOR_INNER = "#E74C3C"  # red - responders
COLOR_RESP = "#2ECC71"  # green - responder bar
COLOR_NON = "#95A5A6"  # gray - non-responder bar


# ---------------------------------------------------------------------------
# A15.1 -- Market Reach Bubble
# ---------------------------------------------------------------------------


def _market_reach(ctx: PipelineContext) -> list[AnalysisResult]:
    """Nested proportional circles: eligible w/ card vs unique responders."""
    logger.info("A15.1 Market Reach")
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A15.1",
                title="Market Reach",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data
    eligible_debit = ctx.subsets.eligible_with_debit
    if eligible_debit is None or eligible_debit.empty:
        return [
            AnalysisResult(
                slide_id="A15.1",
                title="Market Reach",
                success=False,
                error="No eligible-with-debit subset",
            )
        ]

    n_eligible = len(eligible_debit)
    resp_mask = build_responder_mask(data, pairs)
    mailed_mask = build_mailed_mask(data, pairs)
    n_responders = int(resp_mask.sum())
    n_mailed = int(mailed_mask.sum())

    if n_eligible == 0:
        return [
            AnalysisResult(
                slide_id="A15.1",
                title="Market Reach",
                success=False,
                error="No eligible accounts",
            )
        ]

    resp_rate = n_responders / n_mailed * 100 if n_mailed > 0 else 0
    penetration = n_responders / n_eligible * 100

    save_to = ctx.paths.charts_dir / "a15_1_market_reach.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 8), save_path=save_to) as (fig, ax):
        # Radii proportional to sqrt(count) so area is proportional
        max_radius = 2.5
        r_outer = max_radius
        r_inner = max_radius * np.sqrt(n_responders / n_eligible)
        cx, cy = 0.35, 0.0  # shifted left for KPI space

        outer = plt.Circle(
            (cx, cy),
            r_outer,
            facecolor=COLOR_OUTER,
            alpha=0.25,
            edgecolor=COLOR_OUTER,
            linewidth=2.5,
        )
        ax.add_patch(outer)
        inner = plt.Circle(
            (cx, cy),
            r_inner,
            facecolor=COLOR_INNER,
            alpha=0.35,
            edgecolor=COLOR_INNER,
            linewidth=2.5,
        )
        ax.add_patch(inner)

        # Labels inside circles
        ax.text(
            cx,
            cy + r_outer * 0.65,
            "Eligible with a Card",
            ha="center",
            va="center",
            fontsize=16,
            fontweight="bold",
            color=COLOR_OUTER,
        )
        ax.text(
            cx,
            cy + r_outer * 0.45,
            f"{n_eligible:,}",
            ha="center",
            va="center",
            fontsize=22,
            fontweight="bold",
            color=COLOR_OUTER,
        )
        ax.text(
            cx,
            cy - 0.15,
            "Unique",
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="white",
        )
        ax.text(
            cx,
            cy - 0.50,
            "Responders",
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="white",
        )
        ax.text(
            cx,
            cy - 0.90,
            f"{n_responders:,}",
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
            color="white",
        )

        # KPI callouts
        kpi_x = 4.2
        kpis = [
            (f"{n_mailed:,}", "Total Mailed"),
            (f"{n_responders:,}", "Unique Responders"),
            (f"{resp_rate:.1f}%", "Response Rate"),
            (f"{penetration:.1f}%", "Market Penetration"),
        ]
        for i, (val, label) in enumerate(kpis):
            y = 1.8 - i * 1.3
            ax.text(
                kpi_x,
                y,
                val,
                ha="left",
                va="center",
                fontsize=24,
                fontweight="bold",
                color="#1E3D59",
            )
            ax.text(
                kpi_x,
                y - 0.4,
                label,
                ha="left",
                va="center",
                fontsize=14,
                color="#555",
            )

        ax.set_xlim(-3.0, 7.5)
        ax.set_ylim(-3.5, 3.5)
        ax.set_aspect("equal")
        ax.axis("off")

    ctx.results["market_reach"] = {
        "n_eligible": n_eligible,
        "n_responders": n_responders,
        "n_mailed": n_mailed,
        "penetration": penetration,
    }

    return [
        AnalysisResult(
            slide_id="A15.1",
            title="Market Reach",
            chart_path=save_to,
            notes=(
                f"Eligible: {n_eligible:,} | Responders: {n_responders:,} | "
                f"Penetration: {penetration:.1f}%"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# A15.2 -- Spend Share
# ---------------------------------------------------------------------------


def _spend_share(ctx: PipelineContext) -> list[AnalysisResult]:
    """Horizontal bars: total spend from all open, eligible, and responders."""
    logger.info("A15.2 Spend Share")
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A15.2",
                title="Spend Share",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data
    open_accounts = ctx.subsets.open_accounts
    eligible_data = ctx.subsets.eligible_data
    if open_accounts is None or eligible_data is None:
        return [
            AnalysisResult(
                slide_id="A15.2",
                title="Spend Share",
                success=False,
                error="Missing open/eligible subsets",
            )
        ]

    # Find latest spend column
    spend_cols, _ = discover_metric_cols(ctx)
    if not spend_cols:
        return [
            AnalysisResult(
                slide_id="A15.2",
                title="Spend Share",
                success=False,
                error="No spend columns found",
            )
        ]

    latest_spend_col = spend_cols[-1]
    latest_month = latest_spend_col.replace(" Spend", "")

    if latest_spend_col not in open_accounts.columns:
        return [
            AnalysisResult(
                slide_id="A15.2",
                title="Spend Share",
                success=False,
                error=f"{latest_spend_col} not in open accounts",
            )
        ]

    # Unique responders across all mail months
    resp_mask = build_responder_mask(data, pairs)
    responder_indices = data.index[resp_mask]
    open_resp = open_accounts[open_accounts.index.isin(responder_indices)]

    spend_all_open = open_accounts[latest_spend_col].fillna(0).sum()
    spend_eligible = eligible_data[latest_spend_col].fillna(0).sum()
    spend_responders = open_resp[latest_spend_col].fillna(0).sum()

    n_open = len(open_accounts)
    n_eligible = len(eligible_data)
    n_resp = len(open_resp)

    if spend_all_open == 0:
        return [
            AnalysisResult(
                slide_id="A15.2",
                title="Spend Share",
                success=False,
                error="Zero spend across open accounts",
            )
        ]

    elig_pct = spend_eligible / spend_all_open * 100
    resp_pct_elig = spend_responders / spend_eligible * 100 if spend_eligible > 0 else 0
    resp_pct_open = spend_responders / spend_all_open * 100

    save_to = ctx.paths.charts_dir / "a15_2_spend_share.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.remove()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        labels = ["All Open Accounts", "Eligible Accounts", "Responders"]
        values = [spend_all_open, spend_eligible, spend_responders]
        acct_counts = [n_open, n_eligible, n_resp]
        bar_colors = [COLOR_OUTER, "#1E3D59", COLOR_INNER]

        y_pos = [2, 1, 0]
        bars = ax1.barh(y_pos, values, color=bar_colors, height=0.6, alpha=0.85)

        max_val = max(values)
        for bar, val, count in zip(bars, values, acct_counts):
            bar_cy = bar.get_y() + bar.get_height() / 2
            ax1.text(
                val + max_val * 0.02,
                bar_cy,
                f"${val:,.0f}",
                ha="left",
                va="center",
                fontsize=15,
                fontweight="bold",
            )
            if bar.get_width() > max_val * 0.10:
                ax1.text(
                    bar.get_width() * 0.5,
                    bar_cy,
                    f"{count:,} accounts",
                    ha="center",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                    color="white",
                )

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(labels, fontsize=14, fontweight="bold")
        ax1.set_xlabel(f"Total Spend ({latest_month})", fontsize=14, fontweight="bold")
        ax1.set_xlim(0, max_val * 1.35)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))

        # KPI panel
        ax2.axis("off")
        ax2.set_xlim(0, 1)
        ax2.set_ylim(-0.5, 3)
        kpi_items = [
            ("Eligible Share of Open Spend", f"{elig_pct:.1f}%", "#1E3D59", 2.4),
            ("Responder Share of Eligible Spend", f"{resp_pct_elig:.1f}%", COLOR_INNER, 1.4),
            ("Responder Share of All Open Spend", f"{resp_pct_open:.1f}%", COLOR_INNER, 0.4),
        ]
        for label, val, color, y in kpi_items:
            ax2.text(
                0.1,
                y + 0.15,
                label,
                ha="left",
                va="center",
                fontsize=12,
                color="#555",
            )
            ax2.text(
                0.1,
                y - 0.15,
                val,
                ha="left",
                va="center",
                fontsize=26,
                fontweight="bold",
                color=color,
            )

        fig.tight_layout()

    ctx.results["spend_share"] = {
        "spend_open": spend_all_open,
        "spend_eligible": spend_eligible,
        "spend_responders": spend_responders,
    }

    return [
        AnalysisResult(
            slide_id="A15.2",
            title="Spend Composition",
            chart_path=save_to,
            notes=(
                f"Open: ${spend_all_open:,.0f} | Eligible: ${spend_eligible:,.0f} "
                f"({elig_pct:.1f}%) | Responders: ${spend_responders:,.0f} "
                f"({resp_pct_elig:.1f}% of eligible)"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# A15.3 -- Revenue Attribution
# ---------------------------------------------------------------------------


def _revenue_attribution(ctx: PipelineContext) -> list[AnalysisResult]:
    """Interchange revenue from responders vs non-responders."""
    logger.info("A15.3 Revenue Attribution")
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A15.3",
                title="Revenue Attribution",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data
    ic_rate = ctx.client.ic_rate
    if ic_rate <= 0:
        return [
            AnalysisResult(
                slide_id="A15.3",
                title="Revenue Attribution",
                success=False,
                error="No IC rate configured",
            )
        ]

    # Find latest month with spend data
    cols = list(data.columns)
    latest_resp_col = None
    latest_mail_col = None
    latest_spend_col = None

    for month, resp_col, mail_col in reversed(pairs):
        sc = f"{month} Spend"
        if sc in cols:
            latest_resp_col = resp_col
            latest_mail_col = mail_col
            latest_spend_col = sc
            break

    if not latest_spend_col:
        return [
            AnalysisResult(
                slide_id="A15.3",
                title="Revenue Attribution",
                success=False,
                error="No spend data",
            )
        ]

    mailed = data[data[latest_mail_col].isin(MAILED_SEGMENTS)].copy()
    if mailed.empty:
        return [
            AnalysisResult(
                slide_id="A15.3",
                title="Revenue Attribution",
                success=False,
                error="No mailed accounts",
            )
        ]

    resp_mask = mailed[latest_resp_col].isin(RESPONSE_SEGMENTS)
    n_resp = int(resp_mask.sum())
    n_non = int((~resp_mask).sum())

    if n_resp == 0 or n_non == 0:
        return [
            AnalysisResult(
                slide_id="A15.3",
                title="Revenue Attribution",
                success=False,
                error="Need both responders and non-responders",
            )
        ]

    resp_spend = mailed.loc[resp_mask, latest_spend_col].fillna(0).sum()
    non_spend = mailed.loc[~resp_mask, latest_spend_col].fillna(0).sum()
    resp_ic = resp_spend * ic_rate
    non_ic = non_spend * ic_rate
    resp_ic_per = resp_ic / n_resp
    non_ic_per = non_ic / n_non
    incremental_per = resp_ic_per - non_ic_per
    incremental_total = incremental_per * n_resp

    save_to = ctx.paths.charts_dir / "a15_3_revenue_attribution.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.remove()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        # Left: IC revenue per account
        values = [resp_ic_per, non_ic_per]
        colors = [COLOR_RESP, COLOR_NON]

        bars = ax1.barh([1, 0], values, color=colors, height=0.5, alpha=0.9)
        for bar, val in zip(bars, values):
            bar_cy = bar.get_y() + bar.get_height() / 2
            ax1.text(
                val + max(values) * 0.03,
                bar_cy,
                f"${val:,.2f}",
                ha="left",
                va="center",
                fontsize=16,
                fontweight="bold",
            )
        ax1.set_yticks([0, 1])
        ax1.set_yticklabels(
            ["Non-Responders", "Responders"],
            fontsize=14,
            fontweight="bold",
        )
        ax1.set_xlabel("IC Revenue per Account", fontsize=14, fontweight="bold")
        ax1.set_xlim(0, max(values) * 1.4)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.2f}"))
        ax1.set_title("Per Account", fontsize=16, fontweight="bold")

        # Right: KPI text block
        ax2.axis("off")
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)

        lift_sign = "+" if incremental_per >= 0 else ""
        total_sign = "+" if incremental_total >= 0 else ""
        kpi_data = [
            ("Responder IC Revenue", f"${resp_ic:,.0f}", 0.85),
            ("Non-Responder IC Revenue", f"${non_ic:,.0f}", 0.65),
            ("Lift per Account", f"{lift_sign}${incremental_per:,.2f}", 0.45),
            ("Incremental Program Revenue", f"{total_sign}${incremental_total:,.0f}", 0.22),
        ]
        for label, val, y in kpi_data:
            ax2.text(
                0.1,
                y + 0.05,
                label,
                ha="left",
                va="center",
                fontsize=13,
                color="#555",
            )
            color = "#1E3D59" if "Incremental" not in label else COLOR_RESP
            ax2.text(
                0.1,
                y - 0.05,
                val,
                ha="left",
                va="center",
                fontsize=20,
                fontweight="bold",
                color=color,
            )

        rect = mpatches.FancyBboxPatch(
            (0.03, 0.10),
            0.94,
            0.22,
            boxstyle="round,pad=0.02",
            facecolor=COLOR_RESP,
            alpha=0.08,
            edgecolor=COLOR_RESP,
            linewidth=2,
        )
        ax2.add_patch(rect)
        fig.tight_layout()

    ctx.results["revenue_attribution"] = {
        "resp_ic": resp_ic,
        "non_ic": non_ic,
        "incremental_total": incremental_total,
    }

    return [
        AnalysisResult(
            slide_id="A15.3",
            title="Revenue Attribution",
            chart_path=save_to,
            notes=(
                f"Resp IC: ${resp_ic:,.0f} | Non-resp IC: ${non_ic:,.0f} | "
                f"Incremental: {total_sign}${incremental_total:,.0f}"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# A15.4 -- Pre/Post Spend Delta
# ---------------------------------------------------------------------------


def _pre_post_delta(ctx: PipelineContext) -> list[AnalysisResult]:
    """Compare avg spend before vs after mailer for responders and non-responders."""
    logger.info("A15.4 Pre/Post Spend Delta")
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A15.4",
                title="Pre/Post Spend Delta",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data
    spend_cols, _ = discover_metric_cols(ctx)

    if len(spend_cols) < 4:
        return [
            AnalysisResult(
                slide_id="A15.4",
                title="Pre/Post Spend Delta",
                success=False,
                error="Need 4+ spend months for pre/post analysis",
            )
        ]

    first_mail_month = pairs[0][0]
    first_resp_col = pairs[0][1]
    first_mail_col = pairs[0][2]
    mail_date = parse_month(first_mail_month)

    pre_cols = [c for c in spend_cols if parse_month(c) < mail_date]
    post_cols = [c for c in spend_cols if parse_month(c) >= mail_date]

    if len(pre_cols) < 2 or len(post_cols) < 2:
        return [
            AnalysisResult(
                slide_id="A15.4",
                title="Pre/Post Spend Delta",
                success=False,
                error="Need 2+ months before and after mailer",
            )
        ]

    pre_cols = pre_cols[-3:]
    post_cols = post_cols[:3]

    mailed = data[data[first_mail_col].isin(MAILED_SEGMENTS)].copy()
    if mailed.empty:
        return [
            AnalysisResult(
                slide_id="A15.4",
                title="Pre/Post Spend Delta",
                success=False,
                error="No mailed accounts",
            )
        ]

    resp_mask = mailed[first_resp_col].isin(RESPONSE_SEGMENTS)
    n_resp = int(resp_mask.sum())
    n_non = int((~resp_mask).sum())

    if n_resp == 0 or n_non == 0:
        return [
            AnalysisResult(
                slide_id="A15.4",
                title="Pre/Post Spend Delta",
                success=False,
                error="Need both responders and non-responders",
            )
        ]

    resp_pre = mailed.loc[resp_mask, pre_cols].fillna(0).mean(axis=1).mean()
    resp_post = mailed.loc[resp_mask, post_cols].fillna(0).mean(axis=1).mean()
    non_pre = mailed.loc[~resp_mask, pre_cols].fillna(0).mean(axis=1).mean()
    non_post = mailed.loc[~resp_mask, post_cols].fillna(0).mean(axis=1).mean()

    resp_delta = resp_post - resp_pre
    non_delta = non_post - non_pre
    resp_pct = resp_delta / resp_pre * 100 if resp_pre > 0 else 0
    non_pct = non_delta / non_pre * 100 if non_pre > 0 else 0

    save_to = ctx.paths.charts_dir / "a15_4_pre_post_delta.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        x = np.arange(2)
        bar_w = 0.32
        pre_vals = [resp_pre, non_pre]
        post_vals = [resp_post, non_post]

        bars_pre = ax.bar(
            x - bar_w / 2,
            pre_vals,
            bar_w,
            color="#BDC3C7",
            edgecolor="none",
            label="Before Mailer",
        )
        bars_post = ax.bar(
            x + bar_w / 2,
            post_vals,
            bar_w,
            color=[COLOR_RESP, COLOR_NON],
            edgecolor="none",
            label="After Mailer",
        )

        all_vals = pre_vals + post_vals
        for bar in list(bars_pre) + list(bars_post):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + max(all_vals) * 0.02,
                f"${h:,.0f}",
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold",
            )

        deltas = [(resp_delta, resp_pct, 0), (non_delta, non_pct, 1)]
        for delta, pct, i in deltas:
            sign = "+" if delta >= 0 else ""
            color = COLOR_RESP if delta > 0 else "#E74C3C"
            ax.text(
                i,
                max(all_vals) * 1.15,
                f"{sign}${delta:,.0f}/acct ({sign}{pct:.0f}%)",
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color=color,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(
            ["Responders", "Non-Responders"],
            fontsize=18,
            fontweight="bold",
        )
        ax.set_ylabel("Avg Monthly Spend per Account", fontsize=14, fontweight="bold")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.set_ylim(0, max(all_vals) * 1.30)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=14, loc="upper right")

    ctx.results["pre_post_delta"] = {
        "resp_pre": resp_pre,
        "resp_post": resp_post,
        "resp_delta": resp_delta,
        "non_pre": non_pre,
        "non_post": non_post,
        "non_delta": non_delta,
    }

    sign = "+" if resp_delta > 0 else ""
    return [
        AnalysisResult(
            slide_id="A15.4",
            title="Before vs After Mailer",
            chart_path=save_to,
            notes=(
                f"Resp: ${resp_pre:,.0f} -> ${resp_post:,.0f} ({resp_pct:+.0f}%) | "
                f"Non: ${non_pre:,.0f} -> ${non_post:,.0f} ({non_pct:+.0f}%)"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class MailerImpact(AnalysisModule):
    """Market Impact -- reach, spend share, revenue attribution, pre/post."""

    module_id = "mailer.impact"
    display_name = "Market Impact Analysis"
    section = "mailer"
    required_columns = ()  # Dynamic -- depends on mailer columns

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Mailer Impact for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._market_reach, "A15.1", ctx)
        results += _safe(self._spend_share, "A15.2", ctx)
        results += _safe(self._revenue_attribution, "A15.3", ctx)
        results += _safe(self._pre_post_delta, "A15.4", ctx)
        return results

    @staticmethod
    def _market_reach(ctx: PipelineContext) -> list[AnalysisResult]:
        return _market_reach(ctx)

    @staticmethod
    def _spend_share(ctx: PipelineContext) -> list[AnalysisResult]:
        return _spend_share(ctx)

    @staticmethod
    def _revenue_attribution(ctx: PipelineContext) -> list[AnalysisResult]:
        return _revenue_attribution(ctx)

    @staticmethod
    def _pre_post_delta(ctx: PipelineContext) -> list[AnalysisResult]:
        return _pre_post_delta(ctx)
