"""Layer 4: Household/network inference via soft signals."""

from __future__ import annotations

import pandas as pd


def infer_networks(df: pd.DataFrame) -> pd.DataFrame:
    """Infer household/network relationships via shared referrer + account surname.

    Added columns: Network ID, Network Size
    """
    df = df.copy()
    network_map = (
        df.groupby(["Referrer", "Account Surname"])
        .agg(network_size=("MRDB Account Hash", "nunique"))
        .reset_index()
    )
    network_map["Network ID"] = network_map["Referrer"] + ":" + network_map["Account Surname"]

    df = df.merge(
        network_map[["Referrer", "Account Surname", "Network ID", "network_size"]],
        on=["Referrer", "Account Surname"],
        how="left",
    )
    df.rename(columns={"network_size": "Network Size"}, inplace=True)
    return df
