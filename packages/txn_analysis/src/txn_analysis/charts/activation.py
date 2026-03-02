"""M24: Activation & dormancy charts (matplotlib)."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import (
    ACCENT,
    CORAL,
    GOLD,
    TEAL,
    WARM_GRAY,
    set_insight_title,
)
from txn_analysis.settings import ChartConfig

_STATUS_COLORS = {
    "Active": TEAL,
    "At-Risk": GOLD,
    "Dormant": CORAL,
    "Lost": WARM_GRAY,
}


def chart_dormancy_bars(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Dormancy status distribution -- stacked horizontal bar."""
    dormancy = result.data.get("dormancy")
    if dormancy is None or dormancy.empty:
        return Figure()

    with chart_figure(figsize=(10, 4)) as (fig, ax):
        statuses = dormancy["Status"].tolist()
        accounts = dormancy["Accounts"].astype(int).tolist()

        colors = [_STATUS_COLORS.get(s, WARM_GRAY) for s in statuses]
        y_pos = list(range(len(statuses)))

        ax.barh(y_pos, accounts, color=colors, height=0.6)

        for i, (acct, status) in enumerate(zip(accounts, statuses)):
            if acct > 0:
                ax.annotate(
                    f"{acct:,}",
                    xy=(acct, i),
                    xytext=(4, 0),
                    textcoords="offset points",
                    fontsize=10,
                    va="center",
                    fontweight="bold",
                )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(statuses, fontsize=11)
        ax.xaxis.set_visible(False)

        total = sum(accounts)
        active = accounts[0] if statuses and statuses[0] == "Active" else 0
        active_pct = active / total * 100 if total else 0

        set_insight_title(
            ax,
            f"{active_pct:.0f}% of accounts active -- {total - active:,} need attention",
            "Account status by days since last transaction",
        )
        fig.tight_layout()

    return fig


def chart_reactivation_flow(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Monthly reactivation flow -- stacked bar showing new, reactivated, went dormant."""
    reactivation = result.data.get("reactivation")
    if reactivation is None or reactivation.empty:
        return Figure()

    with chart_figure(figsize=(12, 5)) as (fig, ax):
        months = reactivation["Month"].tolist()
        x = np.arange(len(months))
        width = 0.6

        new_vals = reactivation["New"].tolist()
        react_vals = reactivation["Reactivated"].tolist()
        dormant_vals = reactivation["Went Dormant"].tolist()

        # Positive stack: new + reactivated
        ax.bar(x, new_vals, width=width, color=ACCENT, label="New Accounts")
        ax.bar(x, react_vals, width=width, bottom=new_vals, color=TEAL, label="Reactivated")

        # Negative stack: went dormant
        neg_dormant = [-d for d in dormant_vals]
        ax.bar(x, neg_dormant, width=width, color=CORAL, alpha=0.7, label="Went Dormant")

        ax.axhline(0, color="#888888", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=-45, ha="right", fontsize=8)
        ax.set_ylabel("Account Flow", fontsize=10)
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=3,
            frameon=False,
            fontsize=9,
        )

        total_reactivated = sum(react_vals)
        set_insight_title(
            ax,
            f"{total_reactivated:,} accounts reactivated across {len(months)} months",
            "Monthly account flow: new activations, reactivations, and dormancy",
        )
        fig.tight_layout()

    return fig
