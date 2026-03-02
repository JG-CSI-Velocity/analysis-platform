"""M23: Mailer effectiveness charts (matplotlib)."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import (
    ACCENT,
    CORAL,
    TEAL,
    WARM_GRAY,
    format_currency,
    set_insight_title,
)
from txn_analysis.settings import ChartConfig


def chart_did_parallel(result: AnalysisResult, config: ChartConfig) -> Figure:
    """ITS actual vs counterfactual trend line with mailer cutoff."""
    its = result.data.get("its")
    if its is None or its.empty:
        return Figure()

    with chart_figure(figsize=(12, 6)) as (fig, ax):
        months = its["Month"].tolist()
        x = np.arange(len(months))
        actual = its["actual_spend"].tolist()
        counterfactual = its["counterfactual"].tolist()
        post_flags = its["post"].tolist()

        ax.plot(x, actual, color=ACCENT, linewidth=2.5, marker="o", markersize=5, label="Actual")
        ax.plot(
            x,
            counterfactual,
            color=WARM_GRAY,
            linewidth=2,
            linestyle="--",
            label="Counterfactual (pre-trend)",
        )

        # Shade post period
        post_start = next((i for i, p in enumerate(post_flags) if p == 1), None)
        if post_start is not None:
            ax.axvspan(post_start - 0.5, len(months) - 0.5, alpha=0.08, color=TEAL)
            ax.axvline(post_start - 0.5, color=CORAL, linewidth=1.5, linestyle="--", label="Mailer")

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=-45, ha="right", fontsize=8)
        ax.set_ylabel("Avg Monthly Spend ($)", fontsize=10)
        ax.legend(loc="upper left", frameon=False, fontsize=9)

        did_est = result.metadata.get("did_estimate", 0)
        set_insight_title(
            ax,
            f"Responder spend lifted {format_currency(did_est)}/mo vs control",
            "Interrupted Time Series: actual spend vs counterfactual pre-trend",
        )
        fig.tight_layout()

    return fig


def chart_decay_curve(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Effect decay: monthly lift with trend line."""
    decay = result.data.get("decay")
    if decay is None or decay.empty:
        return Figure()

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        months_post = decay["Months Post-Mailer"].tolist()
        lifts = decay["Lift"].tolist()

        ax.bar(months_post, lifts, color=ACCENT, width=0.6, alpha=0.8)

        for i, (mp, lift) in enumerate(zip(months_post, lifts)):
            ax.annotate(
                format_currency(lift),
                xy=(mp, lift),
                xytext=(0, 6),
                textcoords="offset points",
                fontsize=9,
                ha="center",
                va="bottom",
            )

        ax.axhline(0, color="#888888", linewidth=0.8)
        ax.set_xlabel("Months Post-Mailer", fontsize=10)
        ax.set_ylabel("Monthly Lift ($)", fontsize=10)

        half_life = result.metadata.get("half_life")
        subtitle = "Monthly incremental spend (responders minus control)"
        if half_life and half_life != float("inf"):
            subtitle += f" | Half-life: {half_life:.1f} months"

        set_insight_title(ax, "Mailer Effect Decay", subtitle)
        fig.tight_layout()

    return fig


def chart_cumulative_lift(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Cumulative incremental spend area chart."""
    cum = result.data.get("cumulative")
    if cum is None or cum.empty:
        return Figure()

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        months = cum["Month"].tolist()
        x = np.arange(len(months))
        cumulative = cum["Cumulative Incremental"].tolist()

        ax.fill_between(x, cumulative, color=ACCENT, alpha=0.3)
        ax.plot(x, cumulative, color=ACCENT, linewidth=2.5, marker="o", markersize=5)

        for i, val in enumerate(cumulative):
            ax.annotate(
                format_currency(val),
                xy=(i, val),
                xytext=(0, 8),
                textcoords="offset points",
                fontsize=9,
                ha="center",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=-45, ha="right", fontsize=8)
        ax.set_ylabel("Cumulative Incremental ($)", fontsize=10)
        ax.axhline(0, color="#888888", linewidth=0.8)

        total = cumulative[-1] if cumulative else 0
        set_insight_title(
            ax,
            f"{format_currency(total)} total incremental spend from mailer",
            "Running sum of responder lift above control group",
        )
        fig.tight_layout()

    return fig


def chart_lift_violin(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Per-account lift distribution: responders vs non-responders."""
    lift = result.data.get("lift_distribution")
    if lift is None or lift.empty:
        return Figure()

    groups = ["Responder", "Non-Responder"]
    group_data = [lift[lift["group"] == g]["lift_pct"].dropna() for g in groups]

    if all(d.empty for d in group_data):
        return Figure()

    with chart_figure(figsize=(8, 6)) as (fig, ax):
        positions = [1, 2]
        colors = [ACCENT, WARM_GRAY]

        parts = ax.violinplot(
            [d.tolist() for d in group_data if not d.empty],
            positions=[p for p, d in zip(positions, group_data) if not d.empty],
            showmeans=True,
            showmedians=True,
        )

        for i, pc in enumerate(parts["bodies"]):
            idx = [j for j, d in enumerate(group_data) if not d.empty][i]
            pc.set_facecolor(colors[idx])
            pc.set_alpha(0.6)

        ax.axhline(0, color=CORAL, linewidth=1, linestyle="--", alpha=0.7)
        ax.set_xticks(positions)
        ax.set_xticklabels(groups, fontsize=11)
        ax.set_ylabel("Lift (%)", fontsize=10)

        resp_data = group_data[0]
        positive_pct = (resp_data > 0).sum() / len(resp_data) * 100 if not resp_data.empty else 0

        set_insight_title(
            ax,
            f"{positive_pct:.0f}% of responders increased spending",
            "Per-account spend change distribution (post minus pre)",
        )
        fig.tight_layout()

    return fig
