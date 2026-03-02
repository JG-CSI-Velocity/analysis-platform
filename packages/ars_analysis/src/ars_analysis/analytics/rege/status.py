"""Reg E Status -- core opt-in rates, historical, L12M, trend.

Slide IDs: A8.1, A8.2, A8.3, A8.12.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import l12m_month_labels
from ars_analysis.analytics.rege._helpers import reg_e_base, rege, total_row
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import ELIGIBLE, HISTORICAL, NEUTRAL, SILVER, TEAL
from ars_analysis.pipeline.context import PipelineContext


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run analysis function, catch errors, return failed result on exception."""
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [
            AnalysisResult(
                slide_id=label,
                title=label,
                success=False,
                error=str(exc),
            )
        ]


@register
class RegEStatus(AnalysisModule):
    """Core Reg E opt-in rates -- overall status, historical, L12M monthly, trend."""

    module_id = "rege.status"
    display_name = "Reg E Opt-In Status"
    section = "rege"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Reg E Status for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._overall, "A8.1", ctx)
        results += _safe(self._historical, "A8.2", ctx)
        results += _safe(self._l12m_monthly, "A8.3", ctx)
        results += _safe(self._trend_24m, "A8.12", ctx)
        return results

    # -- A8.1: Overall Reg E Status (donut chart) ---------------------------

    def _overall(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.1: Overall Reg E Status")
        base, base_l12m, col, opts = reg_e_base(ctx)

        t_all, oi_all, r_all = rege(base, col, opts)
        t_l12m, oi_l12m, r_l12m = 0, 0, 0.0
        if base_l12m is not None and not base_l12m.empty:
            t_l12m, oi_l12m, r_l12m = rege(base_l12m, col, opts)

        summary = pd.DataFrame(
            [
                {
                    "Category": "All-Time",
                    "Total Accounts": t_all,
                    "Opted In": oi_all,
                    "Opted Out": t_all - oi_all,
                    "Opt-In Rate %": r_all,
                },
                {
                    "Category": "Last 12 Months",
                    "Total Accounts": t_l12m,
                    "Opted In": oi_l12m,
                    "Opted Out": t_l12m - oi_l12m,
                    "Opt-In Rate %": r_l12m,
                },
            ]
        )

        # Store for downstream modules
        ctx.results["reg_e_1"] = {
            "opt_in_rate": r_all,
            "l12m_rate": r_l12m,
            "total_base": t_all,
            "opted_in": oi_all,
            "opted_out": t_all - oi_all,
        }

        # Side-by-side donut charts (All-Time vs L12M)
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_1_reg_e_status.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, _):
            fig.clf()
            ax1 = fig.add_subplot(1, 2, 1)
            ax2 = fig.add_subplot(1, 2, 2)

            donut_data = [
                (ax1, [oi_all, t_all - oi_all], "All-Time", r_all, t_all),
                (ax2, [oi_l12m, max(t_l12m - oi_l12m, 0)], "Last 12 Months", r_l12m, t_l12m),
            ]

            for ax_d, sizes, label, rate, total in donut_data:
                colors = [ELIGIBLE, SILVER]
                wedges, texts = ax_d.pie(
                    sizes,
                    startangle=90,
                    colors=colors,
                    wedgeprops={"edgecolor": "white", "linewidth": 2},
                )
                # Inner circle for donut effect
                centre = plt.Circle((0, 0), 0.55, fc="white")
                ax_d.add_patch(centre)

                # Rate in center
                ax_d.text(
                    0,
                    0.05,
                    f"{rate:.1%}",
                    ha="center",
                    va="center",
                    fontsize=28,
                    fontweight="bold",
                    color="#1B2A4A",
                )
                ax_d.text(
                    0,
                    -0.18,
                    "opt-in rate",
                    ha="center",
                    va="center",
                    fontsize=12,
                    color=NEUTRAL,
                )

                ax_d.set_title(label, fontsize=20, fontweight="bold", pad=15)
                ax_d.set_aspect("equal")

                # Legend below with counts
                legend_labels = [
                    f"Opted In: {sizes[0]:,}",
                    f"Opted Out: {sizes[1]:,}",
                ]
                ax_d.legend(
                    wedges,
                    legend_labels,
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.02),
                    fontsize=14,
                    frameon=False,
                    ncol=1,
                )

            fig.suptitle(
                f"Reg E Opt-In Status -- {ctx.client.client_name}",
                fontsize=22,
                fontweight="bold",
                y=1.0,
            )
        chart_path = save_to

        change = r_l12m - r_all
        trend = "improving" if change > 0.01 else "declining" if change < -0.01 else "stable"
        notes = f"All-time: {r_all:.1%} ({oi_all:,}/{t_all:,}). L12M: {r_l12m:.1%}. Trend: {trend}"

        return [
            AnalysisResult(
                slide_id="A8.1",
                title="Overall Reg E Status",
                chart_path=chart_path,
                excel_data={"Summary": summary},
                notes=notes,
            )
        ]

    # -- A8.2: Historical by Year + Decade ----------------------------------

    def _historical(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.2: Historical Reg E (Year/Decade)")
        base, _, col, opts = reg_e_base(ctx)

        df = base.copy()
        df["Year"] = pd.to_datetime(df["Date Opened"], errors="coerce", format="mixed").dt.year
        valid = df.dropna(subset=["Year"]).copy()

        # Yearly breakdown
        rows = []
        for yr in sorted(valid["Year"].dropna().unique()):
            yd = valid[valid["Year"] == yr]
            t, oi, r = rege(yd, col, opts)
            rows.append(
                {
                    "Year": int(yr),
                    "Total Accounts": t,
                    "Opted In": oi,
                    "Opted Out": t - oi,
                    "Opt-In Rate": r,
                }
            )
        yearly = pd.DataFrame(rows)
        if not yearly.empty:
            yearly = total_row(yearly, "Year")

        # Decade breakdown
        valid["Decade"] = (valid["Year"] // 10 * 10).astype(int).astype(str) + "s"
        drows = []
        for dec in sorted(valid["Decade"].unique()):
            dd = valid[valid["Decade"] == dec]
            t, oi, r = rege(dd, col, opts)
            drows.append(
                {
                    "Decade": dec,
                    "Total Accounts": t,
                    "Opted In": oi,
                    "Opted Out": t - oi,
                    "Opt-In Rate": r,
                }
            )
        decade = pd.DataFrame(drows)
        if not decade.empty:
            decade = total_row(decade, "Decade")

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_2_reg_e_historical.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        chart_yearly = (
            yearly[yearly["Year"] != "TOTAL"].copy() if not yearly.empty else pd.DataFrame()
        )

        with chart_figure(figsize=(18, 7), save_path=save_to) as (fig, _):
            ax1 = fig.add_subplot(1, 2, 1)
            ax2 = fig.add_subplot(1, 2, 2)

            if not chart_yearly.empty:
                x = range(len(chart_yearly))
                total_rows = yearly[yearly["Year"] == "TOTAL"]["Opt-In Rate"]
                overall = (
                    total_rows.values[0]
                    if len(total_rows) > 0
                    else chart_yearly["Opt-In Rate"].mean()
                )
                bars = ax1.bar(
                    x, chart_yearly["Opt-In Rate"] * 100, color=HISTORICAL, edgecolor="none"
                )
                for bar, rate in zip(bars, chart_yearly["Opt-In Rate"]):
                    ax1.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.5,
                        f"{rate:.1%}",
                        ha="center",
                        fontsize=10,
                        fontweight="bold",
                    )
                ax1.axhline(y=overall * 100, color="red", linestyle="--", linewidth=2, alpha=0.7)
                ax1.set_xticks(list(x))
                ax1.set_xticklabels(
                    [str(int(y)) for y in chart_yearly["Year"]], rotation=45, ha="right"
                )
                ax1.set_ylabel("Opt-In Rate (%)")
                ax1.set_title("Reg E Opt-In by Year", fontweight="bold")
                ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))

            chart_decade = (
                decade[decade["Decade"] != "TOTAL"].copy() if not decade.empty else pd.DataFrame()
            )
            if not chart_decade.empty:
                x2 = range(len(chart_decade))
                dec_total = decade[decade["Decade"] == "TOTAL"]["Opt-In Rate"]
                dec_overall = (
                    dec_total.values[0]
                    if len(dec_total) > 0
                    else chart_decade["Opt-In Rate"].mean()
                )
                bars2 = ax2.bar(x2, chart_decade["Opt-In Rate"] * 100, color=TEAL, edgecolor="none")
                for bar, rate in zip(bars2, chart_decade["Opt-In Rate"]):
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.5,
                        f"{rate:.1%}",
                        ha="center",
                        fontsize=10,
                        fontweight="bold",
                    )
                ax2.axhline(
                    y=dec_overall * 100, color="red", linestyle="--", linewidth=2, alpha=0.7
                )
                ax2.set_xticks(list(x2))
                ax2.set_xticklabels(chart_decade["Decade"].tolist(), rotation=45, ha="right")
                ax2.set_ylabel("Opt-In Rate (%)")
                ax2.set_title("Reg E Opt-In by Decade", fontweight="bold")
                ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))

            fig.tight_layout()
        chart_path = save_to

        notes = f"{len(rows)} years, {len(drows)} decades analyzed"
        if not chart_yearly.empty:
            best = chart_yearly.loc[chart_yearly["Opt-In Rate"].idxmax()]
            worst = chart_yearly.loc[chart_yearly["Opt-In Rate"].idxmin()]
            notes = (
                f"Best: {int(best['Year'])} ({best['Opt-In Rate']:.1%}). "
                f"Worst: {int(worst['Year'])} ({worst['Opt-In Rate']:.1%})"
            )

        ctx.results["reg_e_2"] = {"yearly": yearly, "decade": decade}
        return [
            AnalysisResult(
                slide_id="A8.2",
                title="Reg E Historical (Year/Decade)",
                chart_path=chart_path,
                excel_data={"Yearly": yearly, "Decade": decade},
                notes=notes,
            )
        ]

    # -- A8.3: L12M Monthly Reg E -------------------------------------------

    def _l12m_monthly(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.3: L12M Monthly Reg E")
        base, base_l12m, col, opts = reg_e_base(ctx)

        if base_l12m is None or base_l12m.empty:
            return [
                AnalysisResult(
                    slide_id="A8.3",
                    title="L12M Monthly Reg E",
                    success=False,
                    error="No L12M Reg E data",
                )
            ]

        l12m_labels = l12m_month_labels(ctx.end_date)
        df = base_l12m.copy()
        df["Month_Year"] = pd.to_datetime(
            df["Date Opened"], errors="coerce", format="mixed"
        ).dt.strftime("%b%y")

        rows = []
        for my in l12m_labels:
            ma = df[df["Month_Year"] == my]
            t, oi, r = rege(ma, col, opts) if len(ma) > 0 else (0, 0, 0.0)
            rows.append(
                {
                    "Month": my,
                    "Total Accounts": t,
                    "Opted In": oi,
                    "Opted Out": t - oi,
                    "Opt-In Rate": r,
                }
            )
        monthly = pd.DataFrame(rows)
        monthly = total_row(monthly, "Month")

        # Historical opt-in rate from full base (all-time)
        t_all, oi_all, r_all = rege(base, col, opts)
        historical_rate = r_all * 100

        # Chart: dual-axis combo (bars = accounts, lines = rates)
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_3_reg_e_l12m.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        chart = monthly[monthly["Month"] != "TOTAL"].copy()
        overall_rate = monthly[monthly["Month"] == "TOTAL"]["Opt-In Rate"].iloc[0] * 100
        monthly_counts = chart["Total Accounts"].tolist()
        ttm_rates = (chart["Opt-In Rate"] * 100).tolist()

        with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
            x = np.arange(len(chart))

            # Bars: eligible accounts opened per month (left axis)
            ax.bar(
                x,
                monthly_counts,
                color="#B0C4DE",
                edgecolor="#4A6FA5",
                linewidth=1.2,
                alpha=0.7,
                width=0.6,
                label="Eligible Accounts",
                zorder=1,
            )
            ax.set_ylabel("Eligible Accounts Opened", fontsize=20, fontweight="bold")
            ax.tick_params(axis="y", labelsize=18)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))

            # Lines: Reg E rates (right axis)
            ax2 = ax.twinx()

            # Historical rate (flat reference line)
            ax2.axhline(
                y=historical_rate,
                color="black",
                linestyle="--",
                linewidth=2.5,
                alpha=0.7,
                label=f"Historical Reg E ({historical_rate:.1f}%)",
                zorder=2,
            )

            # TTM per-month rate
            rates_arr = np.array(ttm_rates)
            valid_mask = rates_arr > 0
            if valid_mask.any():
                ax2.plot(
                    x[valid_mask],
                    rates_arr[valid_mask],
                    color="#1B4F72",
                    linewidth=3.5,
                    marker="o",
                    markersize=12,
                    label="TTM Reg E Opt-In",
                    zorder=4,
                )

            ax2.set_ylabel("Opt-In Rate (%)", fontsize=20, fontweight="bold")
            ax2.tick_params(axis="y", labelsize=18)
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}%"))

            ax.set_xticks(x)
            ax.set_xticklabels(chart["Month"].tolist(), rotation=45, ha="right", fontsize=18)
            ax.set_title(
                "Trailing Twelve Months -- Reg E Opt-In Trend",
                fontsize=24,
                fontweight="bold",
                pad=20,
            )

            # Combined legend
            bars_handle = ax.get_legend_handles_labels()
            lines_handle = ax2.get_legend_handles_labels()
            all_handles = bars_handle[0] + lines_handle[0]
            all_labels = bars_handle[1] + lines_handle[1]
            ax.legend(
                all_handles,
                all_labels,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.12),
                ncol=3,
                fontsize=14,
            )

            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)

            # Endpoint label on last valid month
            last_valid = valid_mask.nonzero()[0]
            if len(last_valid) > 0:
                li = last_valid[-1]
                ax2.annotate(
                    f"{rates_arr[li]:.1f}%",
                    xy=(x[li], rates_arr[li]),
                    xytext=(x[li] + 0.3, rates_arr[li] + 2),
                    fontsize=14,
                    fontweight="bold",
                    color="#1B4F72",
                    arrowprops={
                        "arrowstyle": "->",
                        "color": "#1B4F72",
                        "lw": 1.5,
                    },
                )
        chart_path = save_to

        active = chart[chart["Total Accounts"] > 0]
        best_month = (
            active.loc[active["Opt-In Rate"].idxmax(), "Month"] if not active.empty else "N/A"
        )
        notes = f"Overall L12M: {overall_rate:.1f}%. Historical: {historical_rate:.1f}%. Best: {best_month}"

        ctx.results["reg_e_3"] = {"monthly": monthly}
        return [
            AnalysisResult(
                slide_id="A8.3",
                title="L12M Monthly Reg E",
                chart_path=chart_path,
                excel_data={"Monthly": monthly},
                notes=notes,
            )
        ]

    # -- A8.12: 24-Month Trend ----------------------------------------------

    def _trend_24m(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.12: 24-Month Reg E Trend")
        base, _, col, opts = reg_e_base(ctx)

        df = base.copy()
        df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce", format="mixed")
        df["Year_Month"] = df["Date Opened"].dt.to_period("M")
        df["Has_RegE"] = df[col].isin(opts).astype(int)

        monthly = (
            df.groupby("Year_Month")
            .agg(
                Total=("Has_RegE", "count"),
                With_RegE=("Has_RegE", "sum"),
            )
            .reset_index()
        )
        monthly["Rate"] = (monthly["With_RegE"] / monthly["Total"]).round(4)
        monthly["Date"] = monthly["Year_Month"].dt.to_timestamp()
        monthly["Year_Month"] = monthly["Year_Month"].astype(str)
        last_24 = monthly.tail(24)

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_12_reg_e_trend.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        slope = 0.0
        with chart_figure(figsize=(16, 7), save_path=save_to) as (fig, ax):
            ax.plot(
                last_24["Date"],
                last_24["Rate"] * 100,
                "o-",
                color=ELIGIBLE,
                linewidth=2.5,
                markersize=6,
                label="Reg E Rate",
            )

            if len(last_24) >= 4:
                x_num = np.arange(len(last_24))
                z = np.polyfit(x_num, last_24["Rate"].values * 100, 1)
                p = np.poly1d(z)
                ax.plot(
                    last_24["Date"],
                    p(x_num),
                    "--",
                    color="navy",
                    linewidth=2,
                    alpha=0.6,
                    label=f"Trend ({z[0]:+.2f}pp/mo)",
                )
                slope = z[0]

            ax.set_ylabel("Opt-In Rate (%)")
            ax.set_title(
                f"Reg E Opt-In Trend (24 Months) -- {ctx.client.client_name}", fontweight="bold"
            )
            ax.legend()
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            rate_vals = last_24["Rate"].values * 100
            y_max = min(100, max(rate_vals) * 1.25) if len(rate_vals) > 0 else 100
            ax.set_ylim(0, y_max)
            fig.autofmt_xdate()
        chart_path = save_to

        start_r = last_24.iloc[0]["Rate"] * 100
        end_r = last_24.iloc[-1]["Rate"] * 100
        change = end_r - start_r
        direction = "improving" if slope > 0.1 else "declining" if slope < -0.1 else "stable"
        notes = (
            f"{len(last_24)} months. {start_r:.1f}% -> {end_r:.1f}% "
            f"({change:+.1f}pp). Trend: {direction}"
        )

        ctx.results["reg_e_12"] = {"monthly": last_24}
        return [
            AnalysisResult(
                slide_id="A8.12",
                title="Reg E 24-Month Trend",
                chart_path=chart_path,
                excel_data={"Trend": last_24[["Year_Month", "Total", "With_RegE", "Rate"]]},
                notes=notes,
            )
        ]
