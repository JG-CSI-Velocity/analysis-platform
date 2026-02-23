"""Charts for Persona Deep-Dive analyses -- behavioral segmentation."""

from io import BytesIO

import numpy as np
import pandas as pd

from ics_toolkit.analysis.charts.guards import chart_figure
from ics_toolkit.analysis.charts.style import (
    BAR_EDGE,
    BAR_EDGE_WIDTH,
    DATA_LABEL_SIZE,
    DOLLAR_FORMATTER,
    NAVY,
    PERSONA_COLORS,
    PERSONA_ORDER,
)
from ics_toolkit.settings import ChartConfig


def chart_persona_map(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Bubble scatter quadrant -- M1 vs M3 swipes, sized by account count."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 10), save_path=buf) as (_fig, ax):
        for persona in PERSONA_ORDER:
            row = df[df["Persona"] == persona]
            if row.empty:
                continue
            r = row.iloc[0]
            count = int(r["Account Count"])
            if count == 0:
                continue

            size = max(150, min(2000, count * 3))
            color = PERSONA_COLORS.get(persona, "#999")

            ax.scatter(
                float(r["Avg M1 Swipes"]),
                float(r["Avg M3 Swipes"]),
                s=size,
                c=color,
                alpha=0.7,
                edgecolors="white",
                linewidth=1.5,
                label=f"{persona} ({count:,})",
                zorder=5,
            )
            ax.annotate(
                persona,
                (float(r["Avg M1 Swipes"]), float(r["Avg M3 Swipes"])),
                textcoords="offset points",
                xytext=(0, 15),
                fontsize=12,
                fontweight="bold",
                color=color,
                ha="center",
            )

        ax.set_xlabel("Avg M1 Swipes (Early Engagement)")
        ax.set_ylabel("Avg M3 Swipes (Sustained Engagement)")
        ax.set_title("Activation Persona Map")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.legend(loc="upper left", fontsize=12, frameon=True)
        ax.grid(alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_persona_contribution(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Grouped horizontal bars -- % of Accounts vs % of L12M Swipes."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        personas = list(df["Persona"])
        colors = [PERSONA_COLORS.get(p, "#999") for p in personas]
        y = np.arange(len(personas))
        height = 0.35

        ax.barh(
            y - height / 2,
            df["% of Accounts"],
            height,
            label="% of Accounts",
            color=colors,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
        )

        # Lighter version for swipes
        ax.barh(
            y + height / 2,
            df["% of L12M Swipes"],
            height,
            label="% of L12M Swipes",
            color=colors,
            alpha=0.5,
            edgecolor=BAR_EDGE,
            linewidth=BAR_EDGE_WIDTH,
        )

        # Data labels
        for yi, (acct, swipe) in enumerate(zip(df["% of Accounts"], df["% of L12M Swipes"])):
            ax.text(
                acct,
                yi - height / 2,
                f" {acct:.1f}%",
                va="center",
                fontsize=DATA_LABEL_SIZE - 3,
                fontweight="bold",
            )
            ax.text(
                swipe,
                yi + height / 2,
                f" {swipe:.1f}%",
                va="center",
                fontsize=DATA_LABEL_SIZE - 3,
                fontweight="bold",
                alpha=0.8,
            )

        ax.set_yticks(y)
        ax.set_yticklabels(list(reversed(personas)))
        ax.invert_yaxis()
        ax.set_xlabel("Percentage")
        ax.set_title("Persona Contribution: Accounts vs Swipes")
        ax.legend(loc="lower right", fontsize=13)
        ax.grid(axis="x", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_persona_by_branch(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked 100% bar per branch, colored by persona."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df.copy()
        branches = data.iloc[:, 0].astype(str)
        x = np.arange(len(data))
        bottom = np.zeros(len(data))

        for persona in PERSONA_ORDER:
            if persona not in data.columns:
                continue
            total = data.get("Total", 1)
            pct = data.apply(
                lambda r: (r[persona] / r["Total"] * 100) if r["Total"] > 0 else 0, axis=1
            )
            color = PERSONA_COLORS.get(persona, "#999")
            ax.bar(
                x,
                pct,
                bottom=bottom,
                label=persona,
                color=color,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                width=0.6,
            )
            bottom += pct.values

        ax.set_xticks(x)
        ax.set_xticklabels(list(branches), rotation=45, ha="right")
        ax.set_xlabel(data.columns[0])
        ax.set_ylabel("% of Accounts")
        ax.set_title("Persona Mix by Branch")
        ax.set_ylim(0, 105)
        ax.legend(loc="upper right", fontsize=12)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_persona_by_source(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked 100% bar per source, colored by persona."""
    buf = BytesIO()
    with chart_figure(figsize=(12, 8), save_path=buf) as (_fig, ax):
        data = df[df["Source"] != "Total"].copy() if "Source" in df.columns else df.copy()
        sources = data.iloc[:, 0].astype(str)
        x = np.arange(len(data))
        bottom = np.zeros(len(data))

        for persona in PERSONA_ORDER:
            if persona not in data.columns:
                continue
            pct = data.apply(
                lambda r: (r[persona] / r["Total"] * 100) if r["Total"] > 0 else 0, axis=1
            )
            color = PERSONA_COLORS.get(persona, "#999")
            ax.bar(
                x,
                pct,
                bottom=bottom,
                label=persona,
                color=color,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                width=0.5,
            )
            bottom += pct.values

        ax.set_xticks(x)
        ax.set_xticklabels(list(sources))
        ax.set_xlabel("Source")
        ax.set_ylabel("% of Accounts")
        ax.set_title("Persona Mix by Source")
        ax.set_ylim(0, 105)
        ax.legend(loc="upper right", fontsize=12)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_persona_revenue(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Horizontal bar of interchange by persona."""
    buf = BytesIO()
    with chart_figure(figsize=(14, 8), save_path=buf) as (_fig, ax):
        revenue_rows = df[df["Metric"].str.contains("Interchange", na=False)].copy()
        if revenue_rows.empty:
            ax.text(
                0.5,
                0.5,
                "No revenue data",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=18,
            )
        else:
            labels = list(revenue_rows["Metric"])
            values = pd.to_numeric(revenue_rows["Value"], errors="coerce").fillna(0)

            colors = []
            for label in labels:
                if "Fast" in label:
                    colors.append(PERSONA_COLORS["Fast Activator"])
                elif "Slow" in label:
                    colors.append(PERSONA_COLORS["Slow Burner"])
                else:
                    colors.append(NAVY)

            bars = ax.barh(
                range(len(labels)),
                values,
                color=colors,
                edgecolor=BAR_EDGE,
                linewidth=BAR_EDGE_WIDTH,
                height=0.55,
            )
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels)

            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_width(),
                    bar.get_y() + bar.get_height() / 2,
                    f"  ${val:,.0f}",
                    va="center",
                    ha="left",
                    fontsize=DATA_LABEL_SIZE - 2,
                    fontweight="bold",
                )

            ax.set_xlabel("Estimated Interchange ($)")
            ax.set_title("Persona Revenue Impact")
            ax.xaxis.set_major_formatter(DOLLAR_FORMATTER)
            ax.grid(axis="x", alpha=0.15, linestyle="--")
            ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()


def chart_persona_cohort_trend(df: pd.DataFrame, config: ChartConfig) -> bytes:
    """Stacked area of persona % over cohorts."""
    buf = BytesIO()
    with chart_figure(figsize=(16, 8), save_path=buf) as (_fig, ax):
        months = df["Opening Month"].astype(str)
        x = range(len(months))

        # Build stacked data
        ys = []
        labels_used = []
        colors_used = []
        for persona in PERSONA_ORDER:
            col = f"{persona} %"
            if col not in df.columns:
                continue
            vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
            ys.append(vals.values)
            labels_used.append(persona)
            colors_used.append(PERSONA_COLORS.get(persona, "#999"))

        if ys:
            ax.stackplot(list(x), *ys, labels=labels_used, colors=colors_used, alpha=0.85)

        ax.set_xticks(list(x))
        ax.set_xticklabels(list(months), rotation=45, ha="right")
        ax.set_xlabel("Opening Month")
        ax.set_ylabel("% of Cohort")
        ax.set_title("Persona Distribution Over Time")
        ax.set_ylim(0, 100)
        ax.legend(loc="upper right", fontsize=12)
        ax.grid(axis="y", alpha=0.15, linestyle="--")
        ax.set_axisbelow(True)

    buf.seek(0)
    return buf.read()
