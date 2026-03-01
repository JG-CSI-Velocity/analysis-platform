"""Shared chart constants for all analysis modules.

Constants only -- no functions. Use ars.mplstyle for rcParams defaults.
Import what you need: from ars_analysis.charts.style import PERSONAL, BUSINESS, TITLE_SIZE

Color authority imported from shared.charts.COLORS (canonical).
Legacy ARS-specific semantic names (PERSONAL, BUSINESS, etc.) preserved as aliases.
"""

from matplotlib.ticker import FuncFormatter

from shared.charts import COLORS

# Canonical semantic colors (from shared authority)
PRIMARY = COLORS["primary"]
POSITIVE = COLORS["positive"]
NEGATIVE = COLORS["negative"]
NEUTRAL = COLORS["neutral"]

# ARS-specific semantic names (backward-compatible aliases)
PERSONAL = "#4472C4"
BUSINESS = "#ED7D31"
HISTORICAL = "#5B9BD5"
TTM = "#FFC000"
ELIGIBLE = "#70AD47"
SILVER = "#BDC3C7"
TEAL = "#2E86AB"

# Presentation font sizes (for per-call overrides beyond rcParams)
TITLE_SIZE = 24
AXIS_LABEL_SIZE = 20
DATA_LABEL_SIZE = 20
TICK_SIZE = 18
LEGEND_SIZE = 16
ANNOTATION_SIZE = 18

# Bar chart defaults
BAR_EDGE = "none"
BAR_ALPHA = 0.9

# Percentage formatter (pre-instantiated, reuse everywhere)
PCT_FORMATTER = FuncFormatter(lambda x, p: f"{x:.0f}%")
