"""ARS (Account Revenue Solution) v2 modular analysis pipeline.

20 analytics modules across 7 sections: Overview, DCTR, Reg E,
Attrition, Value, Mailer, and Insights. Batch processing for 300+ clients.
"""

from ars_analysis.runner import run_ars

__all__ = ["run_ars"]
