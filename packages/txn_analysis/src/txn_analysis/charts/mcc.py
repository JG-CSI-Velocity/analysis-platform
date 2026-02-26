"""M2: MCC triple-subplot chart (matplotlib)."""

from __future__ import annotations

from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.bar_charts import _fmt
from txn_analysis.charts.guards import multi_axes
from txn_analysis.charts.theme import ACCENT, ACCENT_SECONDARY, TEAL
from txn_analysis.settings import ChartConfig


def chart_mcc_comparison(
    mcc_accounts: AnalysisResult,
    mcc_transactions: AnalysisResult,
    mcc_spend: AnalysisResult,
    config: ChartConfig,
) -> Figure:
    """Triple horizontal bar: MCC by accounts, transactions, and spend."""
    datasets = [
        (mcc_accounts, "unique_accounts", ACCENT_SECONDARY, ",.0f", "By Accounts"),
        (mcc_transactions, "transaction_count", TEAL, ",.0f", "By Transactions"),
        (mcc_spend, "total_amount", ACCENT, "$,.0f", "By Spend"),
    ]
    top_n = 15

    with multi_axes(nrows=1, ncols=3, figsize=(18, max(5, top_n * 0.35 + 1))) as (fig, axes):
        for ax, (result, value_col, color, fmt, subtitle) in zip(axes, datasets):
            df = result.df
            if df.empty:
                ax.set_visible(False)
                continue

            data = df[df["mcc_description"].astype(str) != "Grand Total"].head(top_n)
            labels = list(reversed(data["mcc_description"].tolist()))
            values = list(reversed(data[value_col].tolist()))
            n = len(labels)

            y_pos = list(range(n))
            ax.barh(y_pos, values, color=color, height=0.6)

            for i, val in enumerate(values):
                ax.annotate(
                    _fmt(val, fmt),
                    xy=(val, i),
                    xytext=(4, 0),
                    textcoords="offset points",
                    fontsize=8,
                    va="center",
                )

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=8)
            ax.xaxis.set_visible(False)
            ax.set_title(subtitle, fontsize=12, fontweight="bold")

        fig.suptitle(
            "MCC Code Comparison",
            fontsize=16,
            fontweight="bold",
            x=0.02,
            ha="left",
        )
        fig.tight_layout(rect=[0, 0, 1, 0.95])

    return fig
