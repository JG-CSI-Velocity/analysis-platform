# Improve Analysis Output Quality: Presentation, Excel, and UI

**Type:** feat
**Date:** 2026-02-23
**Status:** Draft

---

## Overview

The platform produces 100+ analyses across 3 pipelines (ARS, TXN, ICS) but the output quality is inconsistent: three separate Excel exporters with different styling, duplicated deck builders, no PPTX for TXN, static PNG charts in the Streamlit dashboard, and no unified cross-pipeline deliverable. This plan addresses the highest-impact improvements in priority order.

## Problem Statement

CSMs run analyses for 300+ credit union clients and deliver PPTX decks + Excel workbooks. Current pain points:

1. **No TXN PPTX** -- the transaction pipeline produces only Excel + standalone PNGs. CSMs must manually assemble TXN slides.
2. **Three different Excel formats** -- navy headers are three different hex values (#2E4057, #1B365D, #1E3D59), chart embed sizes differ (900x500 vs 800x480), TXN and ICS exporters are 90% identical code.
3. **Static charts in UI** -- TXN generates Plotly figures but the Outputs page renders everything as static PNGs. No hover, zoom, or interactivity.
4. **No unified deliverable** -- a client with ARS + ICS + TXN gets 3-5 separate output files. No single "executive summary" deck exists.
5. **Inconsistent narratives** -- ARS has consultant-quality S1-S8 synthesis narratives. TXN `summary` fields are often empty. ICS is partial.
6. **Duplicated code** -- `SlideContent` dataclass, color palettes, Excel styles defined independently in each pipeline.

## Proposed Solution

Four phases, ordered by impact and dependency:

---

## Phase 1: Unify Shared Infrastructure (Foundation)

Extract duplicated code into `shared/` so subsequent phases build on a single foundation.

### 1A. Move `SlideContent` to shared types

- [ ] Add `SlideContent` frozen dataclass to `shared/types.py`
- [ ] Fields: `slide_type`, `title`, `subtitle`, `images`, `kpis`, `bullets`, `source`, `footnotes`, `layout_index`, `notes`
- [ ] Update ARS `deck_builder.py` to import from `shared.types`
- [ ] Update ICS `deck_builder.py` to import from `shared.types`
- [ ] Delete duplicated definitions

**Files:**
- `packages/shared/src/shared/types.py` -- add SlideContent
- `packages/ars_analysis/src/ars_analysis/output/deck_builder.py` -- import from shared
- `packages/ics_toolkit/src/ics_toolkit/analysis/exports/deck_builder.py` -- import from shared

### 1B. Unify Excel export base

- [ ] Create `shared/excel_report.py` with `ExcelReportBase` class
- [ ] Extract common logic: `_register_styles(wb)`, `_write_cover_sheet()`, `_write_toc_sheet()`, `_write_analysis_sheet()`
- [ ] Configurable constants: `HEADER_COLOR`, `CHART_WIDTH`, `CHART_HEIGHT`
- [ ] Single authority: header color = `#2E4057` (matches `shared/charts.py`)
- [ ] Migrate TXN `excel_report.py` to inherit from base (override percentage handling)
- [ ] Migrate ICS `excel.py` to inherit from base
- [ ] Route all `wb.save()` calls through `shared/excel.py:save_workbook()` (retry logic for M: drive)
- [ ] Add conditional formatting: green/red variance columns, data bars for volume columns

**Files:**
- `packages/shared/src/shared/excel_report.py` -- NEW shared base class
- `packages/txn_analysis/src/txn_analysis/exports/excel_report.py` -- refactor to inherit
- `packages/ics_toolkit/src/ics_toolkit/analysis/exports/excel.py` -- refactor to inherit

### 1C. Consolidate color palette

- [ ] Make `shared/charts.py:COLORS` the single import authority for base colors
- [ ] Add semantic color mappings: `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `HIGHLIGHT`
- [ ] Per-pipeline style modules import base colors and define domain-specific aliases:
  - ARS: `PERSONAL = COLORS["primary"]`, `BUSINESS = COLORS["accent"]`
  - TXN: Register Plotly template from shared colors
  - ICS: Map business-goal colors to shared base

**Files:**
- `packages/shared/src/shared/charts.py` -- expand with semantic colors
- `packages/ars_analysis/src/ars_analysis/charts/style.py` -- import from shared
- `packages/txn_analysis/src/txn_analysis/charts/theme.py` -- import from shared
- `packages/ics_toolkit/src/ics_toolkit/analysis/charts/style.py` -- import from shared

### Verification (Phase 1)

```bash
uv run pytest tests/ -q        # all tests pass
uv run ruff check packages/    # lint clean
# Visual: run each pipeline, compare PPTX/XLSX side-by-side for consistency
```

---

## Phase 2: TXN PPTX Builder + Action Titles

### 2A. Build TXN deck builder

- [ ] Create `txn_analysis/exports/deck_builder.py` using shared `SlideContent`
- [ ] Define `TXN_PRIMARY_STORYLINE` -- curated 6-8 slide narrative:
  - Section: Portfolio Overview (scorecard, member segments)
  - Section: Top Merchants & Categories (M1 spend, M2 MCC, M3/M4 biz/personal)
  - Section: Competitive Landscape (M6 competitor high-level, threat assessment)
  - Section: Behavioral Insights (M15 recurring, M16 time patterns, M17 demographics)
- [ ] Chart source: read from `chart_pngs` dict (in-memory PNG bytes, same as Excel path)
- [ ] Use shared template (or blank widescreen if no template available)
- [ ] Wire into `txn_analysis/pipeline.py` export step
- [ ] Add CLI flag: `--pptx` / `--no-pptx` (default: enabled)

**Files:**
- `packages/txn_analysis/src/txn_analysis/exports/deck_builder.py` -- NEW
- `packages/txn_analysis/src/txn_analysis/pipeline.py` -- wire export
- `packages/txn_analysis/src/txn_analysis/settings.py` -- add pptx output toggle

### 2B. Add action titles to AnalysisResult

- [ ] Convention: `metadata["action_title"]` holds an insight sentence
- [ ] Pattern: `"{metric} {direction} {magnitude} -- {context}"`
  - Example: `"67% DCTR -- 5pp below peer median of 72%"`
  - Example: `"Netflix leads recurring payments across 1,200 accounts"`
- [ ] Add `_generate_action_title()` helper to each analysis that computes a declarative title from the result data
- [ ] PPTX builders prefer `metadata["action_title"]` over `title` for slide titles
- [ ] Streamlit Outputs page shows action title in Key Findings cards
- [ ] Start with TXN (new, clean) then extend to ICS (has partial support) then ARS

**Files:**
- `packages/txn_analysis/src/txn_analysis/analyses/*.py` -- add action titles to each module
- `packages/platform_app/src/platform_app/pages/outputs.py` -- prefer action_title

### 2C. Add source footers to charts

- [ ] TXN: `add_source_footer(fig, client_name, date_range)` already exists in theme.py -- wire into all chart builders
- [ ] ARS: Add `fig.text(0.05, 0.02, source, ...)` to `chart_figure()` context manager
- [ ] ICS: Add source parameter to `chart_figure()` guard

### Verification (Phase 2)

```bash
uv run pytest tests/txn/ -q
# E2E: generate TXN PPTX from synthetic data
uv run python -m txn_analysis tests/e2e_data/8888_transactions.csv -o /tmp/txn_out --pptx
# Open /tmp/txn_out/*.pptx and verify slide titles are action titles, not labels
```

---

## Phase 3: Interactive Streamlit Dashboard

### 3A. Interactive Plotly charts for TXN

- [ ] Store Plotly `go.Figure` objects in `AnalysisResult.metadata["plotly_fig"]`
- [ ] Outputs page Charts tab: detect `plotly_fig` in metadata
  - If present: `st.plotly_chart(fig, use_container_width=True)`
  - If absent: `st.image(chart_path)` (ARS/ICS static PNGs)
- [ ] Add visual indicator: "Interactive" badge on Plotly charts
- [ ] Memory guard: clear `plotly_fig` from session state when switching clients

**Files:**
- `packages/txn_analysis/src/txn_analysis/charts/__init__.py` -- store fig in result metadata
- `packages/platform_app/src/platform_app/pages/outputs.py` -- detect and render Plotly

### 3B. Enhanced Key Findings

- [ ] Round-robin pipeline selection: take findings from each active pipeline before repeating
- [ ] Sort by `metadata.get("dollar_impact", 0)` descending within each pipeline
- [ ] Show up to 9 findings (3 per pipeline) in 3x3 grid
- [ ] Each card shows: action title (bold), summary text, pipeline badge

**Files:**
- `packages/platform_app/src/platform_app/pages/outputs.py` -- rewrite findings logic

### 3C. Per-chart download buttons

- [ ] Add download button below each chart in the Charts tab
- [ ] PNG download from `chart_path` or `plotly_fig.to_image()`
- [ ] Data download: CSV export of `result.df` for each analysis

**Files:**
- `packages/platform_app/src/platform_app/pages/outputs.py` -- add download buttons

### 3D. Fix deprecated API usage

- [ ] Replace `width="stretch"` with `use_container_width=True` in `components/results_display.py`

### Verification (Phase 3)

```bash
uv run pytest tests/platform/ -q
# Manual: run Streamlit, execute TXN pipeline, verify interactive charts in Outputs
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

---

## Phase 4: Unified Cross-Pipeline Deliverables (Future)

### 4A. Unified deck composer

- [ ] Create `shared/deck_composer.py`
- [ ] Architecture: re-render from `SlideContent` objects (not slide copying between .pptx files)
- [ ] Each pipeline's runner produces `list[SlideContent]` as output
- [ ] Composer assembles: Cover -> Executive Summary -> per-pipeline sections -> Appendix
- [ ] Target: <= 40 primary slides
- [ ] Wire into platform orchestrator when all 3 pipelines run

### 4B. Unified Excel workbook

- [ ] Single workbook with pipeline-prefixed sheet names (`ARS_DCTR`, `TXN_M1`, `ICS_Portfolio`)
- [ ] Master Summary sheet with cross-pipeline KPIs
- [ ] Master TOC with hyperlinks to all sheets

### 4C. Narrative templates for TXN

- [ ] Port the ARS S1-S8 narrative pattern to TXN
- [ ] TXN "story arc": Portfolio Health -> Competitive Position -> Behavioral Insights -> Opportunities
- [ ] Template-based sentences with conditional branches (improving/declining/stable)
- [ ] Populate `summary` field on all 39 TXN analyses

### 4D. Anomaly detection

- [ ] Define anomaly types: statistical outliers, period-over-period spikes, branch divergence
- [ ] Output: enhance `summary` field with anomaly callouts
- [ ] Surface in Key Findings with "Alert" badge
- [ ] Start with TXN (clean data, numerical metrics) then extend

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Slide composition mechanism | Re-render from `SlideContent` objects | python-pptx cannot copy slides between presentations; SlideContent is already the abstraction both ARS and ICS use |
| Excel header color | `#2E4057` | Already in `shared/excel.py` and `shared/charts.py:COLORS["primary"]` |
| Interactive charts | Plotly for TXN only (pilot) | ARS/ICS recently moved to matplotlib; converting back would be wasteful. TXN already has Plotly figures. |
| Action title storage | `metadata["action_title"]` | No schema change to AnalysisResult; backward compatible |
| Kaleido strategy | Keep pinned at 0.2.1 | ICS fallback (plotly_to_png renderer) proves matplotlib conversion is viable if needed |
| Anomaly output | Enhance `summary` field | Minimal change, surfaces in existing Key Findings UI |
| Chart source for TXN PPTX | In-memory PNG bytes from `chart_pngs` dict | Same path as Excel embedding; no disk I/O or kaleido re-invocation |

## Risks

| Risk | Mitigation |
|------|-----------|
| Kaleido 0.2.1 deprecated by Plotly | ICS `plotly_to_png()` renderer proves matplotlib fallback works. Can convert TXN charts to matplotlib if needed. |
| Color palette change breaks visual consistency | Phase 1C is cosmetic only -- no functional changes. Compare before/after screenshots. |
| Excel format change affects downstream consumers | Keep column headers and sheet names identical. Only styling (header color, borders) changes. |
| TXN PPTX adds maintenance burden | Uses shared `SlideContent` and shared deck infrastructure. Follows existing ICS pattern. |
| Interactive charts consume browser memory | Clear `plotly_fig` from session state when switching clients. Limit to TXN only (39 analyses max). |

## Success Metrics

- All three pipelines produce visually consistent Excel workbooks (same header color, same zebra striping, same chart embed size)
- TXN pipeline produces a 6-8 slide PPTX deck alongside Excel
- TXN charts are interactive in Streamlit (hover tooltips, zoom)
- 80%+ of analyses have a populated `action_title` in metadata
- Key Findings in Outputs page shows findings from all active pipelines (not just ARS)
- Zero regression: existing tests pass, existing output files are structurally equivalent

## Implementation Order

| Phase | Effort | Impact | Dependencies |
|-------|--------|--------|-------------|
| 1A: SlideContent to shared | ~1 hour | Foundation | None |
| 1B: Excel base class | ~1 day | High (eliminates 250 lines of duplication) | None |
| 1C: Color palette | ~2 hours | Medium (visual consistency) | None |
| 2A: TXN PPTX builder | ~1 day | High (fills biggest gap) | 1A |
| 2B: Action titles | ~1 day | High (output quality) | None |
| 2C: Source footers | ~2 hours | Medium | None |
| 3A: Interactive charts | ~4 hours | High (UX improvement) | None |
| 3B: Enhanced findings | ~2 hours | Medium | 2B |
| 3C: Per-chart downloads | ~2 hours | Medium | 3A |
| 3D: Fix deprecated API | ~15 min | Low | None |
| 4A: Unified composer | ~2 days | High | 1A, 2A |
| 4B: Unified Excel | ~4 hours | Medium | 1B |
| 4C: TXN narratives | ~1 day | High | 2B |
| 4D: Anomaly detection | ~1 day | Medium | 4C |

## References

### Internal
- Consolidation plan: `plans/refactor-unified-deck-consolidation.md`
- ARS deck builder: `packages/ars_analysis/src/ars_analysis/output/deck_builder.py`
- ICS PPTX system: `packages/ics_toolkit/src/ics_toolkit/analysis/exports/pptx.py`
- TXN chart registry: `packages/txn_analysis/src/txn_analysis/charts/__init__.py`
- Shared types: `packages/shared/src/shared/types.py`
- Shared Excel: `packages/shared/src/shared/excel.py`
- Outputs page: `packages/platform_app/src/platform_app/pages/outputs.py`
- ARS narrative gold standard: `packages/ars_analysis/src/ars_analysis/analytics/insights/synthesis.py`

### External
- [python-pptx docs](https://python-pptx.readthedocs.io/en/latest/)
- [openpyxl conditional formatting](https://openpyxl.readthedocs.io/en/stable/formatting.html)
- [Streamlit st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)
- [Consulting slide structure (McKinsey/BCG/Bain)](https://www.theanalystacademy.com/consulting-slide-structure/)
- [Kaleido performance issue #400](https://github.com/plotly/Kaleido/issues/400)
