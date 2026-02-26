"""Figure lifecycle management -- guaranteed cleanup + style isolation."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

_TXN_STYLE = Path(__file__).parent / "txn.mplstyle"


@contextmanager
def chart_figure(
    figsize: tuple[float, float] = (10, 6),
    dpi: int = 150,
    style: str | None = None,
    save_path: Path | None = None,
) -> Generator[tuple[Figure, Axes], None, None]:
    """Context manager guaranteeing figure cleanup + style isolation.

    Usage:
        with chart_figure(save_path=out / "chart.png") as (fig, ax):
            ax.bar(x, y)
            ax.set_title("My Chart")
        # Figure is saved and closed automatically
    """
    style_path = style or str(_TXN_STYLE)
    with plt.style.context(style_path):
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        try:
            yield fig, ax
            if save_path is not None:
                fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        finally:
            plt.close(fig)


@contextmanager
def multi_axes(
    nrows: int = 1,
    ncols: int = 1,
    figsize: tuple[float, float] = (14, 7),
    dpi: int = 150,
    style: str | None = None,
    save_path: Path | None = None,
) -> Generator[tuple[Figure, any], None, None]:
    """Context manager for multi-subplot figures with guaranteed cleanup.

    Usage:
        with multi_axes(nrows=1, ncols=3, figsize=(18, 6)) as (fig, axes):
            for ax, data in zip(axes, datasets):
                ax.barh(data.y, data.x)
    """
    style_path = style or str(_TXN_STYLE)
    with plt.style.context(style_path):
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, dpi=dpi)
        try:
            yield fig, axes
            if save_path is not None:
                fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        finally:
            plt.close(fig)
