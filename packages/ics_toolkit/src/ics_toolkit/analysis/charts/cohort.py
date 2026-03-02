"""Charts for cohort analyses -- activation, heatmap, milestones, growth."""

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
    LINE_WIDTH,
    MARKER_SIZE,
    NAVY,
    PALETTE,
    PERSONA_COLORS,
    TEAL,
)
from ics_toolkit.settings import ChartConfig


def chart_cohort_activation(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of M1/M3/M6/M12 activation rates by cohort."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        milestones = ["M1", "M3", "M6", "M12"]
        colors = [NAVY, TEAL, ACQUISITION, "#F39C12"]
        x = np.arange(len(df))
        n_bars = sum(1 for m in milestones if f"{m} Activation %" in df.columns)
        width = 0.7 / max(n_bars, 1)

        bar_idx = 0
        for m, color in zip(milestones, colors):
            col = f"{m} Activation %"
            if col not in df.columns:
                continue
            vals = pd.to_numeric(df[col], errors="coerce")
            offset = (bar_idx - n_bars / 2 + 0.5) * width
            ax.bar(
                x + offset,
                vals,
                width,
                label=m,
                color=color,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
            )
            bar_idx += 1

        ax.set_xticks(x)
        ax.set_xticklabels(list(df["Opening Month"]), rotation=45, ha="right")
        ax.set_xlabel("Opening Month")
        ax.set_ylabel("Activation Rate")
        ax.set_title("Cohort Activation Rates")
        ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_cohort_heatmap(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Heatmap of total swipes per month per cohort."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 10), save_path=buf) as (fig, ax):
        month_cols = [c for c in df.columns if c != "Opening Month"]
        if not month_cols:
            ax.text(
                0.5,
                0.5,
                "No monthly data available",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=18,
            )
        else:
            z_data = df[month_cols].apply(pd.to_numeric, errors="coerce").values
            z_masked = np.ma.masked_invalid(z_data)

            im = ax.imshow(z_masked, aspect="auto", cmap="YlGnBu", interpolation="nearest")
            cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
            cbar.ax.tick_params(labelsize=12)
            cbar.set_label("Swipes", fontsize=14)

            ax.set_xticks(range(len(month_cols)))
            ax.set_xticklabels(month_cols, rotation=45, ha="right", fontsize=11)
            ax.set_yticks(range(len(df)))
            ax.set_yticklabels(df["Opening Month"].tolist(), fontsize=11)

            # Text annotations
            z_max = np.nanmax(z_data) if np.any(~np.isnan(z_data)) else 1
            for row_i in range(z_data.shape[0]):
                for col_i in range(z_data.shape[1]):
                    val = z_data[row_i, col_i]
                    if np.isnan(val):
                        continue
                    text_color = "white" if val > z_max * 0.55 else "#333"
                    ax.text(
                        col_i,
                        row_i,
                        f"{int(val):,}",
                        ha="center",
                        va="center",
                        fontsize=10,
                        color=text_color,
                        fontweight="bold",
                    )

            ax.set_xlabel("Month")
            ax.set_ylabel("Opening Month (Cohort)")
            ax.set_title("Cohort Engagement Heatmap")

    buf.seek(0)
    return buf.read()


def chart_cohort_milestones(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped bar of avg swipes at M1/M3/M6/M12 by cohort."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        milestones = ["M1", "M3", "M6", "M12"]
        colors = [NAVY, TEAL, ACQUISITION, "#F39C12"]
        x = np.arange(len(df))
        n_bars = sum(1 for m in milestones if f"{m} Avg Swipes" in df.columns)
        width = 0.7 / max(n_bars, 1)

        bar_idx = 0
        for m, color in zip(milestones, colors):
            col = f"{m} Avg Swipes"
            if col not in df.columns:
                continue
            vals = pd.to_numeric(df[col], errors="coerce")
            offset = (bar_idx - n_bars / 2 + 0.5) * width
            ax.bar(
                x + offset,
                vals,
                width,
                label=m,
                color=color,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                alpha=BAR_ALPHA,
            )
            bar_idx += 1

        ax.set_xticks(x)
        ax.set_xticklabels(list(df["Opening Month"]), rotation=45, ha="right")
        ax.set_xlabel("Opening Month")
        ax.set_ylabel("Avg Swipes")
        ax.set_title("Cohort Milestones: Avg Swipes")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_activation_summary(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bar chart of aggregate activation rates (M1, M3, M6, M12)."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 8), save_path=buf) as (_fig, ax):
        milestones = []
        rates = []
        for _, row in df.iterrows():
            metric = str(row["Metric"])
            value = row["Value"]
            if "Activation Rate" in metric and pd.notna(value):
                label = metric.replace(" Activation Rate", "")
                milestones.append(label)
                rates.append(float(value) / 100.0)

        colors = [NAVY, TEAL, ACQUISITION, "#F39C12"][: len(milestones)]
        bars = ax.bar(
            milestones,
            rates,
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
            alpha=BAR_ALPHA,
            width=0.5,
        )

        for bar, rate in zip(bars, rates):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{rate:.1%}",
                ha="center",
                va="bottom",
                fontsize=DATA_LABEL_SIZE + 2,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_xlabel("Milestone")
        ax.set_ylabel("Activation Rate")
        ax.set_title("Overall Activation Summary")
        ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
        ax.set_ylim(0, max(rates) * 1.2 if rates else 1)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_growth_patterns(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Line chart of swipe trajectories across milestones by cohort."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        milestones = ["M1", "M3", "M6", "M12"]
        markers = ["o", "s", "D", "^", "v", "P", "*", "X"]

        for i, (_, row) in enumerate(df.iterrows()):
            cohort = row["Opening Month"]
            vals = []
            x_labels = []
            for m in milestones:
                col = f"{m} Swipes"
                if col in df.columns and pd.notna(row[col]):
                    vals.append(pd.to_numeric(row[col], errors="coerce"))
                    x_labels.append(m)

            if vals:
                ax.plot(
                    x_labels,
                    vals,
                    label=str(cohort),
                    marker=markers[i % len(markers)],
                    markersize=MARKER_SIZE,
                    linewidth=LINE_WIDTH,
                    color=PALETTE[i % len(PALETTE)],
                )

        ax.set_xlabel("Milestone")
        ax.set_ylabel("Total Swipes")
        ax.set_title("Cohort Growth Patterns")
        ax.legend(loc="upper left", fontsize=11, ncol=2)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_activation_personas(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Donut chart of activation persona distribution."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 7), save_path=buf) as (_fig, ax):
        colors = [
            PERSONA_COLORS.get(cat, PALETTE[i % len(PALETTE)])
            for i, cat in enumerate(df["Category"])
        ]

        wedges, _, autotexts = ax.pie(
            df["Account Count"],
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%" if pct > 3 else "",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )

        # Center hole for donut
        ax.add_patch(
            __import__("matplotlib.patches", fromlist=["Circle"]).Circle((0, 0), 0.35, fc="white")
        )

        for t in autotexts:
            t.set_fontsize(13)
            t.set_fontweight("bold")

        # Legend with counts
        legend_labels = [
            f"{cat}  ({count:,})" for cat, count in zip(df["Category"], df["Account Count"])
        ]
        ax.legend(
            wedges,
            legend_labels,
            loc="center right",
            fontsize=12,
            frameon=False,
        )

        ax.set_title("Activation Personas", fontsize=22, fontweight="bold", pad=20)
        ax.set_aspect("equal")

    buf.seek(0)
    return buf.read()


def chart_branch_activation(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar of branch activation rates."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 9), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy()
        if "Activation Rate" not in data.columns:
            data["Activation Rate"] = 0
        data = data.sort_values("Activation Rate", ascending=True)

        rates = pd.to_numeric(data["Activation Rate"], errors="coerce")
        n = len(data)
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
            label = f"{val:.1%}" if isinstance(val, float) else str(val)
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                f"  {label}",
                va="center",
                ha="left",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )

        # Median reference line
        ax.axvline(med, color="#E74C3C", linestyle="--", linewidth=1.5, alpha=0.6)
        ax.text(med, n - 0.5, f" Median: {med:.1%}", fontsize=12, color="#E74C3C", va="bottom")

        ax.set_xlabel("Activation Rate")
        ax.set_title("Branch Activation Rates")
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
