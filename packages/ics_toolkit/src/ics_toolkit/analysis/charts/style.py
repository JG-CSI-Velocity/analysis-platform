"""ICS chart style constants -- semantic colors and presentation defaults.

Import what you need:
    from ics_toolkit.analysis.charts.style import NAVY, TEAL, ACQUISITION, VALUE
"""

from matplotlib.ticker import FuncFormatter

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
NAVY = "#1B365D"
STEEL = "#4A6FA5"
TEAL = "#1ABC9C"
SKY = "#4A90D9"

# ---------------------------------------------------------------------------
# Semantic colors (mapped to ICS business goals)
# ---------------------------------------------------------------------------

# Goal 1: Acquisition -- bringing accounts in
ACQUISITION = "#2ECC71"       # Vibrant green for new accounts, opens
DM_SOURCE = NAVY              # Direct Mail channel
REF_SOURCE = TEAL             # Referral channel

# Goal 2: Value -- proving revenue impact
VALUE = "#27AE60"             # Deep green for revenue/interchange
SPEND = "#4A90D9"             # Blue for spend metrics
INTERCHANGE = "#1B365D"       # Navy for interchange revenue

# Goal 3: Need -- retention and health
CLOSURE = "#E74C3C"           # Red for closures, attrition
DECAY = "#E67E22"             # Orange for engagement decay
GROWTH = "#27AE60"            # Green for net growth

# General semantic
POSITIVE = "#27AE60"
NEGATIVE = "#E74C3C"
NEUTRAL = "#95A5A6"
SILVER = "#BDC3C7"
HIGHLIGHT = "#F39C12"         # Gold for callouts
MUTED = "#7F8C8D"

# Persona colors (established in existing codebase)
PERSONA_FAST = "#27AE60"
PERSONA_SLOW = "#1ABC9C"
PERSONA_ONE = "#E67E22"
PERSONA_NEVER = "#BDC3C7"
PERSONA_COLORS = {
    "Fast Activator": PERSONA_FAST,
    "Slow Burner": PERSONA_SLOW,
    "One and Done": PERSONA_ONE,
    "Never Activator": PERSONA_NEVER,
}
PERSONA_ORDER = ["Fast Activator", "Slow Burner", "One and Done", "Never Activator"]

# Ordered palette for multi-series charts (8 distinct colors)
PALETTE = [NAVY, TEAL, ACQUISITION, CLOSURE, HIGHLIGHT, STEEL, DECAY, SKY]

# ---------------------------------------------------------------------------
# Presentation font sizes (for per-call overrides beyond rcParams)
# ---------------------------------------------------------------------------
TITLE_SIZE = 24
SUBTITLE_SIZE = 18
AXIS_LABEL_SIZE = 18
DATA_LABEL_SIZE = 16
TICK_SIZE = 14
LEGEND_SIZE = 14
ANNOTATION_SIZE = 16

# ---------------------------------------------------------------------------
# Bar chart defaults
# ---------------------------------------------------------------------------
BAR_EDGE = "white"
BAR_EDGE_WIDTH = 0.8
BAR_ALPHA = 0.92
BAR_WIDTH = 0.6

# Marker/line defaults
LINE_WIDTH = 2.5
MARKER_SIZE = 8

# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
PCT_FORMATTER = FuncFormatter(lambda x, _: f"{x:.0f}%")
DOLLAR_FORMATTER = FuncFormatter(lambda x, _: f"${x:,.0f}")
COUNT_FORMATTER = FuncFormatter(lambda x, _: f"{x:,.0f}")
