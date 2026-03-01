"""Reusable chart annotation utilities for executive presentations.

Provides helpers for labeling bars, annotating line endpoints, adding
comparison callouts, and computing emphasis/directional color arrays.
All functions work with matplotlib Axes objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer
    from matplotlib.lines import Line2D


def add_bar_labels(
    ax: Axes,
    bars: BarContainer,
    values: list[float],
    fmt: str = "{:.1%}",
    inside_threshold: float = 0.15,
    fontsize: int = 11,
    color: str = "#2E4057",
    inside_color: str = "white",
) -> None:
    """Add value labels above or inside bars.

    Labels are placed inside the bar when the value exceeds *inside_threshold*
    of the axis range, otherwise above.
    """
    y_max = ax.get_ylim()[1]
    for bar, val in zip(bars, values):
        label = fmt.format(val)
        x = bar.get_x() + bar.get_width() / 2
        h = bar.get_height()
        if h > y_max * inside_threshold:
            ax.text(
                x, h * 0.85, label,
                ha="center", va="top", fontsize=fontsize, color=inside_color,
                fontweight="bold",
            )
        else:
            ax.text(
                x, h + y_max * 0.01, label,
                ha="center", va="bottom", fontsize=fontsize, color=color,
            )


def label_line_ends(
    ax: Axes,
    lines: list[Line2D],
    labels: list[str],
    fontsize: int = 14,
    color: str = "#2E4057",
    offset: float = 0.02,
) -> None:
    """Add labels at the right endpoint of each line.

    Useful for clearly identifying multiple time-series without a legend.
    """
    for line, label in zip(lines, labels):
        data = line.get_ydata()
        xdata = line.get_xdata()
        if len(data) == 0:
            continue
        y = float(data[-1])
        x = float(xdata[-1])
        y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
        ax.text(
            x, y + y_range * offset, label,
            fontsize=fontsize, color=color, va="bottom",
        )


def add_comparison_callout(
    ax: Axes,
    value: float,
    x_pos: float,
    y_pos: float,
    label_fmt: str = "{:+.1f}pp",
    fontsize: int = 14,
    color: str | None = None,
) -> Any:
    """Add a comparison annotation (e.g. "+4pp vs baseline").

    Returns the text artist for further customization.
    """
    if color is None:
        color = "#2D936C" if value >= 0 else "#C73E1D"
    text = label_fmt.format(value)
    return ax.annotate(
        text,
        xy=(x_pos, y_pos),
        fontsize=fontsize,
        color=color,
        fontweight="bold",
        ha="center",
        va="bottom",
    )


def emphasis_colors(
    n_bars: int,
    hero_index: int = 0,
    hero: str = "#2E4057",
    muted: str = "#D5D8DC",
) -> list[str]:
    """Return a list of colors where one bar is emphasized.

    The bar at *hero_index* gets the *hero* color; all others get *muted*.
    """
    return [hero if i == hero_index else muted for i in range(n_bars)]


def directional_color(
    value: float,
    threshold_good: float = 0,
    threshold_bad: float = 0,
    good_color: str = "#2D936C",
    bad_color: str = "#C73E1D",
    neutral_color: str = "#8B95A2",
) -> str:
    """Return a color based on whether value is above or below thresholds.

    If *threshold_good* == *threshold_bad*, values above are good and below bad.
    """
    if value > threshold_good:
        return good_color
    if value < threshold_bad:
        return bad_color
    return neutral_color
