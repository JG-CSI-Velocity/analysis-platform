"""DCTR categorization functions for age, balance, and decade buckets."""

import pandas as pd


def categorize_account_age(days):
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
    return "10+ years"


def categorize_holder_age(age):
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
    return "65+"


def categorize_balance(bal):
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


def simplify_account_age(age_range):
    if age_range in ("0-6 months", "6-12 months"):
        return "New (0-1 year)"
    if age_range in ("1-2 years", "2-5 years"):
        return "Recent (1-5 years)"
    if age_range in ("5-10 years", "10+ years"):
        return "Mature (5+ years)"
    return "Unknown"


def map_to_decade(year):
    if pd.isna(year):
        return None
    recent = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
    if year < 1970:
        return "Before 1970"
    if int(year) in recent:
        return str(int(year))
    return f"{(int(year) // 10) * 10}s"
