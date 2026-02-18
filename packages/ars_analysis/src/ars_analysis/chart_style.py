"""
chart_style.py -- Shared chart constants for dctr, reg_e, value, attrition modules.

Constants only -- no functions. Use ars.mplstyle for rcParams defaults.
Import what you need: from chart_style import PERSONAL, BUSINESS, TITLE_SIZE
"""

from matplotlib.ticker import FuncFormatter

# Semantic colors
PERSONAL = '#4472C4'
BUSINESS = '#ED7D31'
HISTORICAL = '#5B9BD5'
TTM = '#FFC000'
ELIGIBLE = '#70AD47'
POSITIVE = '#27AE60'
NEGATIVE = '#E74C3C'
NEUTRAL = '#95A5A6'
SILVER = '#BDC3C7'
TEAL = '#2E86AB'

# Presentation font sizes (for per-call overrides beyond rcParams)
TITLE_SIZE = 24
AXIS_LABEL_SIZE = 20
DATA_LABEL_SIZE = 20
TICK_SIZE = 18
LEGEND_SIZE = 16
ANNOTATION_SIZE = 18

# Bar chart defaults
BAR_EDGE = 'none'
BAR_ALPHA = 0.9

# Percentage formatter (pre-instantiated, reuse everywhere)
PCT_FORMATTER = FuncFormatter(lambda x, p: f'{x:.0f}%')
