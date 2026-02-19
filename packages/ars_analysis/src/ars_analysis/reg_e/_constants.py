"""Reg E constants -- categorization orders and bucket definitions."""

import numpy as np
import pandas as pd

ACCT_AGE_ORDER = (
    "0-6 months",
    "6-12 months",
    "1-2 years",
    "2-5 years",
    "5-10 years",
    "10-20 years",
    "20+ years",
)

HOLDER_AGE_ORDER = ("18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+")

BALANCE_ORDER = (
    "Negative",
    "$0-$499",
    "$500-$999",
    "$1K-$2.5K",
    "$2.5K-$5K",
    "$5K-$10K",
    "$10K-$25K",
    "$25K-$50K",
    "$50K-$100K",
    "$100K+",
)


def _cat_acct_age(days):
    if pd.isna(days):
        return "Unknown"
    if days < 180:
        return "0-6 months"
    if days < 365:
        return "6-12 months"
    if days < 730:
        return "1-2 years"
    if days < 1825:
        return "2-5 years"
    if days < 3650:
        return "5-10 years"
    if days < 7300:
        return "10-20 years"
    return "20+ years"


def _cat_holder_age(age):
    if pd.isna(age):
        return "Unknown"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    if age < 75:
        return "65-74"
    return "75+"


def _cat_balance(bal):
    if pd.isna(bal):
        return "Unknown"
    if bal < 0:
        return "Negative"
    if bal < 500:
        return "$0-$499"
    if bal < 1000:
        return "$500-$999"
    if bal < 2500:
        return "$1K-$2.5K"
    if bal < 5000:
        return "$2.5K-$5K"
    if bal < 10000:
        return "$5K-$10K"
    if bal < 25000:
        return "$10K-$25K"
    if bal < 50000:
        return "$25K-$50K"
    if bal < 100000:
        return "$50K-$100K"
    return "$100K+"
