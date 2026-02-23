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
    "merchant_description": "merchant_name",
    "description": "merchant_name",
    "payee": "merchant_name",
    "payee_name": "merchant_name",
    "vendor": "merchant_name",
    "vendor_name": "merchant_name",
    "merch": "merchant_name",
    # amount
    "amount": "amount",
    "transaction_amount": "amount",
    "txn_amount": "amount",
    "trans_amount": "amount",
    "amt": "amount",
    "tran_amount": "amount",
    "tran_amt": "amount",
    "debit_amount": "amount",
    "purchase_amount": "amount",
    "total_amount": "amount",
    "auth_amount": "amount",
    # primary_account_num
    "primary_account_num": "primary_account_num",
    "primaryaccountnum": "primary_account_num",
    "primary account num": "primary_account_num",
    "account_number": "primary_account_num",
    "account_num": "primary_account_num",
    "acct_num": "primary_account_num",
    "acct_number": "primary_account_num",
    "account": "primary_account_num",
    "acct": "primary_account_num",
    "acct_no": "primary_account_num",
    "account_no": "primary_account_num",
    "card_number": "primary_account_num",
    "card_num": "primary_account_num",
    "pan": "primary_account_num",
    "member_number": "primary_account_num",
    "member_num": "primary_account_num",
    "member_no": "primary_account_num",
    "primary_account_number": "primary_account_num",
    # transaction_date
    "transaction_date": "transaction_date",
    "transactiondate": "transaction_date",
    "transaction date": "transaction_date",
    "trans_date": "transaction_date",
    "txn_date": "transaction_date",
    "date": "transaction_date",
    "tran_date": "transaction_date",
    "posting_date": "transaction_date",
    "post_date": "transaction_date",
    "settlement_date": "transaction_date",
    "auth_date": "transaction_date",
    "effective_date": "transaction_date",
    # mcc_code
    "mcc_code": "mcc_code",
    "mcccode": "mcc_code",
    "mcc code": "mcc_code",
    "mcc": "mcc_code",
    "merchant_category_code": "mcc_code",
    "sic_code": "mcc_code",
    "sic": "mcc_code",
    # business_flag
    "business_flag": "business_flag",
    "businessflag": "business_flag",
    "business flag": "business_flag",
    "business": "business_flag",
    "is_business": "business_flag",
    "account_type": "business_flag",
    # year_month
    "year_month": "year_month",
    "yearmonth": "year_month",
    "year month": "year_month",
    "ym": "year_month",
}


_KEYWORD_FALLBACKS: list[tuple[str, list[str]]] = [
    ("merchant_name", ["merch", "payee", "vendor", "descr"]),
    ("amount", ["amt", "amount"]),
    ("primary_account_num", ["acct", "account", "member", "card", "pan"]),
    ("transaction_date", ["date", "posted", "settle"]),
]


def resolve_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical names using COLUMN_ALIASES.

    Uses a two-pass approach:
    1. Exact alias match (fast, deterministic)
    2. Keyword fallback for remaining missing columns (catches non-standard names)

    Returns a new DataFrame with resolved column names.
    Raises ColumnMismatchError if required columns are missing after resolution.
    """
    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower().replace("-", "_")
        if key in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[key]

    result = df.rename(columns=rename_map)

    # Pass 2: keyword fallback for still-missing required columns
    resolved = set(result.columns)
    missing = REQUIRED_COLUMNS - resolved
    if missing:
        extra_renames: dict[str, str] = {}
        for canonical, keywords in _KEYWORD_FALLBACKS:
            if canonical not in missing:
                continue
            for col in result.columns:
                if col in extra_renames.values():
                    continue
                cl = str(col).strip().lower()
                if any(kw in cl for kw in keywords):
                    extra_renames[col] = canonical
                    break
        if extra_renames:
            result = result.rename(columns=extra_renames)

    resolved = set(result.columns)
    missing = REQUIRED_COLUMNS - resolved
    if missing:
        raise ColumnMismatchError(missing=missing, available=resolved)

    return result
