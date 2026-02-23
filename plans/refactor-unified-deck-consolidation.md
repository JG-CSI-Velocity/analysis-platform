# Unified Deck Consolidation -- 40-Slide Primary + Appendix

**Type:** refactor
**Date:** 2026-02-23
**Problem:** A client with ARS + ICS + TXN gets ~340 slides across multiple decks. CSMs can't present that. Need a single **Primary deck <= 40 slides** covering all active pipelines, plus a single **Appendix deck** for the rest.

## Current State

| Pipeline | Primary | Appendix | Notes |
|----------|---------|----------|-------|
| ARS | ~113 slides | ~23 | No primary/secondary split yet |
| ICS | ~27 slides | ~178 | Just split (Primary/Secondary) |
| TXN | 0 (no PPTX) | 0 | Excel + PNG only |

**Key insight from user:** "tables + charts for the same thing are redundant" -- appendix gets the table, primary gets the chart only.

## Target Architecture

### Primary Deck: <= 40 slides, one file

```
Title Slide (1)
Executive Dashboard (1)          -- cross-pipeline KPI panel
ARS Section (8-12 slides)        -- storyline-driven, chart-only
ICS Section (8-10 slides)        -- already done (PRIMARY_STORYLINE)
TXN Section (6-8 slides)         -- new: top merchants, competitors, trends
Insights & Actions (3-5 slides)  -- cross-pipeline takeaways
= 27-37 slides
```

Each section only appears if that pipeline ran. A client with only ARS gets ~15 slides. ARS + ICS + TXN gets ~35.

### Appendix Deck: unlimited, one file

Everything else: full tables, all charts, detailed breakdowns. Organized by pipeline section with dividers.

### Delivery per client

```
{ClientID}_Primary_YYYYMMDD.pptx     -- CSM presents this
{ClientID}_Appendix_YYYYMMDD.pptx    -- reference/drill-down
{ClientID}_Report_YYYYMMDD.xlsx      -- data tables (already exists)
```

---

## Phase 1: ARS Primary/Secondary Split

ARS currently dumps ~136 slides into one deck. Apply the same pattern as ICS.

### 1.1 Define ARS_PRIMARY_STORYLINE

**File:** `packages/ars_analysis/src/ars_analysis/output/deck_builder.py`

Pick the ~12 most impactful ARS slides organized by narrative:

```python
ARS_PRIMARY_STORYLINE = {
    "How Active Are Debit Cards?": [
        "DCTR-1",                           # Overall DCTR (historical + L12M)
        ("DCTR-3", "DCTR-5"),               # Personal vs Business side-by-side
        ("A7.7", "A7.8"),                    # Funnel: Historical vs TTM (already merged)
    ],
    "What's the Revenue Impact?": [
        "A11.1",                             # Value of Debit Card
        "A11.2",                             # Value of Reg E
    ],
    "Are Members Opting In?": [
        "A8.3",                              # Reg E status overview
        ("A8.10", "A8.11"),                  # Reg E funnel (already merged)
    ],
    "What's the Attrition Story?": [
        "A9.1",                              # Overall attrition rate
        "A9.9",                              # Debit retention
        "A9.11",                             # Revenue lost
    ],
    "What Should We Do Next?": [
        "S1",                                # Synthesis: program health
        "S6",                                # Conclusion: recommendations
    ],
}
```

This gives ~12-14 slides (with merges). The remaining ~120 go to appendix.

### 1.2 Implement write_ars_primary() and write_ars_secondary()

**File:** `packages/ars_analysis/src/ars_analysis/output/deck_builder.py`

Follow the exact pattern from ICS `pptx.py`:
- `write_ars_primary()` -- chart-only, storyline sections, ARS-style dark dividers, merged pairs
- `write_ars_secondary()` -- everything (rename from current `build_deck`)
- `write_ars_reports()` -- orchestrator returning (primary_path, secondary_path)

### 1.3 Update ARS pipeline to produce both decks

**File:** `packages/ars_analysis/src/ars_analysis/pipeline/steps/generate.py`

Change from single deck output to dual deck output.

### 1.4 Tests

- Primary deck <= 20 slides (ARS alone)
- All storyline sections present
- No tables in primary
- All slides appear in secondary
- Backward compat: secondary matches old full deck

---

## Phase 2: TXN Primary Slides

TXN has no PPTX output. Add a minimal primary-only builder (no secondary -- Excel covers the detail).

### 2.1 Define TXN_PRIMARY_STORYLINE

**File:** `packages/txn_analysis/src/txn_analysis/exports/pptx_primary.py` (new)

```python
TXN_PRIMARY_STORYLINE = {
    "Where Are Members Spending?": [
        "top_merchants_by_spend",            # Top 10 merchants bar chart
        ("mcc_by_spend", "mcc_by_accounts"), # MCC breakdown side-by-side
    ],
    "Who's the Competition?": [
        "competitor_high_level",             # Competitor overview
        "competitor_threat_assessment",      # Threat scatter
    ],
    "What Are the Trends?": [
        "monthly_rank_tracking",             # Rank trajectory
        "growth_leaders_decliners",          # Growth leaders
    ],
    "Business vs Personal": [
        ("business_top_by_spend", "personal_top_by_spend"),  # Side-by-side
    ],
}
```

~8-10 slides. Uses existing PNG charts from the chart registry.

### 2.2 Implement write_txn_primary()

- Same slide-building helpers (dark dividers, merged pairs, chart-only)
- Read chart PNGs from pipeline result
- No table slides

### 2.3 Wire into TXN pipeline

**File:** `packages/txn_analysis/src/txn_analysis/pipeline.py`

Add PPTX export step after Excel export.

### 2.4 Tests

- Creates file
- <= 15 slides
- No tables
- Has section dividers

---

## Phase 3: Unified Deck Composer

A top-level function that combines primary slides from all active pipelines into one deck.

### 3.1 Create unified composer

**File:** `packages/shared/src/shared/deck_composer.py` (new)

```python
def compose_unified_deck(
    pipelines: dict[str, Path],  # {"ars": primary.pptx, "ics": primary.pptx, "txn": primary.pptx}
    output_path: Path,
    client_name: str,
    template_path: Path | None = None,
) -> Path:
    """Merge multiple primary decks into one unified presentation."""
```

Logic:
1. Create new presentation from template
2. Add unified title slide (client name, date, which pipelines ran)
3. Add cross-pipeline executive KPI slide (optional -- if all results available)
4. For each pipeline that ran:
   - Copy all slides from that pipeline's primary deck
5. Save unified deck

This is simpler than re-generating -- just concatenate the already-curated primary decks.

### 3.2 Create unified appendix composer

Same approach -- concatenate appendix/secondary decks with pipeline dividers between them.

### 3.3 Wire into platform orchestrator

**File:** `packages/platform_app/src/platform_app/orchestrator.py`

After all pipelines run, call `compose_unified_deck()` with whichever primary decks were produced.

### 3.4 Tests

- Single pipeline: unified deck = that pipeline's primary
- Two pipelines: both sections present
- Three pipelines: all present, <= 40 slides
- Appendix: all secondary content preserved

---

## Phase 4: Slim Down ARS Preamble

The ARS preamble has 13 fixed slides (P01-P13), many blank placeholders for manual data. These bloat the primary deck.

### 4.1 Move manual/blank slides to appendix

Keep in primary: P01 (title), P02 (agenda)
Move to appendix: P04-P06 (blank financial tables), P10 (blank data check), P12 (blank results)

Saves ~5 slides from the ARS primary section.

### 4.2 Wire mailer revisit into storyline

P08/P09 (mailer revisit swipes/spend) should be part of the storyline, not preamble. Move into the "What Should We Do Next?" section as a merged pair.

---

## File Changes

| # | File | Change |
|---|------|--------|
| 1 | `packages/ars_analysis/src/ars_analysis/output/deck_builder.py` | Add ARS_PRIMARY_STORYLINE, write_ars_primary(), write_ars_secondary() |
| 2 | `packages/ars_analysis/src/ars_analysis/pipeline/steps/generate.py` | Dual deck output |
| 3 | `packages/txn_analysis/src/txn_analysis/exports/pptx_primary.py` | New: TXN primary PPTX builder |
| 4 | `packages/txn_analysis/src/txn_analysis/pipeline.py` | Wire PPTX export |
| 5 | `packages/shared/src/shared/deck_composer.py` | New: unified deck composer |
| 6 | `packages/platform_app/src/platform_app/orchestrator.py` | Wire unified composition |
| 7 | Tests for each phase |

## Acceptance Criteria

- [ ] ARS primary deck <= 15 slides (chart-only, storyline-driven)
- [ ] ICS primary deck <= 12 slides (already done)
- [ ] TXN primary deck <= 10 slides (chart-only, new)
- [ ] Unified primary deck <= 40 slides (all 3 pipelines combined)
- [ ] Single appendix deck with all detail
- [ ] No tables in any primary deck
- [ ] Tests pass, ruff clean

## Verification

```bash
uv run pytest tests/ -q
uv run ruff check packages/
```
