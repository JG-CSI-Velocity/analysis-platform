"""Value formatting for display and Excel export."""


def format_value(value, col_name: str = "") -> str:
    """Format a value based on column name conventions.

    Convention:
        - Column contains '%' or 'Pct' -> percentage (e.g., 75.0 -> '75.0%')
        - Column contains '$' or 'Bal' or 'Spend' -> currency
        - Column contains 'Ratio' -> decimal with 2 places
        - Otherwise -> comma-separated integer or plain string
    """
    if value is None:
        return ""

    col_upper = col_name.upper()

    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    if "%" in col_name or "PCT" in col_upper:
        return f"{num:.1f}%"

    if "$" in col_name or "BAL" in col_upper or "SPEND" in col_upper:
        return f"${num:,.2f}"

    if "RATIO" in col_upper:
        return f"{num:.2f}"

    if num == int(num) and abs(num) < 1e15:
        return f"{int(num):,}"

    return f"{num:,.2f}"


def excel_number_format(col_name: str) -> str:
    """Return an Excel number format string based on column name conventions."""
    col_upper = col_name.upper()

    if "%" in col_name or "PCT" in col_upper:
        return '0.0"%"'

    if "$" in col_name or "BAL" in col_upper or "SPEND" in col_upper:
        return "$#,##0.00"

    if "RATIO" in col_upper:
        return "0.00"

    if "COUNT" in col_upper or "TOTAL" in col_upper or "SWIPE" in col_upper:
        return "#,##0"

    return "General"
