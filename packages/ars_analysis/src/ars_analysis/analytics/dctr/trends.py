"""DCTR Trends -- segment, decade, L12M, seasonality, vintage analyses.

Slide IDs: A7.4, A7.5, A7.6a, A7.6b, A7.14, A7.15.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import (
    dctr,
    filter_l12m,
    l12m_month_labels,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import BUSINESS, HISTORICAL, PERSONAL, TEAL, TTM
from ars_analysis.pipeline.context import PipelineContext


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(slide_id=label, title=label, success=False, error=str(exc))]


@register
class DCTRTrends(AnalysisModule):
    """DCTR trend analyses -- temporal patterns and cohort tracking."""

    module_id = "dctr.trends"
    display_name = "DCTR Trends"
    section = "dctr"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("DCTR Trends for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._segment_trends, "A7.4", ctx)
        results += _safe(self._decade_trend, "A7.5", ctx)
        results += _safe(self._l12m_trend, "A7.6a", ctx)
        results += _safe(self._decade_pb, "A7.6b", ctx)
        results += _safe(self._seasonality, "A7.14", ctx)
        results += _safe(self._vintage, "A7.15", ctx)
        return results

    # -- A7.4: Segment Trends (P/B x Historical/L12M) -------------------------

    def _segment_trends(self, ctx: PipelineContext) -> list[AnalysisResult]:
        r = ctx.results
        p_ins = r.get("dctr_4", {}).get("insights", {})
        b_ins = r.get("dctr_5", {}).get("insights", {})
        p6_ins = r.get("dctr_6", {}).get("insights", {})
        b7_ins = r.get("dctr_7", {}).get("insights", {})

        p_hist = p_ins.get("overall_dctr", 0) * 100
        p_l12m = p6_ins.get("dctr", 0) * 100
        p_trend = p_l12m - p_hist
        has_biz = b_ins.get("total_accounts", 0) > 0
        b_hist = b_ins.get("overall_dctr", 0) * 100
        b_l12m = b7_ins.get("dctr", 0) * 100
        b_trend = b_l12m - b_hist

        rows = [
            {
                "Segment": "Personal",
                "Historical DCTR %": p_hist,
                "L12M DCTR %": p_l12m,
                "Change pp": p_trend,
            }
        ]
        if has_biz:
            rows.append(
                {
                    "Segment": "Business",
                    "Historical DCTR %": b_hist,
                    "L12M DCTR %": b_l12m,
                    "Change pp": b_trend,
                }
            )
        df = pd.DataFrame(rows)

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_segment_trends.png"
            try:
                if has_biz:
                    cats = [
                        "Personal\nHistorical",
                        "Personal\nTTM",
                        "Business\nHistorical",
                        "Business\nTTM",
                    ]
                    vals = [p_hist, p_l12m, b_hist, b_l12m]
                    colors = [PERSONAL, HISTORICAL, BUSINESS, TTM]
                else:
                    cats = ["Personal\nHistorical", "Personal\nTTM"]
                    vals = [p_hist, p_l12m]
                    colors = [PERSONAL, HISTORICAL]

                with chart_figure(save_path=save_to) as (fig, ax):
                    x_pos = np.arange(len(cats))
                    ax.bar(
                        x_pos,
                        vals,
                        color=colors,
                        edgecolor="black",
                        linewidth=2,
                        alpha=0.9,
                        width=0.6,
                    )
                    for i, v in enumerate(vals):
                        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontweight="bold", fontsize=22)
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title(
                        "DCTR Segment Trends: Historical vs TTM",
                        fontsize=24,
                        fontweight="bold",
                        pad=20,
                    )
                    ax.set_xticks(x_pos)
                    ax.set_xticklabels(cats, fontsize=20)
                    ax.tick_params(axis="y", labelsize=20)
                    ax.set_ylim(0, max(vals) * 1.2 if vals else 100)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.set_axisbelow(True)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.4 chart failed: {err}", err=exc)

        ctx.results["dctr_segment_trends"] = {
            "personal_trend": p_trend,
            "business_trend": b_trend,
            "has_business": has_biz,
        }
        return [
            AnalysisResult(
                slide_id="A7.4",
                title="DCTR Segment Trends",
                chart_path=chart_path,
                excel_data={"Segment Trends": df},
                notes=f"Personal: {p_hist:.1f}% -> {p_l12m:.1f}% ({p_trend:+.1f}pp)",
            )
        ]

    # -- A7.5: Decade Trend ---------------------------------------------------

    def _decade_trend(self, ctx: PipelineContext) -> list[AnalysisResult]:
        d1 = ctx.results.get("dctr_1", {}).get("decade", pd.DataFrame())
        d4 = ctx.results.get("dctr_4", {}).get("decade", pd.DataFrame())
        d5 = ctx.results.get("dctr_5", {}).get("decade", pd.DataFrame())
        if d1.empty:
            return []

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_decade_trend.png"
            try:
                decades = d1["Decade"].values
                overall = d1["DCTR %"].values * 100
                x = np.arange(len(decades))

                with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
                    ax2 = ax.twinx()
                    total_vol = d1["Total Accounts"].values
                    ax2.bar(x, total_vol, alpha=0.2, color="gray", edgecolor="none", width=0.8)
                    ax2.set_ylabel("Account Volume", fontsize=24, color="gray")
                    max_vol = max(total_vol) if len(total_vol) > 0 else 100
                    ax2.set_ylim(0, max_vol * 1.3)
                    ax2.tick_params(axis="y", colors="gray", labelsize=24)

                    ax.plot(
                        x,
                        overall,
                        color="black",
                        linewidth=3,
                        linestyle="--",
                        marker="o",
                        markersize=18,
                        label="Overall",
                        zorder=2,
                    )

                    if not d4.empty:
                        p_merged = d4.set_index("Decade").reindex(decades)
                        p_vals = p_merged["DCTR %"].values * 100
                        valid_mask = ~np.isnan(p_vals)
                        if valid_mask.any():
                            ax.plot(
                                x[valid_mask],
                                p_vals[valid_mask],
                                color=PERSONAL,
                                linewidth=4,
                                marker="o",
                                markersize=12,
                                label="Personal",
                                zorder=3,
                            )

                    if not d5.empty and d5["Total Accounts"].sum() > 0:
                        b_merged = d5.set_index("Decade").reindex(decades)
                        b_vals = b_merged["DCTR %"].values * 100
                        valid_mask = ~np.isnan(b_vals)
                        if valid_mask.any():
                            ax.plot(
                                x[valid_mask],
                                b_vals[valid_mask],
                                color=BUSINESS,
                                linewidth=4,
                                marker="s",
                                markersize=12,
                                label="Business",
                                zorder=3,
                            )

                    ax.set_xticks(x)
                    ax.set_xticklabels(decades, fontsize=24, rotation=45 if len(decades) > 8 else 0)
                    ax.set_ylabel("DCTR (%)", fontsize=24, fontweight="bold")
                    ax.set_title(
                        "Historical DCTR Trend by Decade", fontsize=24, fontweight="bold", pad=20
                    )
                    ax.set_ylim(0, min(110, max(overall) * 1.15) if len(overall) > 0 else 100)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x)}%"))
                    ax.tick_params(axis="y", labelsize=24)
                    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=18)
                    ax.set_axisbelow(True)
                    ax.spines["top"].set_visible(False)
                    ax2.spines["top"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.5 chart failed: {err}", err=exc)

        return [
            AnalysisResult(
                slide_id="A7.5",
                title="Historical DCTR Trend by Decade",
                chart_path=chart_path,
                excel_data={"Decade": d1},
                notes=f"{len(d1)} decades plotted",
            )
        ]

    # -- A7.6a: L12M Monthly Trend -------------------------------------------

    def _l12m_trend(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        ep = ctx.subsets.eligible_personal
        eb = ctx.subsets.eligible_business
        if ed is None or ed.empty or ctx.end_date is None:
            return []

        months = l12m_month_labels(ctx.end_date)
        el12 = filter_l12m(ed, ctx.start_date, ctx.end_date) if ctx.start_date else pd.DataFrame()
        if el12.empty:
            return []

        def _monthly_rates(dataset: pd.DataFrame, month_list: list[str]) -> list[float]:
            dc = dataset.copy()
            dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
            dc["Month_Year"] = dc["Date Opened"].dt.strftime("%b%y")
            rates = []
            for m in month_list:
                md = dc[dc["Month_Year"] == m]
                t, w, d = dctr(md)
                rates.append(d * 100 if t > 0 else np.nan)
            return rates

        overall_rates = _monthly_rates(el12, months)
        ep_l12 = (
            filter_l12m(ep, ctx.start_date, ctx.end_date)
            if ep is not None and not ep.empty
            else pd.DataFrame()
        )
        personal_rates = (
            _monthly_rates(ep_l12, months) if not ep_l12.empty else [np.nan] * len(months)
        )
        has_biz = eb is not None and not eb.empty
        eb_l12 = filter_l12m(eb, ctx.start_date, ctx.end_date) if has_biz else pd.DataFrame()
        business_rates = (
            _monthly_rates(eb_l12, months) if not eb_l12.empty else [np.nan] * len(months)
        )

        trend_df = pd.DataFrame(
            {
                "Month": months,
                "Overall DCTR %": overall_rates,
                "Personal DCTR %": personal_rates,
                "Business DCTR %": business_rates,
            }
        )

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_l12m_trend.png"
            try:
                with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
                    x = np.arange(len(months))
                    ov = np.array(overall_rates)
                    mask = ~np.isnan(ov)
                    if mask.any():
                        ax.plot(
                            x[mask],
                            ov[mask],
                            color="black",
                            linewidth=4,
                            linestyle="--",
                            marker="o",
                            markersize=12,
                            label="Overall",
                            zorder=2,
                        )
                    pr = np.array(personal_rates)
                    pmask = ~np.isnan(pr)
                    if pmask.any():
                        ax.plot(
                            x[pmask],
                            pr[pmask],
                            color=PERSONAL,
                            linewidth=5,
                            marker="o",
                            markersize=14,
                            label="Personal",
                            zorder=3,
                        )
                    if has_biz:
                        br = np.array(business_rates)
                        bmask = ~np.isnan(br)
                        if bmask.any():
                            ax.plot(
                                x[bmask],
                                br[bmask],
                                color=BUSINESS,
                                linewidth=4,
                                marker="s",
                                markersize=12,
                                label="Business",
                                zorder=3,
                            )

                    ax.set_xticks(x)
                    ax.set_xticklabels(months, rotation=45, ha="right", fontsize=22)
                    ax.set_ylabel("DCTR (%)", fontsize=28, fontweight="bold")
                    ax.set_title(
                        "Trailing Twelve Months DCTR Trend", fontsize=28, fontweight="bold", pad=25
                    )
                    ax.tick_params(axis="y", labelsize=24)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x)}%"))
                    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=18)
                    ax.set_axisbelow(True)
                    ax.spines["top"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.6a chart failed: {err}", err=exc)

        return [
            AnalysisResult(
                slide_id="A7.6a",
                title="Trailing Twelve Months DCTR Trend",
                chart_path=chart_path,
                excel_data={"L12M Trend": trend_df},
                notes=f"{len(months)} months plotted",
            )
        ]

    # -- A7.6b: Personal vs Business by Decade --------------------------------

    def _decade_pb(self, ctx: PipelineContext) -> list[AnalysisResult]:
        d4 = ctx.results.get("dctr_4", {}).get("decade", pd.DataFrame())
        d5 = ctx.results.get("dctr_5", {}).get("decade", pd.DataFrame())
        if d4.empty:
            return []

        has_biz = not d5.empty and d5["Total Accounts"].sum() > 0
        p_dec = d4[d4["Decade"] != "TOTAL"].copy() if "Decade" in d4.columns else d4

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir and not p_dec.empty:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_decade_pb.png"
            try:
                if has_biz:
                    b_dec = d5[d5["Decade"] != "TOTAL"].copy()
                    all_decades = sorted(
                        set(p_dec["Decade"].tolist()) | set(b_dec["Decade"].tolist())
                    )
                else:
                    all_decades = p_dec["Decade"].tolist()

                with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
                    x = np.arange(len(all_decades))
                    p_rates = []
                    for d in all_decades:
                        match = p_dec[p_dec["Decade"] == d]
                        p_rates.append(match["DCTR %"].iloc[0] * 100 if not match.empty else 0)

                    if has_biz:
                        width = 0.35
                        b_rates = []
                        for d in all_decades:
                            match = b_dec[b_dec["Decade"] == d]
                            b_rates.append(match["DCTR %"].iloc[0] * 100 if not match.empty else 0)
                        ax.bar(
                            x - width / 2,
                            p_rates,
                            width,
                            label="Personal",
                            color=PERSONAL,
                            alpha=0.9,
                            edgecolor="black",
                            linewidth=2,
                        )
                        ax.bar(
                            x + width / 2,
                            b_rates,
                            width,
                            label="Business",
                            color=BUSINESS,
                            alpha=0.9,
                            edgecolor="black",
                            linewidth=2,
                        )
                    else:
                        ax.bar(
                            x,
                            p_rates,
                            0.6,
                            label="Personal",
                            color=PERSONAL,
                            alpha=0.9,
                            edgecolor="black",
                            linewidth=2,
                        )

                    ax.set_title(
                        "Personal vs Business DCTR by Decade",
                        fontsize=24,
                        fontweight="bold",
                        pad=20,
                    )
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_xticks(x)
                    ax.set_xticklabels(all_decades, fontsize=20)
                    ax.tick_params(axis="y", labelsize=20)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=18)
                    ax.set_axisbelow(True)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.6b chart failed: {err}", err=exc)

        return [
            AnalysisResult(
                slide_id="A7.6b",
                title="Personal vs Business DCTR by Decade",
                chart_path=chart_path,
                excel_data={"Personal Decade": p_dec},
                notes=f"{len(p_dec)} decades",
            )
        ]

    # -- A7.14: Seasonality ---------------------------------------------------

    def _seasonality(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []

        valid = ed.copy()
        valid["Date Opened"] = pd.to_datetime(valid["Date Opened"], errors="coerce")
        valid = valid[valid["Date Opened"].notna()]
        if valid.empty:
            return []

        valid["Month Name"] = valid["Date Opened"].dt.month_name()
        valid["Quarter"] = "Q" + valid["Date Opened"].dt.quarter.astype(str)
        valid["Day of Week"] = valid["Date Opened"].dt.day_name()

        month_order = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        m_rows = []
        for m in month_order:
            md = valid[valid["Month Name"] == m]
            if len(md) > 0:
                t, w, d = dctr(md)
                m_rows.append(
                    {"Month Name": m, "Total Accounts": t, "With Debit": w, "DCTR %": d * 100}
                )
        monthly = pd.DataFrame(m_rows)

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir and not monthly.empty:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_seasonality.png"
            try:
                with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
                    vals = monthly["DCTR %"].values
                    ax.bar(range(len(monthly)), vals, color=TEAL, edgecolor="white")
                    ax.set_xticks(range(len(monthly)))
                    ax.set_xticklabels(
                        [m[:3] for m in monthly["Month Name"]], rotation=45, fontsize=14
                    )
                    for i, v in enumerate(vals):
                        ax.text(
                            i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=12, fontweight="bold"
                        )
                    ax.set_ylabel("DCTR (%)", fontsize=16)
                    ax.set_title("DCTR Seasonality Analysis", fontsize=20, fontweight="bold")
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.set_ylim(0, max(vals) * 1.15 if len(vals) > 0 else 100)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.set_axisbelow(True)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.14 chart failed: {err}", err=exc)

        best = monthly.loc[monthly["DCTR %"].idxmax(), "Month Name"] if not monthly.empty else "N/A"
        worst = (
            monthly.loc[monthly["DCTR %"].idxmin(), "Month Name"] if not monthly.empty else "N/A"
        )
        return [
            AnalysisResult(
                slide_id="A7.14",
                title="DCTR Seasonality Analysis",
                chart_path=chart_path,
                excel_data={"Monthly": monthly},
                notes=f"Best: {best} | Worst: {worst}",
            )
        ]

    # -- A7.15: Vintage & Cohort ----------------------------------------------

    def _vintage(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []

        valid = ed.copy()
        valid["Date Opened"] = pd.to_datetime(valid["Date Opened"], errors="coerce")
        valid = valid[valid["Date Opened"].notna()]
        if valid.empty:
            return []

        valid["Account Age Days"] = (pd.Timestamp.now() - valid["Date Opened"]).dt.days
        valid["Year"] = valid["Date Opened"].dt.year

        vintage_buckets = [
            ("0-30 days", 0, 30),
            ("31-90 days", 31, 90),
            ("91-180 days", 91, 180),
            ("181-365 days", 181, 365),
            ("1-2 years", 366, 730),
            ("2-3 years", 731, 1095),
            ("3-5 years", 1096, 1825),
            ("5-10 years", 1826, 3650),
            ("10+ years", 3651, 999999),
        ]
        v_rows = []
        cum_debit = 0
        cum_total = 0
        for label, lo, hi in vintage_buckets:
            seg = valid[(valid["Account Age Days"] >= lo) & (valid["Account Age Days"] <= hi)]
            if len(seg) > 0:
                t, w, d = dctr(seg)
                cum_total += t
                cum_debit += w
                v_rows.append(
                    {
                        "Age Bucket": label,
                        "Total Accounts": t,
                        "With Debit": w,
                        "DCTR %": d * 100,
                        "Cumulative Capture %": cum_debit / cum_total * 100 if cum_total else 0,
                    }
                )
        vintage_df = pd.DataFrame(v_rows)

        cohort_years = sorted(valid["Year"].dropna().unique())
        c_rows = []
        for yr in cohort_years:
            seg = valid[valid["Year"] == yr]
            if len(seg) > 10:
                t, w, d = dctr(seg)
                c_rows.append(
                    {
                        "Cohort Year": int(yr),
                        "Total Accounts": t,
                        "With Debit": w,
                        "DCTR %": d * 100,
                    }
                )
        cohort_df = pd.DataFrame(c_rows)

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir and not vintage_df.empty:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_vintage.png"
            try:
                with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
                    x_pos = np.arange(len(vintage_df))
                    ax.bar(x_pos, vintage_df["DCTR %"], color=TEAL, alpha=0.8, edgecolor="white")
                    for i, v in enumerate(vintage_df["DCTR %"]):
                        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=14, fontweight="bold")
                    ax.set_xticks(x_pos)
                    ax.set_xticklabels(
                        vintage_df["Age Bucket"], rotation=30, ha="right", fontsize=14
                    )
                    ax.set_ylabel("DCTR (%)", fontsize=16)
                    ax.set_title(
                        "DCTR by Account Age (Vintage Curve)", fontweight="bold", fontsize=18
                    )
                    dctr_vals = vintage_df["DCTR %"].values
                    ax.set_ylim(0, max(dctr_vals) * 1.15 if len(dctr_vals) > 0 else 100)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.grid(axis="y", alpha=0.3, linestyle="--")
                    ax.set_axisbelow(True)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.15 chart failed: {err}", err=exc)

        new_dctr = vintage_df.iloc[0]["DCTR %"] if not vintage_df.empty else 0
        mature_dctr = vintage_df.iloc[-1]["DCTR %"] if not vintage_df.empty else 0
        return [
            AnalysisResult(
                slide_id="A7.15",
                title="Vintage Curves & Cohort Analysis",
                chart_path=chart_path,
                excel_data={"Vintage": vintage_df, "Cohort": cohort_df},
                notes=f"New: {new_dctr:.0f}% | Mature: {mature_dctr:.0f}% | {len(cohort_df)} cohort years",
            )
        ]
