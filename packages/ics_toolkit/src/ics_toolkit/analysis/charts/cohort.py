"""Charts for cohort analyses (ax27-ax36)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_cohort_activation(df, config: ChartConfig) -> go.Figure:
    """ax27: Grouped bar of M1/M3/M6/M12 activation rates by cohort."""
    colors = config.colors

    fig = go.Figure()

    milestones = ["M1", "M3", "M6", "M12"]
    for i, m in enumerate(milestones):
        col = f"{m} Activation %"
        if col not in df.columns:
            continue

        numeric_vals = pd.to_numeric(df[col], errors="coerce")

        fig.add_trace(
            go.Bar(
                x=df["Opening Month"],
                y=numeric_vals,
                name=m,
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Opening Month",
        yaxis_title="Activation Rate",
        yaxis=dict(tickformat=".0%"),
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_cohort_heatmap(df, config: ChartConfig) -> go.Figure:
    """ax28: Heatmap of total swipes per month per cohort."""
    month_cols = [c for c in df.columns if c != "Opening Month"]

    if not month_cols:
        fig = go.Figure()
        fig.add_annotation(text="No monthly data available", showarrow=False)
        return fig

    z_data = df[month_cols].apply(pd.to_numeric, errors="coerce").values

    # Text annotations: show count where data exists, blank where NaN
    nan_mask = np.isnan(z_data)
    int_vals = np.nan_to_num(z_data, nan=0).astype(int).astype(str)
    text_arr = np.where(nan_mask, "", int_vals)

    fig = go.Figure(
        go.Heatmap(
            z=z_data,
            x=month_cols,
            y=df["Opening Month"].tolist(),
            colorscale="Blues",
            text=text_arr,
            texttemplate="%{text}",
            textfont=dict(size=12),
        )
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Month",
        yaxis_title="Opening Month",
        yaxis=dict(autorange="reversed"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_cohort_milestones(df, config: ChartConfig) -> go.Figure:
    """ax29: Grouped bar of avg swipes at M1/M3/M6/M12 by cohort."""
    colors = config.colors

    fig = go.Figure()
    milestones = ["M1", "M3", "M6", "M12"]
    for i, m in enumerate(milestones):
        col = f"{m} Avg Swipes"
        if col not in df.columns:
            continue
        numeric_vals = pd.to_numeric(df[col], errors="coerce")
        fig.add_trace(
            go.Bar(
                x=df["Opening Month"],
                y=numeric_vals,
                name=m,
                marker_color=colors[i % len(colors)],
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Opening Month",
        yaxis_title="Avg Swipes",
        xaxis=dict(tickangle=-45),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_activation_summary(df, config: ChartConfig) -> go.Figure:
    """ax31: Bar chart of aggregate activation rates (M1, M3, M6, M12)."""
    colors = config.colors

    milestones = []
    rates = []
    for _, row in df.iterrows():
        metric = str(row["Metric"])
        value = row["Value"]
        if "Activation Rate" in metric and pd.notna(value):
            label = metric.replace(" Activation Rate", "")
            milestones.append(label)
            rates.append(float(value) / 100.0)

    fig = go.Figure(
        go.Bar(
            x=milestones,
            y=rates,
            marker_color=colors[: len(milestones)],
            text=[f"{r:.1%}" for r in rates],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Milestone",
        yaxis_title="Activation Rate",
        yaxis=dict(tickformat=".0%"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_growth_patterns(df, config: ChartConfig) -> go.Figure:
    """ax32: Line chart of swipe trajectories across milestones by cohort."""
    colors = config.colors

    fig = go.Figure()
    milestones = ["M1", "M3", "M6", "M12"]

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
            fig.add_trace(
                go.Scatter(
                    x=x_labels,
                    y=vals,
                    name=str(cohort),
                    mode="lines+markers",
                    line=dict(color=colors[i % len(colors)]),
                )
            )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Milestone",
        yaxis_title="Total Swipes",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_activation_personas(df, config: ChartConfig) -> go.Figure:
    """ax34: Pie chart of activation persona distribution."""
    colors = config.colors

    fig = go.Figure(
        go.Pie(
            labels=df["Category"],
            values=df["Account Count"],
            marker=dict(colors=colors[: len(df)]),
            textinfo="label+percent+value",
            hole=0.35,
        )
    )

    fig.update_layout(template=config.theme, **LAYOUT_DEFAULTS)
    return fig


def chart_branch_activation(df, config: ChartConfig) -> go.Figure:
    """ax36: Horizontal bar of branch activation rates."""
    data = df[df["Branch"] != "Total"].copy()
    colors = config.colors

    if "Activation Rate" not in data.columns:
        data["Activation Rate"] = 0

    data = data.sort_values("Activation Rate", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=data["Branch"].astype(str),
            x=pd.to_numeric(data["Activation Rate"], errors="coerce"),
            orientation="h",
            marker_color=colors[2],
            text=data["Activation Rate"].apply(
                lambda v: f"{v:.1%}" if isinstance(v, (int, float)) else str(v)
            ),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Activation Rate",
        xaxis=dict(tickformat=".0%"),
        yaxis_title="Branch",
        **LAYOUT_DEFAULTS,
    )
    return fig
