"""Reg E analysis package -- A8 Reg E Opt-In Analysis."""

from ars_analysis.reg_e._constants import (
    ACCT_AGE_ORDER,
    BALANCE_ORDER,
    HOLDER_AGE_ORDER,
    _cat_acct_age,
    _cat_balance,
    _cat_holder_age,
)
from ars_analysis.reg_e._core import (
    run_reg_e_1,
    run_reg_e_2,
    run_reg_e_3,
    run_reg_e_4,
    run_reg_e_4b,
    run_reg_e_5,
    run_reg_e_6,
    run_reg_e_7,
    run_reg_e_8,
    run_reg_e_9,
    run_reg_e_10,
    run_reg_e_11,
    run_reg_e_12,
    run_reg_e_13,
    run_reg_e_cohort,
    run_reg_e_executive_summary,
    run_reg_e_opportunity,
    run_reg_e_seasonality,
)
from ars_analysis.reg_e._helpers import (
    _opt_list,
    _reg_col,
    _rege,
    _total_row,
)
from ars_analysis.reg_e._suite import (
    REG_ORDER,
    REGE_APPENDIX_IDS,
    REGE_MERGES,
    run_reg_e_suite,
)

__all__ = [
    # Suite runner
    "run_reg_e_suite",
    "REG_ORDER",
    "REGE_MERGES",
    "REGE_APPENDIX_IDS",
    # Analysis functions
    "run_reg_e_1",
    "run_reg_e_2",
    "run_reg_e_3",
    "run_reg_e_4",
    "run_reg_e_4b",
    "run_reg_e_5",
    "run_reg_e_6",
    "run_reg_e_7",
    "run_reg_e_8",
    "run_reg_e_9",
    "run_reg_e_10",
    "run_reg_e_11",
    "run_reg_e_12",
    "run_reg_e_13",
    "run_reg_e_opportunity",
    "run_reg_e_executive_summary",
    "run_reg_e_cohort",
    "run_reg_e_seasonality",
    # Constants
    "ACCT_AGE_ORDER",
    "HOLDER_AGE_ORDER",
    "BALANCE_ORDER",
    # Helpers (public API)
    "_rege",
    "_opt_list",
    "_reg_col",
    "_total_row",
    "_cat_acct_age",
    "_cat_holder_age",
    "_cat_balance",
]
