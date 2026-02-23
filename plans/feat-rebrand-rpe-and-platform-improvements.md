# Rebrand to RPE Analysis Platform + Platform Improvements

## Enhancement Summary

**Deepened on:** 2026-02-23
**Agents used:** architecture-strategist, code-simplicity-reviewer, pattern-recognition-specialist, kieran-python-reviewer, performance-oracle, deployment-verification-agent, stale-test-imports learning, st.logo research, config.toml sidebar research

### Key Improvements from Research
1. **Simplified `brand.py`**: Frozen dataclass replaced with plain module constants (reviewer consensus: dataclass is over-engineered for 5 strings)
2. **CSS rename deferred**: Multiple reviewers flagged Phase 4 as high-effort/low-reward. Moved to optional. Keep `uap-` internally, just like `uap_` session state.
3. **Brand consistency test added**: New `test_brand_consistency.py` catches .bat file drift automatically
4. **`[theme.sidebar]` config**: Streamlit natively supports sidebar-specific theming in config.toml -- use it for base colors
5. **`st.logo()` ready**: Can add branding logo once asset is provided (deferred, needs SVG)
6. **Performance config**: Add `fastReruns = true` and `magicEnabled = false` to config.toml while we're touching it
7. **Stale test imports warning**: Prior V2 rewrite caused test failures from stale imports -- grep tests before deleting dead code

### Scope Reduction (Simplicity Review)
- **Phase 4 (CSS rename)**: DEFERRED -- 224+ edits for internal-only class names, no user benefit, inconsistent with keeping `uap_` session keys
- **Phase 6 (tempdir)**: DROPPED -- ephemeral, never seen by users
- **Phase 7 (history dir)**: SIMPLIFIED -- just delete dead file
- **Files touched**: 25 -> 17 (32% reduction)
- **Edits**: ~200 -> ~60 (70% reduction)

---

## Overview

Rebrand the platform from "UAP" / "Unified Analysis Platform" / "CSI Velocity Solutions" to **"RPE Analysis Platform"** by **"CSI | Velocity"**. Simultaneously clean up dead CSS code and add a brand consistency test.

## Problem Statement

The current codebase uses three overlapping brand names ("UAP", "Analysis Platform", "CSI Velocity Solutions") scattered across 27+ files. Two dead theming layers (`theme.py` and `components/styles.py`) conflict with the active CSS in `app.py`.

---

## Proposed Solution

### Phase 1: Create `brand.py` -- Single Source of Truth

**File:** `packages/platform_app/src/platform_app/brand.py` (NEW)

```python
"""RPE Analysis Platform -- brand constants.

Single source of truth for product name, company, version, and display strings.
All user-facing strings derive from this file.

LEGACY CONVENTION: Session state keys and CSS classes retain the `uap_` / `uap-`
prefix. These are internal to Streamlit and never appear in the UI. Renaming
114 session state refs across 7 files would risk silent data loss with no user
benefit. The prefix stays as a historical artifact.
"""

from __future__ import annotations

# Product identity
PRODUCT_NAME: str = "RPE Analysis Platform"
SHORT_NAME: str = "RPE"
COMPANY_NAME: str = "CSI | Velocity"
VERSION: str = "2.0"

# Display strings (derived from constants above)
PAGE_TITLE: str = SHORT_NAME
TAGLINE: str = f"{SHORT_NAME} v{VERSION} // ANALYSIS PLATFORM"
CLI_DESCRIPTION: str = f"{PRODUCT_NAME}: ARS, Transaction, and ICS pipelines."
```

**Why module constants, not a dataclass** (reviewer consensus):
- 5 strings don't need a class wrapper -- that's over-engineering
- `from brand import PRODUCT_NAME` is cleaner than `from brand import BRAND; BRAND.product`
- Follows PEP 8 (`UPPER_CASE` constants) and stdlib conventions (`sys.version`)
- No runtime overhead from class instantiation

- [x] Create `brand.py` with module constants
- [x] Import constants in `app.py` and wire to `page_title`, sidebar footer, home header

### Phase 2: Rebrand User-Facing Strings (Safe, No Functional Impact)

**Browser tab + sidebar footer:**

| File | Line | Old | New |
|------|------|-----|-----|
| `app.py` | 11 | `page_title="UAP"` | `page_title=PAGE_TITLE` |
| `app.py` | ~460 | `UAP v2.0 // ANALYSIS PLATFORM` | `{TAGLINE}` |
| `pages/home.py` | ~201 | `UNIFIED ANALYSIS PLATFORM` | `RPE ANALYSIS PLATFORM` |

- [x] Update `app.py` page_title and sidebar footer
- [x] Update `pages/home.py` header label

**CLI help text:**

| File | Line | Old | New |
|------|------|-----|-----|
| `cli.py` | 10 | `name="analysis-platform"` | Keep (internal command name) |
| `cli.py` | 11 | `"Unified banking analysis platform..."` | `CLI_DESCRIPTION` from brand.py |

- [x] Update `cli.py` help text (keep command name `analysis-platform`)

**.bat file banners (4 files):**

| File | Old | New |
|------|-----|-----|
| `run.bat` | `Analysis Platform v2.0` / `CSI Velocity Solutions` | `RPE Analysis Platform v2.0` / `CSI \| Velocity` |
| `dashboard.bat` | `Analysis Platform -- Dashboard` | `RPE Analysis Platform -- Dashboard` |
| `run_batch.bat` | `Analysis Platform -- Headless Batch` | `RPE Analysis Platform -- Headless Batch` |
| `setup.bat` | `Analysis Platform -- First-Time Setup` | `RPE Analysis Platform -- First-Time Setup` |

Add `REM BRAND: Update if brand.py changes (verified by test_brand_consistency.py)` to each .bat.

- [x] Update `run.bat` banner
- [x] Update `dashboard.bat` banner
- [x] Update `run_batch.bat` banner
- [x] Update `setup.bat` banner

**Docstrings (8 page files + entry point):**

Replace `"""UAP ...` docstrings with `"""RPE ...` in:
- [x] `app.py` line 1
- [x] `pages/home.py` line 1
- [x] `pages/outputs.py` line 1
- [x] `pages/run_history.py` line 1
- [x] `pages/module_library.py` line 1
- [x] `pages/workspace.py` line 1
- [x] `pages/data_ingestion.py` line 1
- [x] `pages/run_analysis.py` line 1
- [x] `pages/batch_workflow.py` line 1

**Documentation:**

- [x] Update `README.md` header and description
- [x] Update `CLAUDE.md` header
- [x] Update `HANDOFF.md` header
- [x] Update `TECHNICAL.md` header
- [x] Update `pyproject.toml` (root) description field
- [x] Update `config/platform.yaml` header comment
- [x] Update `packages/shared/src/shared/__init__.py` docstring
- [x] Update `packages/platform_app/src/platform_app/__init__.py` docstring
- [x] Update `packages/platform_app/src/platform_app/core/__init__.py` docstring

### Phase 3: Delete Dead CSS Code

Research confirmed that `theme.py:inject_theme()` and `components/styles.py:inject_page_css()` are **never called** from any page file. The `ars-stepper`, `ars-step-*`, `pipeline-header`, `status-chip`, and `file-indicator` CSS classes are all unreachable.

**Stale test imports warning** (from prior V2 rewrite learning): Before deleting, grep tests for imports:
```bash
grep -r "from.*theme.*import\|from.*styles.*import" tests/
grep -r "inject_theme\|inject_page_css\|step_indicator_html\|success_banner" tests/
```

- [x] Grep tests for dead code imports (prevent stale import failures)
- [x] Delete `inject_theme()` function and its CSS from `theme.py`
- [x] Delete `step_indicator_html()` and `success_banner()` from `theme.py` (never imported)
- [x] Delete `inject_page_css()` and `render_page_header()` from `components/styles.py` (never imported)
- [x] Keep `theme.py` only if it has other live exports; delete file if empty
- [x] Keep `components/styles.py` only if it has other live exports; delete file if empty
- [x] Delete `pages/history.py` (dead code, replaced by `run_history.py`)
- [x] Run `uv run pytest tests/platform/ -q` to verify nothing breaks

### Phase 4: Brand Consistency Test (NEW)

**File:** `tests/platform/test_brand_consistency.py` (NEW)

```python
"""Verify brand constants are consistent across .bat files and Python code."""

from __future__ import annotations

import re
from pathlib import Path

from platform_app.brand import COMPANY_NAME, PAGE_TITLE, PRODUCT_NAME, SHORT_NAME, TAGLINE, VERSION


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
        company_pattern = re.escape(COMPANY_NAME).replace(r"\|", r"[\|\\\|]")
        assert PRODUCT_NAME in content, f"{name} missing '{PRODUCT_NAME}'"
        assert re.search(company_pattern, content), f"{name} missing '{COMPANY_NAME}'"
```

This catches drift between `brand.py` and .bat files automatically in CI.

- [x] Create `tests/platform/test_brand_consistency.py`
- [x] Verify it passes

### Phase 5: Streamlit Config Improvements (NEW)

**File:** `packages/platform_app/src/platform_app/.streamlit/config.toml`

Add `[theme.sidebar]` section (real Streamlit feature since 1.36) and performance settings:

```toml
[server]
maxUploadSize = 100
maxMessageSize = 200

[browser]
gatherUsageStats = false

[runner]
fastReruns = true
magicEnabled = false

[theme]
primaryColor = "#16A34A"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8FAFC"
textColor = "#0F172A"
font = "sans serif"

[theme.sidebar]
backgroundColor = "#0F172A"
textColor = "#CBD5E1"
primaryColor = "#16A34A"
borderColor = "#1E293B"
```

Note: `[theme.sidebar]` handles base sidebar colors natively. The custom CSS in `app.py` is still needed for typography, nav item styling, and animations -- but base colors can move to config.

- [x] Add `[theme.sidebar]` section to config.toml
- [x] Add `[runner]` performance settings
- [x] Test that sidebar still renders correctly (CSS may need minor adjustments)

### Phase 6: Session State Keys and CSS Classes (KEEP LEGACY PREFIXES)

**Decision: Do NOT rename `uap_*` session state keys OR `uap-` CSS classes.**

**Rationale** (reviewer consensus from architecture, simplicity, and Python reviewers):
- Session state: 21 keys, 114 occurrences, silent breakage risk, no UI tests
- CSS classes: 224+ references, internal-only, no user benefit
- **Consistency**: If `uap_` stays because "internal-only", the same logic applies to `uap-`
- **Cost/benefit**: 224+ edits for zero user impact is textbook over-engineering
- Renaming one but not the other is inconsistent

Document in `brand.py` docstring (already included in Phase 1).

### ~~Phase 4 (DEFERRED): CSS Variable and Class Rename~~

Moved to optional future work. If ever needed, the approach is:
1. Find-and-replace `--uap-` -> `--rpe-` and `uap-` -> `rpe-` across all platform_app files
2. Verify: `grep -r "uap-\|--uap-" packages/platform_app/ --include="*.py"` returns 0 results
3. Manual visual regression test all 8 pages

---

## Platform Improvement Assessment

### Streamlit: Keep or Replace?

**Verdict: Keep Streamlit.** (Architecture strategist: 8.5/10 plan quality, APPROVE)

| Concern | Severity | Why |
|---------|---------|-----|
| Multi-user concurrency | LOW | ~10 CSMs, 2-3 concurrent max. CLI for heavy batch runs. |
| Layout control | MEDIUM | CSS injection works. Acceptable for orchestration UI. |
| Performance | LOW | UI is orchestration, not live dashboards. |
| Deployment/packaging | MEDIUM | .bat files work. Port kill fix shipped. |
| State management | LOW | 8 pages with shared session state is manageable. |
| Print/PDF export | N/A | Already generating PPTX/XLSX directly. |

**NiceGUI migration**: 2-4 weeks rewrite for `.exe` packaging. Not worth it.

### `st.logo()` Branding (Future, Needs Asset)

Streamlit 1.35+ supports `st.logo()` for sidebar branding:
```python
st.logo(
    image="packages/platform_app/src/platform_app/assets/logo_sidebar.svg",
    icon_image="packages/platform_app/src/platform_app/assets/logo_icon.svg",
    size="medium",
)
```

**Requirements**: White/light SVG logo (180-220px wide x 32px tall) for dark sidebar (#0F172A). Square icon (32x32) for collapsed sidebar. Place in `assets/` directory.

**Not in this plan** -- needs logo asset. Ready to implement once provided.

### Power BI Integration (Future)

Create a `.pbit` Power BI template that reads XLSX outputs. Zero Python changes needed.

### Shared Server Deployment (Future)

Run one Streamlit instance as a Windows service via NSSM/WinSW.

### Performance Opportunities (Future, Not Rebrand-Related)

From performance-oracle analysis:
1. `pd.read_excel()` on M: drive -- switch to `calamine` engine (2-3x faster)
2. Transaction file concat -- consider `polars` for multi-file combines
3. Module registry iteration -- cache sorted results with `@st.cache_resource`

---

## Files to Modify

| # | File | Change |
|---|------|--------|
| 1 | `packages/platform_app/src/platform_app/brand.py` | NEW -- brand constants |
| 2 | `packages/platform_app/src/platform_app/app.py` | Import brand, update page_title, sidebar footer, docstring |
| 3 | `packages/platform_app/src/platform_app/pages/home.py` | Header label, docstring |
| 4 | `packages/platform_app/src/platform_app/pages/outputs.py` | Docstring |
| 5 | `packages/platform_app/src/platform_app/pages/run_history.py` | Docstring |
| 6 | `packages/platform_app/src/platform_app/pages/module_library.py` | Docstring |
| 7 | `packages/platform_app/src/platform_app/pages/workspace.py` | Docstring |
| 8 | `packages/platform_app/src/platform_app/pages/data_ingestion.py` | Docstring |
| 9 | `packages/platform_app/src/platform_app/pages/run_analysis.py` | Docstring |
| 10 | `packages/platform_app/src/platform_app/pages/batch_workflow.py` | Docstring |
| 11 | `packages/platform_app/src/platform_app/cli.py` | Help text |
| 12 | `packages/platform_app/src/platform_app/theme.py` | Delete dead code or entire file |
| 13 | `packages/platform_app/src/platform_app/components/styles.py` | Delete dead code or entire file |
| 14 | `packages/platform_app/src/platform_app/pages/history.py` | DELETE (dead code) |
| 15 | `packages/platform_app/src/platform_app/.streamlit/config.toml` | Add sidebar theme + perf settings |
| 16 | `tests/platform/test_brand_consistency.py` | NEW -- brand drift test |
| 17 | `run.bat` | Banner text |
| 18 | `dashboard.bat` | Banner text |
| 19 | `run_batch.bat` | Banner text |
| 20 | `setup.bat` | Banner text |
| 21 | `pyproject.toml` (root) | Description |
| 22 | `config/platform.yaml` | Header comment |
| 23 | `README.md` | Header and description |
| 24 | `CLAUDE.md` | Header |
| 25 | `HANDOFF.md` | Header |
| 26 | `TECHNICAL.md` | Header |
| 27 | Various `__init__.py` | Docstrings |

## Verification

```bash
# Check for stale test imports before deleting dead code
grep -r "from.*theme.*import\|from.*styles.*import\|inject_theme\|inject_page_css" tests/

# Tests
uv run pytest tests/platform/ -q
uv run pytest tests/integration/ -q

# Lint
uv run ruff check packages/platform_app/
uv run ruff format --check packages/platform_app/

# Brand consistency
uv run pytest tests/platform/test_brand_consistency.py -v
```

## Checklist

- [x] `brand.py` created with module constants (not dataclass)
- [x] Browser tab title shows "RPE"
- [x] Sidebar footer shows "RPE v2.0 // ANALYSIS PLATFORM"
- [x] Home page header shows "RPE ANALYSIS PLATFORM"
- [x] All 4 .bat files show "RPE Analysis Platform" and "CSI | Velocity"
- [x] CLI help text updated
- [x] Dead CSS in `theme.py` and `styles.py` deleted
- [x] Dead `pages/history.py` deleted (already done in prior session)
- [x] `[theme.sidebar]` added to config.toml
- [x] `[runner]` performance settings added to config.toml
- [x] `test_brand_consistency.py` created and passing
- [x] `uap_*` session state keys preserved (documented in brand.py)
- [x] `uap-` CSS classes preserved (documented in brand.py)
- [x] Documentation headers updated
- [x] All tests pass (74 platform + 31 integration)
- [x] Ruff clean
