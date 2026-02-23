"""Verify brand constants are consistent across .bat files and Python code."""

from __future__ import annotations

import re
from pathlib import Path

from platform_app.brand import (
    COMPANY_NAME,
    PAGE_TITLE,
    PRODUCT_NAME,
    SHORT_NAME,
    TAGLINE,
    VERSION,
)


def test_brand_constants_are_non_empty_strings() -> None:
    for val in (PRODUCT_NAME, SHORT_NAME, COMPANY_NAME, VERSION, PAGE_TITLE, TAGLINE):
        assert isinstance(val, str) and len(val) > 0


def test_derived_strings_match_constants() -> None:
    assert PAGE_TITLE == SHORT_NAME
    assert SHORT_NAME in TAGLINE
    assert VERSION in TAGLINE


def test_bat_files_show_correct_brand() -> None:
    repo_root = Path(__file__).parent.parent.parent
    for name in ("run.bat", "dashboard.bat", "run_batch.bat", "setup.bat"):
        bat_path = repo_root / name
        assert bat_path.exists(), f"Missing: {bat_path}"
        content = bat_path.read_text(encoding="utf-8")
        # Allow both "CSI | Velocity" and "CSI ^| Velocity" (batch pipe escape)
        company_pattern = re.escape(COMPANY_NAME).replace(r"\|", r"\^?\|")
        assert PRODUCT_NAME in content, f"{name} missing '{PRODUCT_NAME}'"
        assert re.search(company_pattern, content), f"{name} missing '{COMPANY_NAME}'"
