"""Layer 2: Referral code decoding and classification."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ics_toolkit.settings import ReferralSettings

# Channel -> Type mapping
_CHANNEL_TYPE_MAP = {
    "BRANCH_STANDARD": "Standard",
    "DIGITAL_PROCESS": "Standard",
    "EMAIL": "Standard",
    "MANUAL": "Manual",
    "OTHER": "Exception",
}

# Type -> Reliability mapping
_TYPE_RELIABILITY_MAP = {
    "Standard": "High",
    "Manual": "Medium",
    "Exception": "Low",
}


def decode_referral_codes(df: pd.DataFrame, settings: ReferralSettings) -> pd.DataFrame:
    """Decode referral codes into channel, type, and reliability tags.

    Added columns: Referral Channel, Referral Type, Referral Reliability
    """
    df = df.copy()
    sorted_prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)

    df["Referral Channel"] = df["Referral Code"].apply(
        lambda c: _classify_channel(c, sorted_prefixes, settings.code_prefix_map)
    )
    df["Referral Type"] = df["Referral Channel"].map(_CHANNEL_TYPE_MAP).fillna("Exception")
    df["Referral Reliability"] = df["Referral Type"].map(_TYPE_RELIABILITY_MAP)
    return df


def _classify_channel(
    code: object,
    sorted_prefixes: list[str],
    prefix_map: dict[str, str],
) -> str:
    """Classify a single referral code into a channel."""
    if pd.isna(code) or str(code).strip() in ("", "None", "none", "NONE"):
        return "MANUAL"
    code_str = str(code).strip().upper()
    for prefix in sorted_prefixes:
        if code_str.startswith(prefix.upper()):
            return prefix_map[prefix]
    if "EMAIL" in code_str:
        return "EMAIL"
    return "OTHER"
