"""Charts for Persona Deep-Dive analyses (ax55-ax62)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

PERSONA_COLORS = {
    "Fast Activator": "#27AE60",
    "Slow Burner": "#1ABC9C",
    "One and Done": "#E67E22",
    "Never Activator": "#BDC3C7",
}
PERSONA_ORDER = ["Fast Activator", "Slow Burner", "One and Done", "Never Activator"]

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_persona_map(df, config: ChartConfig) -> go.Figure:
    """ax55: Bubble scatter quadrant -- M1 vs M3 swipes, sized by account count."""
    fig = go.Figure()

    for persona in PERSONA_ORDER:
        row = df[df["Persona"] == persona]
        if row.empty:
            continue
        r = row.iloc[0]
        count = int(r["Account Count"])
        if count == 0:
            continue

        fig.add_trace(
            go.Scatter(
                x=[float(r["Avg M1 Swipes"])],
                y=[float(r["Avg M3 Swipes"])],
                mode="markers+text",
                name=persona,
                marker=dict(
                    size=max(20, min(80, count // 5)),
                    color=PERSONA_COLORS.get(persona, "#999"),
                    opacity=0.8,
                ),
                text=[f"{persona}<br>{count} ({r['% of Total']:.1f}%)"],
                textposition="top center",
                textfont=dict(size=12),
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Avg M1 Swipes (Early Engagement)",
        yaxis_title="Avg M3 Swipes (Sustained Engagement)",
        xaxis=dict(rangemode="tozero"),
        yaxis=dict(rangemode="tozero"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_persona_contribution(df, config: ChartConfig) -> go.Figure:
    """ax56: Grouped horizontal bars -- % of Accounts vs % of L12M Swipes."""
    fig = go.Figure()

    personas = list(df["Persona"])
    colors = [PERSONA_COLORS.get(p, "#999") for p in personas]

    fig.add_trace(
        go.Bar(
            y=personas,
            x=df["% of Accounts"],
            name="% of Accounts",
            orientation="h",
            marker_color=colors,
            text=df["% of Accounts"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            y=personas,
            x=df["% of L12M Swipes"],
            name="% of L12M Swipes",
            orientation="h",
            marker_color=[
                f"rgba({int(c[1:3], 16)},{int(c[3:5], 16)},{int(c[5:7], 16)},0.6)" for c in colors
            ],
            text=df["% of L12M Swipes"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Percentage",
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(personas))),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_persona_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax57: Stacked 100% bar per branch, colored by persona."""
    data = df[df["Branch"] != "Total"].copy() if "Branch" in df.columns else df.copy()

    fig = go.Figure()

    for persona in PERSONA_ORDER:
        if persona not in data.columns:
            continue

        pct = data.apply(lambda r: (r[persona] / r["Total"] * 100) if r["Total"] > 0 else 0, axis=1)

        fig.add_trace(
            go.Bar(
                x=data.iloc[:, 0].astype(str),
                y=pct,
                name=persona,
                marker_color=PERSONA_COLORS.get(persona, "#999"),
                text=pct.apply(lambda v: f"{v:.0f}%"),
                textposition="inside",
                textfont=dict(size=11),
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="stack",
        xaxis_title=data.columns[0],
        yaxis_title="% of Accounts",
        yaxis=dict(range=[0, 105]),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_persona_by_source(df, config: ChartConfig) -> go.Figure:
    """ax58: Stacked 100% bar per source, colored by persona."""
    data = df[df["Source"] != "Total"].copy() if "Source" in df.columns else df.copy()

    fig = go.Figure()

    for persona in PERSONA_ORDER:
        if persona not in data.columns:
            continue

        pct = data.apply(lambda r: (r[persona] / r["Total"] * 100) if r["Total"] > 0 else 0, axis=1)

        fig.add_trace(
            go.Bar(
                x=data.iloc[:, 0].astype(str),
                y=pct,
                name=persona,
                marker_color=PERSONA_COLORS.get(persona, "#999"),
                text=pct.apply(lambda v: f"{v:.0f}%"),
                textposition="inside",
                textfont=dict(size=11),
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="stack",
        xaxis_title="Source",
        yaxis_title="% of Accounts",
        yaxis=dict(range=[0, 105]),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_persona_revenue(df, config: ChartConfig) -> go.Figure:
    """ax59: Horizontal bar of interchange by persona."""
    # Extract persona-level interchange rows from KPI table
    revenue_rows = df[df["Metric"].str.contains("Interchange", na=False)].copy()

    if revenue_rows.empty:
        return go.Figure()

    labels = list(revenue_rows["Metric"])
    values = pd.to_numeric(revenue_rows["Value"], errors="coerce").fillna(0)

    # Map colors based on metric names
    colors = []
    for label in labels:
        if "Fast" in label:
            colors.append(PERSONA_COLORS["Fast Activator"])
        elif "Slow" in label:
            colors.append(PERSONA_COLORS["Slow Burner"])
        else:
            colors.append("#1B365D")

    fig = go.Figure(
        go.Bar(
            y=labels,
            x=values,
            orientation="h",
            marker_color=colors,
            text=values.apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Estimated Interchange ($)",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_persona_cohort_trend(df, config: ChartConfig) -> go.Figure:
    """ax62: Stacked area of persona % over cohorts."""
    fig = go.Figure()

    for persona in reversed(PERSONA_ORDER):
        col = f"{persona} %"
        if col not in df.columns:
            continue

        fig.add_trace(
            go.Scatter(
                x=df["Opening Month"].astype(str),
                y=pd.to_numeric(df[col], errors="coerce").fillna(0),
                name=persona,
                mode="lines",
                stackgroup="one",
                line=dict(width=0.5),
                fillcolor=PERSONA_COLORS.get(persona, "#999"),
                marker=dict(color=PERSONA_COLORS.get(persona, "#999")),
            )
        )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Opening Month",
        yaxis_title="% of Cohort",
        yaxis=dict(range=[0, 100]),
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig
