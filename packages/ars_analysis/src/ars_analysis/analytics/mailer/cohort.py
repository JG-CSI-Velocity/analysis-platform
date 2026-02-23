"""Responder Cohort Trajectory Analysis -- A16 series.

Proves that ARS mailer responders reverse downward interchange trends.
Slide IDs: A16.1-A16.6 (5-6 slides depending on data depth).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.mailer._helpers import (
    RESPONSE_SEGMENTS,
    SEGMENT_COLORS,
    build_responder_mask,
    discover_metric_cols,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE, SILVER
from ars_analysis.pipeline.context import PipelineContext

NON_RESP_COLOR = "#404040"


# ---------------------------------------------------------------------------
# Cohort construction helpers
# ---------------------------------------------------------------------------


def _find_first_response_month(
    row: pd.Series,
    pairs: list[tuple[str, str, str]],
) -> str | None:
    """Return the first month string where this account responded, or None."""
    for month, resp_col, _mail_col in pairs:
        val = row.get(resp_col)
        if pd.notna(val) and val in RESPONSE_SEGMENTS:
            return month
    return None


def _find_first_response_segment(
    row: pd.Series,
    pairs: list[tuple[str, str, str]],
) -> str | None:
    """Return the response segment from the first response month, or None."""
    for _month, resp_col, _mail_col in pairs:
        val = row.get(resp_col)
        if pd.notna(val) and val in RESPONSE_SEGMENTS:
            return val
    return None


def _month_offset(metric_ts: pd.Timestamp, anchor_ts: pd.Timestamp) -> int:
    """Compute month offset between two timestamps."""
    return (metric_ts.year - anchor_ts.year) * 12 + (metric_ts.month - anchor_ts.month)


def build_cohort_trajectory(
    ctx: PipelineContext,
    metric_type: str,
    by_segment: bool = False,
) -> pd.DataFrame:
    """Build offset-aligned trajectory DataFrame.

    Returns DataFrame with columns: offset, group, avg_value, n_accounts.
    """
    pairs = discover_pairs(ctx)
    spend_cols, swipe_cols = discover_metric_cols(ctx)
    metric_cols = spend_cols if metric_type == "Spend" else swipe_cols

    if not pairs or not metric_cols:
        return pd.DataFrame(columns=["offset", "group", "avg_value", "n_accounts"])

    # Map metric columns to timestamps
    metric_ts_map = {col: parse_month(col) for col in metric_cols}
    metric_ts_map = {k: v for k, v in metric_ts_map.items() if pd.notna(v)}

    if not metric_ts_map:
        return pd.DataFrame(columns=["offset", "group", "avg_value", "n_accounts"])

    data = ctx.data
    resp_mask = build_responder_mask(data, pairs)

    # Find anchor month per account
    earliest_mail_ts = parse_month(pairs[0][0])
    anchors = data.apply(lambda row: _find_first_response_month(row, pairs), axis=1)
    anchor_timestamps = anchors.map(lambda m: parse_month(m) if m else earliest_mail_ts)

    # Segment labels
    if by_segment:
        segments = data.apply(lambda row: _find_first_response_segment(row, pairs), axis=1)
        groups = segments.where(resp_mask, "Non-Responders")
    else:
        groups = pd.Series("Responders", index=data.index)
        groups = groups.where(resp_mask, "Non-Responders")

    # Build long-form records
    records = []
    for col, ts in metric_ts_map.items():
        for idx in data.index:
            offset = _month_offset(ts, anchor_timestamps[idx])
            val = data.at[idx, col]
            if pd.notna(val):
                records.append(
                    {
                        "offset": offset,
                        "group": groups[idx],
                        "value": float(val),
                    }
                )

    if not records:
        return pd.DataFrame(columns=["offset", "group", "avg_value", "n_accounts"])

    long_df = pd.DataFrame(records)
    result = (
        long_df.groupby(["group", "offset"])
        .agg(avg_value=("value", "mean"), n_accounts=("value", "count"))
        .reset_index()
    )
    return result.sort_values(["group", "offset"])


def _compute_slopes(traj_df: pd.DataFrame, group: str) -> tuple[float, float]:
    """Compute pre-M0 and post-M0 average monthly slope for a group."""
    grp = traj_df[traj_df["group"] == group].sort_values("offset")
    pre = grp[grp["offset"] < 0]
    post = grp[grp["offset"] > 0]

    pre_slope = 0.0
    if len(pre) >= 2:
        vals = pre["avg_value"].values
        pre_slope = float(np.mean(np.diff(vals)))

    post_slope = 0.0
    if len(post) >= 2:
        vals = post["avg_value"].values
        post_slope = float(np.mean(np.diff(vals)))

    return pre_slope, post_slope


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_trajectory(
    ax,
    traj_df: pd.DataFrame,
    metric_type: str,
    by_segment: bool = False,
) -> str:
    """Draw offset-aligned trajectory lines. Returns insight text."""
    import matplotlib.ticker as mticker

    groups_in_data = traj_df["group"].unique()

    for group in sorted(groups_in_data):
        grp = traj_df[traj_df["group"] == group].sort_values("offset")
        if group == "Non-Responders":
            color = NON_RESP_COLOR
            ls = "--"
            lw = 2
            ms = 6
        elif group == "Responders":
            color = POSITIVE
            ls = "-"
            lw = 2.5
            ms = 8
        else:
            color = SEGMENT_COLORS.get(group, POSITIVE)
            ls = "-"
            lw = 2.5
            ms = 8

        ax.plot(
            grp["offset"],
            grp["avg_value"],
            marker="o",
            color=color,
            linestyle=ls,
            linewidth=lw,
            markersize=ms,
            label=group,
        )

        # Endpoint label
        if len(grp) > 0:
            last = grp.iloc[-1]
            if metric_type == "Spend":
                lbl = f"${last['avg_value']:,.0f}"
            else:
                lbl = f"{last['avg_value']:,.0f}"
            ax.annotate(
                lbl,
                xy=(last["offset"], last["avg_value"]),
                xytext=(8, 6),
                textcoords="offset points",
                fontsize=12,
                fontweight="bold",
                color=color,
            )

    # Vertical line at M0
    ax.axvline(0, color="#888888", linestyle=":", linewidth=1.5, alpha=0.7)
    ax.text(
        0.02,
        0.97,
        "Response\nMonth",
        transform=ax.transAxes,
        fontsize=11,
        color="#888888",
        va="top",
    )

    title_scope = "Per-Segment" if by_segment else "Responder vs Non-Responder"
    ax.set_title(
        f"{title_scope} {metric_type} Trajectory",
        fontsize=20,
        fontweight="bold",
    )
    ax.set_xlabel("Months Relative to First Response", fontsize=14)
    ylabel = f"Avg {metric_type} per Account"
    if metric_type == "Spend":
        ylabel = f"Avg {metric_type} per Account ($)"
    ax.set_ylabel(ylabel, fontsize=14)

    if metric_type == "Spend":
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))

    ax.legend(fontsize=14, loc="upper left", frameon=True, fancybox=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    # Compute insight
    resp_label = "Responders" if not by_segment else "NU 5+"
    resp_grp = traj_df[traj_df["group"] == resp_label]
    non_grp = traj_df[traj_df["group"] == "Non-Responders"]

    if not resp_grp.empty and not non_grp.empty:
        r_post = resp_grp[resp_grp["offset"] > 0]["avg_value"]
        r_pre = resp_grp[resp_grp["offset"] < 0]["avg_value"]
        n_post = non_grp[non_grp["offset"] > 0]["avg_value"]
        n_pre = non_grp[non_grp["offset"] < 0]["avg_value"]

        r_delta = r_post.mean() - r_pre.mean() if len(r_post) > 0 and len(r_pre) > 0 else 0
        n_delta = n_post.mean() - n_pre.mean() if len(n_post) > 0 and len(n_pre) > 0 else 0

        if metric_type == "Spend":
            return (
                f"Responders: {'+' if r_delta >= 0 else ''}${r_delta:,.0f}/mo | "
                f"Non-Resp: {'+' if n_delta >= 0 else ''}${n_delta:,.0f}/mo"
            )
        return (
            f"Responders: {'+' if r_delta >= 0 else ''}{r_delta:,.0f}/mo | "
            f"Non-Resp: {'+' if n_delta >= 0 else ''}{n_delta:,.0f}/mo"
        )
    return ""


def _draw_direction_bars(
    ax,
    traj_df: pd.DataFrame,
    metric_type: str,
) -> str:
    """Draw grouped bar chart of before/after slopes. Returns insight."""
    groups_to_check = ["Responders", "Non-Responders"]
    # Add segments if present
    for seg in RESPONSE_SEGMENTS:
        if seg in traj_df["group"].values:
            groups_to_check.append(seg)

    labels = []
    before_slopes = []
    after_slopes = []

    for group in groups_to_check:
        if group not in traj_df["group"].values:
            continue
        pre_s, post_s = _compute_slopes(traj_df, group)
        short = group.replace("Non-Responders", "Non-Resp")
        labels.append(short)
        before_slopes.append(pre_s)
        after_slopes.append(post_s)

    if not labels:
        return "No data for direction chart"

    x = np.arange(len(labels))
    width = 0.35

    after_colors = [POSITIVE if s > 0 else NEGATIVE for s in after_slopes]

    ax.bar(x - width / 2, before_slopes, width, label="Before Response", color=SILVER)
    for xi, (val, color) in enumerate(zip(after_slopes, after_colors)):
        ax.bar(xi + width / 2, val, width, color=color, label="After Response" if xi == 0 else None)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=14)
    ax.set_ylabel(f"Avg Monthly {metric_type} Change", fontsize=14)
    ax.set_title(
        f"{metric_type} Direction: Before vs After Response",
        fontsize=20,
        fontweight="bold",
    )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(fontsize=14, loc="upper right", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    # Data labels on bars
    for xi, (bv, av) in enumerate(zip(before_slopes, after_slopes)):
        fmt = "${:+,.0f}" if metric_type == "Spend" else "{:+,.0f}"
        ax.text(
            xi - width / 2,
            bv,
            fmt.format(bv),
            ha="center",
            va="bottom" if bv >= 0 else "top",
            fontsize=12,
            fontweight="bold",
            color="#555",
        )
        ax.text(
            xi + width / 2,
            av,
            fmt.format(av),
            ha="center",
            va="bottom" if av >= 0 else "top",
            fontsize=12,
            fontweight="bold",
            color=POSITIVE if av > 0 else NEGATIVE,
        )

    # Insight
    if "Responders" in labels:
        ri = labels.index("Responders")
        pre_v, post_v = before_slopes[ri], after_slopes[ri]
        if metric_type == "Spend":
            return f"Responders reversed from ${pre_v:+,.0f}/mo to ${post_v:+,.0f}/mo"
        return f"Responders reversed from {pre_v:+,.0f}/mo to {post_v:+,.0f}/mo"
    return ""


def _draw_cohort_size(
    ax,
    traj_df: pd.DataFrame,
) -> str:
    """Draw stacked bar of cohort size at each offset. Returns insight."""
    resp = traj_df[traj_df["group"] != "Non-Responders"]
    non_resp = traj_df[traj_df["group"] == "Non-Responders"]

    resp_agg = resp.groupby("offset")["n_accounts"].sum().sort_index()
    non_agg = non_resp.groupby("offset")["n_accounts"].sum().sort_index()

    offsets = sorted(set(resp_agg.index) | set(non_agg.index))
    r_vals = [resp_agg.get(o, 0) for o in offsets]
    n_vals = [non_agg.get(o, 0) for o in offsets]

    ax.bar(offsets, r_vals, label="Responders", color=POSITIVE, alpha=0.8)
    ax.bar(offsets, n_vals, bottom=r_vals, label="Non-Responders", color=SILVER, alpha=0.8)

    ax.axvline(0, color="#888888", linestyle=":", linewidth=1.5, alpha=0.7)
    ax.set_title("Cohort Size by Month Offset", fontsize=20, fontweight="bold")
    ax.set_xlabel("Months Relative to First Response", fontsize=14)
    ax.set_ylabel("Account Observations", fontsize=14)
    ax.legend(fontsize=14, loc="upper right", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    total_resp = sum(r_vals)
    total_non = sum(n_vals)
    return f"Responders: {total_resp:,} obs | Non-Resp: {total_non:,} obs"


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class ResponderCohort(AnalysisModule):
    """Responder Cohort Trajectory Analysis -- A16 series."""

    module_id = "mailer.cohort"
    display_name = "Responder Cohort Trajectories"
    section = "mailer"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Cohort trajectories for {client}", client=ctx.client.client_id)
        pairs = discover_pairs(ctx)
        spend_cols, swipe_cols = discover_metric_cols(ctx)

        if not pairs:
            return [
                AnalysisResult(
                    slide_id="A16",
                    title="Cohort Trajectories",
                    success=False,
                    error="No mail/response pairs found",
                )
            ]
        if not spend_cols and not swipe_cols:
            return [
                AnalysisResult(
                    slide_id="A16",
                    title="Cohort Trajectories",
                    success=False,
                    error="No Spend or Swipes columns found",
                )
            ]

        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # A16.1 -- Responder vs Non-Resp Spend Trajectory
        if spend_cols:
            traj = build_cohort_trajectory(ctx, "Spend", by_segment=False)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_1_spend_trajectory.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Spend")
                results.append(
                    AnalysisResult(
                        slide_id="A16.1",
                        title="Responder Spend Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )
                ctx.results["a16_spend_traj"] = traj

        # A16.2 -- Responder vs Non-Resp Swipe Trajectory
        if swipe_cols:
            traj = build_cohort_trajectory(ctx, "Swipes", by_segment=False)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_2_swipe_trajectory.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Swipes")
                results.append(
                    AnalysisResult(
                        slide_id="A16.2",
                        title="Responder Swipe Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.3 -- Per-Segment Spend Trajectory
        if spend_cols:
            traj = build_cohort_trajectory(ctx, "Spend", by_segment=True)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_3_segment_spend.png"
                with chart_figure(figsize=(16, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Spend", by_segment=True)
                results.append(
                    AnalysisResult(
                        slide_id="A16.3",
                        title="Per-Segment Spend Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.4 -- Per-Segment Swipe Trajectory
        if swipe_cols:
            traj = build_cohort_trajectory(ctx, "Swipes", by_segment=True)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_4_segment_swipes.png"
                with chart_figure(figsize=(16, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Swipes", by_segment=True)
                results.append(
                    AnalysisResult(
                        slide_id="A16.4",
                        title="Per-Segment Swipe Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.5 -- Direction Change Proof
        if spend_cols:
            traj_resp = build_cohort_trajectory(ctx, "Spend", by_segment=False)
            if not traj_resp.empty:
                save_to = ctx.paths.charts_dir / "a16_5_direction_change.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_direction_bars(ax, traj_resp, "Spend")
                results.append(
                    AnalysisResult(
                        slide_id="A16.5",
                        title="Spend Direction Change",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.6 -- Cohort Size (optional, only if 8+ metric months)
        metric_count = max(len(spend_cols), len(swipe_cols))
        if metric_count >= 8:
            traj = build_cohort_trajectory(ctx, "Spend", by_segment=False)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_6_cohort_size.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_cohort_size(ax, traj)
                results.append(
                    AnalysisResult(
                        slide_id="A16.6",
                        title="Cohort Size & Retention",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        if not results:
            return [
                AnalysisResult(
                    slide_id="A16",
                    title="Cohort Trajectories",
                    success=False,
                    error="Insufficient data for trajectory analysis",
                )
            ]

        return results
