"""Charts for summary analyses -- ICS overview, stat codes, products, debit, penetration."""

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    ACQUISITION,
    BAR_ALPHA,
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    DATA_LABEL_SIZE,
    NAVY,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def chart_total_ics(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Donut chart of ICS vs Non-ICS accounts."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 7), save_path=buf) as (_fig, ax):
        data = df[df["Category"] != "Total Accounts"].copy()
        colors = [NAVY, TEAL][: len(data)]

        wedges, _, autotexts = ax.pie(
            data["Count"],
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        centre = __import__("matplotlib.patches", fromlist=["Circle"]).Circle(
            (0, 0), 0.35, fc="white"
        )
        ax.add_patch(centre)

        for t in autotexts:
            t.set_fontsize(14)
            t.set_fontweight("bold")

        legend_labels = [
            f"{cat}  ({count:,})" for cat, count in zip(data["Category"], data["Count"])
        ]
        ax.legend(
            wedges,
            legend_labels,
            loc="center right",
            fontsize=13,
            frameon=False,
        )

        ax.set_title("Total ICS Accounts", fontsize=22, fontweight="bold", pad=20)
        ax.set_aspect("equal")

    buf.seek(0)
    return buf.read()


def chart_stat_code(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of ICS accounts by Stat Code."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 8), save_path=buf) as (_fig, ax):
        data = df[df["Stat Code"] != "Total"].copy()

        bars = ax.bar(
            data["Stat Code"],
            data["Count"],
            color=NAVY,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.5,
        )

        for bar, val in zip(bars, data["Count"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Stat Code")
        ax.set_ylabel("Account Count")
        ax.set_title("ICS Accounts by Stat Code")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_prod_code(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar of ICS accounts by Product Code."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Prod Code"] != "Total"].copy()
        data = data.sort_values("Account Count", ascending=True)
        n = len(data)

        base = np.array([0x1B, 0x36, 0x5D]) / 255
        colors = [(*base, 0.4 + 0.6 * i / max(n - 1, 1)) for i in range(n)]

        bars = ax.barh(
            range(n),
            data["Account Count"],
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Prod Code"])

        for bar, val in zip(bars, data["Account Count"]):
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                f"  {val:,}",
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Account Count")
        ax.set_title("ICS Accounts by Product Code")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_debit_dist(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Donut chart of Debit Card distribution."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 7), save_path=buf) as (_fig, ax):
        data = df[df["Debit?"] != "Total"].copy()
        colors = [ACQUISITION, "#E74C3C"][: len(data)]

        wedges, _, autotexts = ax.pie(
            data["Count"],
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        centre = __import__("matplotlib.patches", fromlist=["Circle"]).Circle(
            (0, 0), 0.35, fc="white"
        )
        ax.add_patch(centre)

        for t in autotexts:
            t.set_fontsize(14)
            t.set_fontweight("bold")

        legend_labels = [f"{lbl}  ({val:,})" for lbl, val in zip(data["Debit?"], data["Count"])]
        ax.legend(
            wedges,
            legend_labels,
            loc="center right",
            fontsize=13,
            frameon=False,
        )

        ax.set_title("Debit Card Distribution", fontsize=22, fontweight="bold", pad=20)
        ax.set_aspect("equal")

    buf.seek(0)
    return buf.read()


def chart_debit_by_prod(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked bar of Debit Yes/No by Product Code."""
    buf = BytesIO()
    with chart_figure(save_path=buf) as (_fig, ax):
        data = df[df["Prod Code"] != "Total"].copy()
        x = np.arange(len(data))
        width = 0.5

        yes_vals = pd.to_numeric(data.get("Yes", pd.Series(dtype=float)), errors="coerce").fillna(0)
        no_vals = pd.to_numeric(data.get("No", pd.Series(dtype=float)), errors="coerce").fillna(0)

        bars_yes = ax.bar(
            x,
            yes_vals,
            width,
            label="Debit Yes",
            color=ACQUISITION,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
        )
        bars_no = ax.bar(
            x,
            no_vals,
            width,
            bottom=yes_vals,
            label="Debit No",
            color="#E74C3C",
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=0.7,
        )

        # Data labels on each segment
        for bar, val in zip(bars_yes, yes_vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() / 2,
                    f"{int(val):,}",
                    ha="center",
                    va="center",
                    fontsize=DATA_LABEL_SIZE - 2,
                    fontweight="bold",
                    color="white",
                )
        for bar, val, bottom in zip(bars_no, no_vals, yes_vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom + val / 2,
                    f"{int(val):,}",
                    ha="center",
                    va="center",
                    fontsize=DATA_LABEL_SIZE - 2,
                    fontweight="bold",
                    color="white",
                )

        # % with Debit annotation above each bar
        if "% with Debit" in data.columns:
            totals = yes_vals + no_vals
            for xi, total, pct in zip(x, totals, data["% with Debit"]):
                ax.text(
                    xi,
                    total,
                    f" {pct:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=DATA_LABEL_SIZE - 1,
                    fontweight="bold",
                    color=NAVY,
                )

        ax.set_xticks(x)
        ax.set_xticklabels(data["Prod Code"])
        ax.set_xlabel("Product Code")
        ax.set_ylabel("Count")
        ax.set_title("Debit Distribution by Product Code")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_debit_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar of Debit rate by Branch."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy()
        if "% with Debit" not in data.columns:
            data["% with Debit"] = 0
        data = data.sort_values("% with Debit", ascending=True)

        n = len(data)
        rates = data["% with Debit"]
        med = rates.median()
        colors = [ACQUISITION if r >= med else NAVY for r in rates]

        bars = ax.barh(
            range(n),
            rates,
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Branch"].astype(str))

        for bar, val in zip(bars, rates):
            label = f"{val:.1f}%" if isinstance(val, (int, float)) else str(val)
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                f"  {label}",
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )

        ax.set_xlabel("% with Debit Card")
        ax.set_title("Debit Rate by Branch")
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_penetration_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar chart of ICS penetration rate by branch."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df
        data["Penetration %"] = pd.to_numeric(data["Penetration %"], errors="coerce")
        data = data.sort_values("Penetration %", ascending=True)

        n = len(data)
        med = data["Penetration %"].median()
        colors = [TEAL if r >= med else NAVY for r in data["Penetration %"]]

        bars = ax.barh(
            range(n),
            data["Penetration %"],
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            height=0.65,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(data["Branch"].astype(str))

        for bar, val in zip(bars, data["Penetration %"]):
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                f"  {val:.1f}%",
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )

        # Median line
        ax.axvline(med, color="#E74C3C", linestyle="--", linewidth=1.5, alpha=0.6)
        ax.text(med, n - 0.5, f" Median: {med:.1f}%", fontsize=12, color="#E74C3C", va="bottom")

        ax.set_xlabel("ICS Penetration Rate (%)")
        ax.set_title("ICS Penetration by Branch")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
