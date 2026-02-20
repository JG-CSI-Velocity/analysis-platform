"""Base analysis infrastructure: AnalysisResult dataclass and helpers.

All canonical types and helpers live in the ``shared`` package.
Re-exported here so existing ICS code needs zero import changes.
"""

from shared.helpers import safe_percentage, safe_ratio
from shared.types import AnalysisResult

__all__ = ["AnalysisResult", "safe_percentage", "safe_ratio"]
