"""Shared formatting helpers for Excel and display output."""

from __future__ import annotations


def format_value(val, col_name: str) -> str:
    """Format a cell value for display based on column name heuristics."""
    if val is None or (isinstance(val, float) and val != val):
        return ""
    col_lower = col_name.lower()
    if is_currency_column(col_lower):
        return f"${float(val):,.0f}"
    if is_percentage_column(col_lower):
        return f"{float(val):.1f}%"
    if "avg" in col_lower or "mean" in col_lower or "average" in col_lower:
        return f"{float(val):,.2f}"
    try:
        num = float(val)
        if num == int(num):
            return f"{int(num):,}"
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def excel_number_format(col_name: str) -> str:
    """Return openpyxl number format string for a column."""
    col_lower = col_name.lower()
    if is_percentage_column(col_lower):
        return "0.0%"
    if is_currency_column(col_lower):
        return "$#,##0.00"
    if "avg" in col_lower or "mean" in col_lower or "average" in col_lower:
        return "0.00"
    return "#,##0"


def is_currency_column(col_lower: str) -> bool:
    return any(kw in col_lower for kw in ("spend", "amount", "dollar", "$"))


def is_percentage_column(col_lower: str) -> bool:
    return any(kw in col_lower for kw in ("%", "pct", "percent", "rate", "penetration"))


def is_grand_total_row(val) -> bool:
    return str(val).strip().lower() in ("grand total", "total", "all")
