"""Synthetic chart generators for RPE sales conference deck.

Each function generates an illustrative chart with synthetic data and returns
the Path to the saved PNG. No real client data is used.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from ars_analysis.charts.guards import chart_figure

# ---------------------------------------------------------------------------
# RPE lifecycle colors (consistent across all sales deck visuals)
# ---------------------------------------------------------------------------
ICS_COLOR = "#048A81"       # Teal
ENGAGE_COLOR = "#005EB8"    # Blue
ARS_COLOR = "#2E4057"       # Navy
MRPC_COLOR = "#F18F01"      # Gold
NEUTRAL = "#8B95A2"
LIGHT_BG = "#F7F9FC"

_LIFECYCLE_COLORS = [ICS_COLOR, ENGAGE_COLOR, ARS_COLOR, MRPC_COLOR]
_LIFECYCLE_LABELS = ["ICS", "Account\nEngagement", "ARS", "MRPC"]
_LIFECYCLE_SUBTITLES = [
    "Acquisition",
    "Early Engagement",
    "Ongoing Engagement",
    "Premium",
]


def lifecycle_diagram(output_dir: Path) -> Path:
    """4-stage horizontal lifecycle flow (ICS -> Engagement -> ARS -> MRPC)."""
    out = output_dir / "lifecycle_diagram.png"
    with chart_figure(figsize=(14, 5), save_path=out) as (fig, ax):
        ax.set_xlim(0, 14)
        ax.set_ylim(0, 5)
        ax.axis("off")

        box_w, box_h = 2.8, 2.4
        gap = 0.5
        start_x = 0.6
        y_center = 2.5

        for i, (label, subtitle, color) in enumerate(
            zip(_LIFECYCLE_LABELS, _LIFECYCLE_SUBTITLES, _LIFECYCLE_COLORS)
        ):
            x = start_x + i * (box_w + gap)
            rect = mpatches.FancyBboxPatch(
                (x, y_center - box_h / 2),
                box_w,
                box_h,
                boxstyle="round,pad=0.15",
                facecolor=color,
                edgecolor="none",
                alpha=0.95,
            )
            ax.add_patch(rect)

            ax.text(
                x + box_w / 2,
                y_center + 0.3,
                label,
                ha="center",
                va="center",
                fontsize=18,
                fontweight="bold",
                color="white",
            )
            ax.text(
                x + box_w / 2,
                y_center - 0.55,
                subtitle,
                ha="center",
                va="center",
                fontsize=12,
                color="white",
                alpha=0.85,
            )

            # Arrow between boxes
            if i < 3:
                arrow_x = x + box_w + 0.05
                ax.annotate(
                    "",
                    xy=(arrow_x + gap - 0.1, y_center),
                    xytext=(arrow_x, y_center),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        color="#555555",
                        lw=2.5,
                        mutation_scale=20,
                    ),
                )

        # Stage numbers
        for i in range(4):
            x = start_x + i * (box_w + gap) + box_w / 2
            ax.text(
                x,
                y_center - box_h / 2 - 0.35,
                f"Stage {i + 1}",
                ha="center",
                va="top",
                fontsize=11,
                color="#666666",
            )

    return out


def ics_source_chart(output_dir: Path) -> Path:
    """Horizontal bar: acquisition sources (referral, direct mail, branch)."""
    out = output_dir / "ics_source.png"
    sources = ["Branch Referral", "Direct Mail", "Digital / Online", "Staff Referral", "Other"]
    values = [38, 27, 18, 12, 5]
    colors = [ICS_COLOR, "#06B49A", "#07D1B5", "#09E8CC", NEUTRAL]

    with chart_figure(figsize=(12, 6), save_path=out) as (fig, ax):
        bars = ax.barh(sources[::-1], values[::-1], color=colors[::-1], height=0.6)
        for bar, val in zip(bars, values[::-1]):
            ax.text(
                bar.get_width() + 0.8,
                bar.get_y() + bar.get_height() / 2,
                f"{val}%",
                va="center",
                fontsize=16,
                fontweight="bold",
                color=ARS_COLOR,
            )
        ax.set_xlim(0, 50)
        ax.set_xlabel("")
        ax.set_title("New Account Acquisition by Source", fontsize=22, pad=15)
        ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)

    return out


def service_adoption_chart(output_dir: Path) -> Path:
    """Stacked bar: service adoption at 30/60/90 days."""
    out = output_dir / "service_adoption.png"
    services = ["eStatements", "Online Banking", "Direct Deposit", "Bill Pay", "Mobile Banking"]
    day30 = [62, 55, 38, 22, 48]
    day60 = [14, 18, 20, 15, 17]
    day90 = [8, 10, 15, 12, 13]

    x = np.arange(len(services))
    width = 0.55

    with chart_figure(figsize=(12, 7), save_path=out) as (fig, ax):
        b1 = ax.bar(x, day30, width, label="Within 30 days", color=ENGAGE_COLOR)
        b2 = ax.bar(x, day60, width, bottom=day30, label="30-60 days", color="#3380C8")
        b3 = ax.bar(
            x,
            day90,
            width,
            bottom=[a + b for a, b in zip(day30, day60)],
            label="60-90 days",
            color="#66A3D8",
        )

        ax.set_xticks(x)
        ax.set_xticklabels(services, fontsize=14)
        ax.set_ylabel("% of New Members", fontsize=14)
        ax.set_title("Service Adoption Within First 90 Days", fontsize=22, pad=15)
        ax.set_ylim(0, 100)
        ax.legend(fontsize=13, loc="upper right")

        # Annotate totals
        for i, total in enumerate([a + b + c for a, b, c in zip(day30, day60, day90)]):
            ax.text(i, total + 1.5, f"{total}%", ha="center", fontsize=14, fontweight="bold")

    return out


def swipe_ladder_chart(output_dir: Path) -> Path:
    """Tier distribution with movement arrows (NU 1-4 through TH-25)."""
    out = output_dir / "swipe_ladder.png"
    tiers = ["NU 1-4", "NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"]
    counts = [1200, 3400, 4800, 3200, 2100, 800]
    movements = [None, +320, +450, +180, +120, +60]  # net movement into tier

    with chart_figure(figsize=(12, 7), save_path=out) as (fig, ax):
        # Gradient from light to dark navy
        tier_colors = ["#B0BEC5", ARS_COLOR, "#3A5068", "#466079", "#52708A", "#5E809B"]
        bars = ax.barh(tiers[::-1], counts[::-1], color=tier_colors[::-1], height=0.6)

        for i, (bar, count) in enumerate(zip(bars, counts[::-1])):
            ax.text(
                bar.get_width() + 80,
                bar.get_y() + bar.get_height() / 2,
                f"{count:,}",
                va="center",
                fontsize=14,
                fontweight="bold",
                color=ARS_COLOR,
            )

        # Movement annotations on the right
        for i, (tier, mv) in enumerate(zip(tiers[::-1], movements[::-1])):
            if mv is not None and mv != 0:
                y = i
                color = "#2D936C" if mv > 0 else "#C73E1D"
                arrow = "\u2191" if mv > 0 else "\u2193"
                ax.text(
                    max(counts) + 800,
                    y,
                    f"{arrow} {abs(mv):,}",
                    va="center",
                    fontsize=13,
                    color=color,
                    fontweight="bold",
                )

        ax.set_xlim(0, max(counts) * 1.35)
        ax.set_title("The Swipe Ladder -- Member Distribution & Movement", fontsize=22, pad=15)
        ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)

        # Legend
        ax.text(
            max(counts) * 0.75,
            -0.8,
            "\u2191 = Members moving UP    \u2193 = Members moving DOWN",
            fontsize=12,
            color="#666666",
            ha="center",
        )

    return out


def competition_chart(output_dir: Path) -> Path:
    """6-category competition breakdown (local vs national)."""
    out = output_dir / "competition.png"
    categories = [
        "Big National Banks",
        "Regional Banks",
        "Other Credit Unions",
        "Digital / Neobanks",
        "Wallets & P2P",
        "BNPL / Alt Finance",
    ]
    local = [8, 15, 12, 3, 2, 1]
    national = [22, 5, 3, 8, 6, 4]

    x = np.arange(len(categories))
    width = 0.35

    with chart_figure(figsize=(14, 7), save_path=out) as (fig, ax):
        ax.barh(x + width / 2, national[::-1], width, label="National", color=ARS_COLOR)
        ax.barh(x - width / 2, local[::-1], width, label="Local", color=ICS_COLOR)

        ax.set_yticks(x)
        ax.set_yticklabels(categories[::-1], fontsize=14)
        ax.set_xlabel("% of Competitive Spend", fontsize=14)
        ax.set_title(
            "Competitive Spend Share -- 38 Patterns Across 6 Categories",
            fontsize=20,
            pad=15,
        )
        ax.legend(fontsize=14, loc="lower right")
        ax.set_xlim(0, 30)

        # Annotate totals
        for i, (l, n) in enumerate(zip(local[::-1], national[::-1])):
            total = l + n
            ax.text(
                max(l, n) + 1,
                i,
                f"{total}%",
                va="center",
                fontsize=13,
                fontweight="bold",
                color=ARS_COLOR,
            )

    return out


def financial_services_chart(output_dir: Path) -> Path:
    """8-bucket financial services spend breakdown."""
    out = output_dir / "financial_services.png"
    buckets = [
        "Auto Loans",
        "Banks (Deposits)",
        "Business Loans",
        "Student Loans",
        "Credit Cards",
        "Mortgage / HELOC",
        "Treasury / Bonds",
        "Investment / Brokerage",
    ]
    pct = [18, 22, 5, 8, 25, 14, 3, 5]
    colors = [
        ARS_COLOR,
        ICS_COLOR,
        "#3A5068",
        ENGAGE_COLOR,
        MRPC_COLOR,
        "#2D936C",
        NEUTRAL,
        "#5B6770",
    ]

    with chart_figure(figsize=(14, 7), save_path=out) as (fig, ax):
        bars = ax.barh(buckets[::-1], pct[::-1], color=colors[::-1], height=0.6)
        for bar, val in zip(bars, pct[::-1]):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f"{val}%",
                va="center",
                fontsize=14,
                fontweight="bold",
                color=ARS_COLOR,
            )
        ax.set_xlim(0, 35)
        ax.set_title(
            "Where Members Go for Financial Services -- 8 Categories",
            fontsize=20,
            pad=15,
        )
        ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)

    return out


def lifecycle_kpi_dashboard(output_dir: Path) -> Path:
    """4-panel KPI dashboard, one per lifecycle product."""
    out = output_dir / "lifecycle_kpi.png"

    products = ["ICS", "Account\nEngagement", "ARS", "MRPC"]
    kpi_values = ["847", "72%", "34.2%", "$18.40"]
    kpi_labels = [
        "New accounts / month",
        "Activated in 30 days",
        "Penetration rate",
        "Revenue per account",
    ]
    colors = _LIFECYCLE_COLORS

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    fig.patch.set_facecolor("white")

    for i, ax in enumerate(axes):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Colored header bar
        rect = mpatches.FancyBboxPatch(
            (0.05, 0.7),
            0.9,
            0.25,
            boxstyle="round,pad=0.05",
            facecolor=colors[i],
            edgecolor="none",
        )
        ax.add_patch(rect)
        ax.text(
            0.5,
            0.825,
            products[i],
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="white",
        )

        # KPI value
        ax.text(
            0.5,
            0.45,
            kpi_values[i],
            ha="center",
            va="center",
            fontsize=32,
            fontweight="bold",
            color=colors[i],
        )

        # KPI label
        ax.text(
            0.5,
            0.15,
            kpi_labels[i],
            ha="center",
            va="center",
            fontsize=11,
            color="#666666",
        )

    fig.tight_layout(pad=1.5)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def mrpc_fallback_chart(output_dir: Path) -> Path:
    """Simple revenue comparison: MRPC vs non-MRPC (fallback if no user chart)."""
    out = output_dir / "mrpc_revenue.png"
    categories = ["MRPC\nCardholders", "Standard\nCardholders"]
    revenue = [18.40, 6.20]
    colors = [MRPC_COLOR, NEUTRAL]

    with chart_figure(figsize=(10, 7), save_path=out) as (fig, ax):
        bars = ax.bar(categories, revenue, color=colors, width=0.5)
        for bar, val in zip(bars, revenue):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"${val:.2f}",
                ha="center",
                fontsize=20,
                fontweight="bold",
                color=ARS_COLOR,
            )
        ax.set_ylabel("Revenue per Account / Month", fontsize=14)
        ax.set_title(
            "MRPC Cardholders Generate 3x More Revenue",
            fontsize=22,
            pad=15,
        )
        ax.set_ylim(0, 25)

    return out
