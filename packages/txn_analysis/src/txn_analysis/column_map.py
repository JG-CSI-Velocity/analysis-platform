"""Column alias resolution and required column definitions."""

from __future__ import annotations

import pandas as pd

from txn_analysis.exceptions import ColumnMismatchError

REQUIRED_COLUMNS = {
    "merchant_name",
    "amount",
    "primary_account_num",
    "transaction_date",
}

OPTIONAL_COLUMNS = {
    "mcc_code",
    "business_flag",
    "year_month",
}

# Maps raw header variations -> canonical name.
COLUMN_ALIASES: dict[str, str] = {
    # merchant_name
    "merchant_name": "merchant_name",
    "merchantname": "merchant_name",
    "merchant name": "merchant_name",
    "merchant": "merchant_name",
    "merch_name": "merchant_name",
    # amount
    "amount": "amount",
    "transaction_amount": "amount",
    "txn_amount": "amount",
    "trans_amount": "amount",
    "amt": "amount",
    # primary_account_num
    "primary_account_num": "primary_account_num",
    "primaryaccountnum": "primary_account_num",
    "primary account num": "primary_account_num",
    "account_number": "primary_account_num",
    "account_num": "primary_account_num",
    "acct_num": "primary_account_num",
    "acct_number": "primary_account_num",
    "account": "primary_account_num",
    # transaction_date
    "transaction_date": "transaction_date",
    "transactiondate": "transaction_date",
    "transaction date": "transaction_date",
    "trans_date": "transaction_date",
    "txn_date": "transaction_date",
    "date": "transaction_date",
    # mcc_code
    "mcc_code": "mcc_code",
    "mcccode": "mcc_code",
    "mcc code": "mcc_code",
    "mcc": "mcc_code",
    # business_flag
    "business_flag": "business_flag",
    "businessflag": "business_flag",
    "business flag": "business_flag",
    "business": "business_flag",
    "is_business": "business_flag",
    # year_month
    "year_month": "year_month",
    "yearmonth": "year_month",
    "year month": "year_month",
    "ym": "year_month",
}


def resolve_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical names using COLUMN_ALIASES.

    Returns a new DataFrame with resolved column names.
    Raises ColumnMismatchError if required columns are missing after resolution.
    """
    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower().replace("-", "_")
        if key in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[key]

    result = df.rename(columns=rename_map)

    resolved = set(result.columns)
    missing = REQUIRED_COLUMNS - resolved
    if missing:
        raise ColumnMismatchError(missing=missing, available=resolved)

    return result
