"""Figure lifecycle management -- guaranteed cleanup + style isolation.

Usage:
    from ics_toolkit.analysis.charts.guards import chart_figure

    buf = BytesIO()
    with chart_figure(save_path=buf) as (fig, ax):
        ax.bar(x, y)
    buf.seek(0)
    png_bytes = buf.read()
"""

from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

_ICS_STYLE = Path(__file__).parent / "ics.mplstyle"


@contextmanager
def chart_figure(
    figsize: tuple[float, float] = (14, 8),
    dpi: int = 150,
    style: str | None = None,
    save_path: Path | BytesIO | None = None,
) -> Generator[tuple[Figure, Axes], None, None]:
    """Context manager guaranteeing figure cleanup + style isolation.

    Usage:
        with chart_figure(save_path=out / "chart.png") as (fig, ax):
            ax.bar(x, y)
            ax.set_title("My Chart")
        # Figure is saved and closed automatically
    """
    style_path = style or str(_ICS_STYLE)
    with plt.style.context(style_path):
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        try:
            yield fig, ax
            if save_path is not None:
                fig.savefig(
                    save_path,
                    dpi=dpi,
                    bbox_inches="tight",
                    facecolor="white",
                    edgecolor="none",
                )
        finally:
            plt.close(fig)


def render_to_bytes(
    figsize: tuple[float, float] = (14, 8),
    dpi: int = 150,
) -> tuple[BytesIO, "contextmanager"]:
    """Convenience: get a BytesIO buffer and chart_figure context manager.

    Usage:
        buf = BytesIO()
        with chart_figure(save_path=buf) as (fig, ax):
            ...
        buf.seek(0)
        return buf.read()
    """
    buf = BytesIO()
    return buf, chart_figure(figsize=figsize, dpi=dpi, save_path=buf)
