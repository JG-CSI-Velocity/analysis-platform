"""Base infrastructure for referral analysis artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ics_toolkit.settings import ReferralSettings


@dataclass
class ReferralContext:
    """Bundles all pre-computed data for referral analysis functions."""

    df: pd.DataFrame
    referrer_metrics: pd.DataFrame
    staff_metrics: pd.DataFrame
    settings: ReferralSettings
