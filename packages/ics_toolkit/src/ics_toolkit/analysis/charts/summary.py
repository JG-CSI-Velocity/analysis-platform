"""Charts for summary analyses (ax01-ax07)."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_total_ics(df, config: ChartConfig) -> go.Figure:
    """ax01: Pie chart of ICS vs Non-ICS accounts."""
    data = df[df["Category"] != "Total Accounts"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Pie(
            labels=data["Category"],
            values=data["Count"],
            marker=dict(colors=colors[: len(data)]),
            textinfo="label+percent+value",
            hole=0.35,
        )
    )

    fig.update_layout(template=config.theme, **LAYOUT_DEFAULTS)
    return fig


def chart_stat_code(df, config: ChartConfig) -> go.Figure:
    """ax03: Bar chart of ICS accounts by Stat Code."""
    data = df[df["Stat Code"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=data["Stat Code"],
            y=data["Count"],
            marker_color=colors[0],
            text=data["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Stat Code",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_prod_code(df, config: ChartConfig) -> go.Figure:
    """ax04: Horizontal bar of ICS accounts by Product Code."""
    data = df[df["Prod Code"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            y=data["Prod Code"],
            x=data["Account Count"],
            orientation="h",
            marker_color=colors[1],
            text=data["Account Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Account Count",
        yaxis_title="Product Code",
        yaxis=dict(autorange="reversed"),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_debit_dist(df, config: ChartConfig) -> go.Figure:
    """ax05: Pie chart of Debit Card distribution."""
    data = df[df["Debit?"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Pie(
            labels=data["Debit?"],
            values=data["Count"],
            marker=dict(colors=[colors[2], colors[4]]),
            textinfo="label+percent+value",
            hole=0.35,
        )
    )

    fig.update_layout(template=config.theme, **LAYOUT_DEFAULTS)
    return fig


def chart_debit_by_prod(df, config: ChartConfig) -> go.Figure:
    """ax06: Grouped bar of Debit by Product Code."""
    data = df[df["Prod Code"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure()

    if "Yes" in data.columns:
        fig.add_trace(
            go.Bar(
                x=data["Prod Code"],
                y=data["Yes"],
                name="Debit Yes",
                marker_color=colors[2],
            )
        )

    if "No" in data.columns:
        fig.add_trace(
            go.Bar(
                x=data["Prod Code"],
                y=data["No"],
                name="Debit No",
                marker_color=colors[4],
            )
        )

    if "% with Debit" in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data["Prod Code"],
                y=data["% with Debit"],
                name="% with Debit",
                mode="lines+markers",
                marker=dict(color=colors[3], size=8),
                line=dict(color=colors[3], width=2),
                yaxis="y2",
            )
        )

    fig.update_layout(
        template=config.theme,
        barmode="group",
        xaxis_title="Product Code",
        yaxis=dict(title="Count", side="left"),
        yaxis2=dict(
            title="% with Debit",
            side="right",
            overlaying="y",
            range=[0, 1.1],
            tickformat=".0%",
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_debit_by_branch(df, config: ChartConfig) -> go.Figure:
    """ax07: Horizontal bar of Debit rate by Branch."""
    data = df[df["Branch"] != "Total"].copy()
    colors = config.colors

    if "% with Debit" not in data.columns:
        data["% with Debit"] = 0

    data = data.sort_values("% with Debit", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=data["Branch"].astype(str),
            x=data["% with Debit"],
            orientation="h",
            marker_color=colors[1],
            text=data["% with Debit"].apply(
                lambda v: f"{v:.1%}" if isinstance(v, float) else str(v)
            ),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="% with Debit Card",
        xaxis=dict(tickformat=".0%"),
        yaxis_title="Branch",
        **LAYOUT_DEFAULTS,
    )
    return fig
