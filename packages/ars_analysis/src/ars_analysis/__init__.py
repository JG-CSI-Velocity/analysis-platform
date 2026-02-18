"""ARS (Account Revenue Solution) analysis pipeline.

55+ analyses across DCTR, Reg E, Attrition, Value, and Mailer modules.
Ported from ars_analysis-jupyter with import fixes for package structure.
"""

from ars_analysis.runner import run_ars, run_ars_from_dict

__all__ = ["run_ars", "run_ars_from_dict"]
