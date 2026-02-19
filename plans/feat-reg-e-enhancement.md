# Reg E Analysis Enhancement Plan

**Working directory:** `~/Desktop/analysis_platform/`
**Module:** `packages/ars_analysis/src/ars_analysis/reg_e.py` (2,243 lines, 14 analysis functions + suite runner)
**Current state:** 14 analyses (A8.1-A8.13 + A8.4b) = ~11 slides, 2 commented out (A8.8, A8.9)
**Test coverage:** 9 tests (vs 104 for DCTR) -- only A8.1 has individual function tests

---

## Gap Analysis vs Enhanced DCTR

The DCTR module was recently enhanced (Sprints 0-5) with:
- Sub-package split (8 modules)
- Executive summary slide
- Opportunity sizing with benchmarks
- Months-to-transact analysis
- Cohort capture analysis
- Product type breakdown
- Enhanced seasonality (YoY overlay)
- Enhanced vintage (maturity curves)
- Cross-tab heatmaps (3 new)
- Config-driven benchmark targets
- 104 tests

Reg E is missing ALL of these enhancements. Specifically:

| Feature | DCTR | Reg E |
|---------|------|-------|
| Sub-package split | 8 modules | Monolithic 2,243-line file |
| Executive summary | A7.0 slide | Missing |
| Opportunity sizing | A7.18 with benchmarks | Missing (`reg_e_target` loaded but unused) |
| Cohort analysis | A7.20 cohort capture | Missing |
| Seasonality | YoY overlay | Missing entirely |
| Vintage/maturity | Cross-sectional curves | Missing |
| Cross-tab heatmaps | 3 new (A7.22-24) | A8.8 COMMENTED OUT |
| Config benchmarks | `dctr_targets` used | `reg_e_target` UNUSED |
| Figure cleanup | `finally: plt.close` | No try/finally |
| Hardcoded years | Fixed | Still present |
| REG_ORDER | Exported from `_suite.py` | Inline in `run_reg_e_suite()` |
| MERGES/APPENDIX | Co-located in dctr package | In pipeline.py |
| Test count | 104 | 9 |
| Consultant subtitles | Enhanced | Mechanical |

---

## Current Reg E Inventory

| ID | Function | What it does | Slide? |
|----|----------|-------------|--------|
| A8.1 | `run_reg_e_1` | Overall Reg E status (donut chart) | Slide |
| A8.2 | `run_reg_e_2` | Historical by Year + Decade (bar charts) | Slide (appendix) |
| A8.3 | `run_reg_e_3` | L12M Monthly opt-in rates (bar + line) | Slide |
| A8.4a | `run_reg_e_4` | Branch horizontal bars + scatter (A8.4a + A8.4c) | Slide + appendix |
| A8.4b | `run_reg_e_4b` | Branch vertical bars | Slide (appendix) |
| A8.5 | `run_reg_e_5` | By Account Age (bar chart) | Slide |
| A8.6 | `run_reg_e_6` | By Account Holder Age (grouped bar) | Slide |
| A8.7 | `run_reg_e_7` | By Product Code (bar + scatter) | Slide (appendix) |
| A8.8 | `run_reg_e_8` | Monthly Heatmap (branch x month) | COMMENTED OUT |
| A8.9 | `run_reg_e_9` | Branch Performance Summary Table | COMMENTED OUT |
| A8.10 | `run_reg_e_10` | All-Time Account Funnel with Reg E | Slide |
| A8.11 | `run_reg_e_11` | L12M Funnel with Reg E | Slide |
| A8.12 | `run_reg_e_12` | 24-Month Reg E Trend (line chart) | Slide (appendix) |
| A8.13 | `run_reg_e_13` | Complete Branch x Month Pivot Table | Data only |

---

## Enhancement Opportunities

### Phase A: New Analyses (High Value)

#### A1. Reg E Executive Summary Slide (NEW)
**What:** Single "Reg E At a Glance" KPI dashboard synthesizing all findings.
**Why:** Mirrors DCTR A7.0. Consultants need a one-slide summary.

**Implementation:**
- New function `run_reg_e_executive_summary(ctx)` -- runs LAST
- KPI boxes: Overall opt-in rate, L12M trend direction, best/worst branch, biggest opportunity segment
- 3-4 bullet insight paragraph
- Slide ID: `A8.0 - Reg E Executive Summary`
- Placed FIRST in Reg E section

**Data needed:** Reads from `ctx["results"]["reg_e_*"]` (all prior analyses)

---

#### A2. Reg E Opportunity Sizing (NEW)
**What:** Quantify account/revenue opportunity if opt-in rate improved to target.
**Why:** "Your opt-in rate is 42%" is informational; "Improving to 60% would capture 3,200 additional opted-in accounts worth $X in fee income" is actionable.

**Implementation:**
- New function `run_reg_e_opportunity(ctx)`
- Use `ctx["reg_e_target"]` (0.60, already loaded but unused!)
- Calculate at 3 levels: current, target (0.60), best-in-class (0.75)
- For each: `additional_accounts = eligible_base * (target - current_rate)`
- Revenue impact: `additional_accounts * ctx["nsf_od_fee"]` (fee income per opted-in account)
- Waterfall chart: Current -> Target -> Best-in-class
- Slide ID: `A8.14 - Reg E Opportunity`

**Edge Cases:**
- Current rate already above target -- show "above benchmark" message
- No `nsf_od_fee` configured -- show account count only
- Zero eligible base -- skip

---

#### A3. Reg E Cohort Analysis (NEW)
**What:** For each monthly cohort of new accounts (L12M), what % have opted in at snapshot date?
**Why:** Mirrors DCTR A7.20 cohort capture. Shows onboarding effectiveness for Reg E consent.

**Implementation:**
- New function `run_reg_e_cohort(ctx)`
- Filter to accounts opened in L12M
- For each monthly cohort: `opt_in_rate = count(Opted In) / count(total eligible)`
- Line chart: x = opening month, y = opt-in rate
- Overlay: separate lines for Personal vs Business
- Slide ID: `A8.15 - Reg E Cohort Analysis`

**Edge Cases:**
- Only 1-2 months of data -- table instead of chart
- No eligible accounts in a cohort month -- skip that point

---

#### A4. Reg E Seasonality (NEW)
**What:** Monthly/quarterly opt-in rate patterns with YoY overlay.
**Why:** Reg E consent rates may vary by season (e.g., tax season, back-to-school). YoY context shows whether patterns are recurring or new.

**Implementation:**
- New function `run_reg_e_seasonality(ctx)`
- Panel 1: Monthly average opt-in rate by calendar month (all history)
- Panel 2: Current year vs prior year overlay (solid vs dashed, green/red zones)
- Slide ID: `A8.16 - Reg E Seasonality`

---

### Phase B: Enhance Existing Analyses

#### B1. Uncomment A8.8 and A8.9
**What:** Re-enable the commented-out heatmap and branch summary analyses.
**Why:** These functions exist and work -- they were just excluded from the slide mapping. With the appendix system, they belong in the appendix.

**Implementation:**
- Uncomment `run_reg_e_8` and `run_reg_e_9` calls in suite runner
- Add to REG_ORDER and REGE_APPENDIX_IDS
- Verify they produce valid slides

---

#### B2. Consultant-Grade Subtitles
**What:** Upgrade mechanical subtitles to contextual insights.
**Why:** Current: "42.3% Opt-In Rate". Better: "Opt-in at 42%, trailing 60% target by 18pp -- Branch North leads at 58%"

**Implementation:**
- Enhance subtitle strings inline in each `run_reg_e_*` function
- Pattern: [Key metric] + [Benchmark comparison] + [Standout detail]
- Do incrementally as each function is touched

---

#### B3. Use `reg_e_target` as Benchmark Reference Lines
**What:** Add horizontal reference lines at `reg_e_target` (0.60) on all opt-in rate charts.
**Why:** The target is loaded from config but never displayed. Every chart should show where the CU stands vs target.

**Implementation:**
- In each chart function, add: `ax.axhline(y=ctx["reg_e_target"], color="red", linestyle="--", alpha=0.5, label=f"Target ({ctx['reg_e_target']:.0%})")`
- Update legends to include the target line

---

### Phase C: Structural Improvements

#### C1. Sub-Package Split
**What:** Split monolithic reg_e.py (2,243 lines) into a sub-package.
**Why:** Mirrors DCTR split. Maintainability at scale.

**Implementation:**
```
reg_e/
  __init__.py          ~40 lines   (re-exports + __all__)
  _helpers.py          ~60 lines   (_report, _fig, _save_chart, _slide, _save, _rege, _opt_list, _reg_col, _total_row)
  _core.py             ~1400 lines (run_reg_e_1 through run_reg_e_13 + new analyses)
  _visualizations.py   ~400 lines  (chart-heavy functions if needed, or keep in _core.py)
  _suite.py            ~120 lines  (run_reg_e_suite + REG_ORDER + REGE_MERGES + REGE_APPENDIX_IDS)
```

**Key changes:**
- Move REGE_MERGES and REGE_APPENDIX_IDS from pipeline.py to `reg_e/_suite.py`
- Export REG_ORDER (currently inline in suite runner)
- Update pipeline.py to import from reg_e package
- `from ars_analysis.reg_e import run_reg_e_suite` still works via `__init__.py`

---

#### C2. Fix Hardcoded Values
**What:** Replace hardcoded year lists and y-axis limits.
**Why:** Same issue as DCTR -- these break as time passes.

**Implementation:**
- Audit all year references in reg_e.py
- Replace with dynamic `range(start_year, current_year + 1)`
- Fix any hardcoded axis limits to be data-driven

---

#### C3. Add Figure Cleanup
**What:** Add `finally: plt.close(fig)` to all chart functions.
**Why:** Prevents matplotlib memory leaks (~15MB per unclosed figure).

---

#### C4. Move `import traceback` to Module Top
**What:** `import traceback` is inside `run_reg_e_suite._safe()`.
**Why:** Module-level imports are cleaner and avoid repeated import overhead.

---

## Slide Order (Proposed)

```
# Main Reg E Section
A8.0  - Reg E Executive Summary            (NEW)
A8.1  - Reg E Overall Status               (existing)
A8.12 - Reg E Trend                         (existing)
A8.3  - Reg E L12M Monthly                  (existing)
A8.11 - Reg E L12M Funnel                   (existing)
A8.10 - Reg E All-Time Funnel               (existing)
A8.14 - Reg E Opportunity                   (NEW)
A8.5  - Reg E by Account Age               (existing)
A8.6  - Reg E by Holder Age                 (existing)
A8.4b - Reg E by Branch (Vertical)          (existing)
A8.4a - Reg E by Branch                     (existing)
A8.15 - Reg E Cohort Analysis               (NEW)

# Appendix
A8.16 - Reg E Seasonality                   (NEW)
A8.4c - Reg E Branch Scatter                (existing)
A8.7  - Reg E by Product                    (existing)
A8.2  - Reg E Historical                    (existing)
A8.8  - Reg E Monthly Heatmap               (re-enabled)
A8.9  - Reg E Branch Summary                (re-enabled)
A8.13 - Branch x Month Pivot                (existing, data only)
```

---

## Implementation Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 0 | C2. Fix hardcoded values | Low | Critical -- correctness |
| 0 | C3. Add figure cleanup | Low | High -- memory |
| 0 | C4. Move traceback import | Trivial | Cleanup |
| 0 | Test infrastructure (smoke tests for all 14 functions) | Medium | Safety net |
| 1 | C1. Sub-package split | Medium | Maintainability |
| 1 | Move REGE_MERGES/APPENDIX to reg_e package | Low | Co-location |
| 2 | B1. Uncomment A8.8/A8.9 | Trivial | Appendix completeness |
| 2 | B3. Benchmark reference lines | Low | High -- makes `reg_e_target` useful |
| 3 | A2. Opportunity Sizing | Medium | Very High -- actionable dollars |
| 3 | A1. Executive Summary | Medium | Very High -- the "so what" |
| 4 | A3. Cohort Analysis | Medium | High -- onboarding effectiveness |
| 5 | A4. Seasonality | Medium | Medium -- pattern insight |
| 5 | B2. Consultant subtitles | Low | High -- quality upgrade |

---

## Execution Plan

### Sprint 0: Foundations (no behavior change)
1. Fix hardcoded year lists in reg_e.py (audit all year references)
2. Add `finally: plt.close(fig)` to all chart try/except blocks
3. Move `import traceback` to module top level
4. Create smoke tests for all 14 existing `run_reg_e_*` functions
   - Pattern: call function, verify (a) returns ctx, (b) appends expected slide ID, (c) creates chart PNG, (d) calls `_save_to_excel`
5. **Verify:** `make test` passes, existing analyses still produce same output

### Sprint 1: Sub-Package Split (pure refactor)
1. Create `reg_e/` package directory
2. Extract `_helpers.py` (9 helper functions)
3. Extract `_core.py` (all 14 `run_reg_e_*` functions)
4. Extract `_suite.py` (suite runner + REG_ORDER + REGE_MERGES + REGE_APPENDIX_IDS)
5. Create `__init__.py` with re-exports
6. Update pipeline.py to import REGE_MERGES/APPENDIX from reg_e package
7. **Verify:** `make test` passes, `from ars_analysis.reg_e import run_reg_e_suite` still works

### Sprint 2: Quick Wins (B1, B3)
1. Uncomment A8.8 and A8.9 in suite runner
2. Add to REG_ORDER and REGE_APPENDIX_IDS
3. Add `reg_e_target` benchmark reference lines to all opt-in rate charts
4. Update REG_ORDER with new slide positions
5. Add tests for A8.8, A8.9, and benchmark lines
6. **Verify:** `make test` passes, 2 more appendix slides appear

### Sprint 3: Executive Summary + Opportunity (A1, A2)
1. Build `run_reg_e_opportunity(ctx)` with waterfall chart using `reg_e_target`
2. Build `run_reg_e_executive_summary(ctx)` reading from all results
3. Update REG_ORDER
4. Add tests (~15 per function)
5. **Verify:** `make test` passes, 2 new main slides

### Sprint 4: Cohort + Seasonality (A3, A4)
1. Build `run_reg_e_cohort(ctx)` with monthly cohort opt-in curve
2. Build `run_reg_e_seasonality(ctx)` with YoY overlay
3. Update REG_ORDER
4. Add tests (~12 per function)
5. **Verify:** `make test` passes, 2 new slides

### Sprint 5: Polish (B2)
1. Upgrade subtitle text on all Reg E slides to consultant-grade
2. Final cleanup pass
3. **Verify:** `make test` passes

---

## Data Dependencies

All analyses use data already available in ctx:
- **Opportunity (A2):** `ctx["reg_e_target"]` (already loaded), `ctx["nsf_od_fee"]` (already loaded), `ctx["reg_e_eligible_base"]`
- **Cohort (A3):** `ctx["open_accounts"]`, `Date Opened`, Reg E column, L12M range
- **Seasonality (A4):** `ctx["reg_e_eligible_base"]`, `Date Opened`, Reg E column
- **Executive Summary (A1):** `ctx["results"]["reg_e_*"]` (all prior analyses)

No new ODD columns needed. All data inputs already exist.

---

## Test Strategy

- Each new `run_reg_e_*` function gets tests following the DCTR pattern:
  1. `test_populates_results` -- verify `ctx["results"]["reg_e_key"]` exists
  2. `test_adds_slide` -- verify slide appended with correct ID and category
  3. `test_creates_chart` -- verify PNG file created in chart_dir
  4. `test_calls_excel_export` -- verify `_save_to_excel` mock was called
  5. Edge case tests (empty data, no eligible accounts, missing columns)
- Target: 60+ total tests (up from 9)
- All rates stored and compared as fractions (0-1)

---

## Notes

- Reg E has simpler data structure than DCTR (binary opt-in/opt-out vs debit yes/no)
- No equivalent to `Month to First Transaction` -- Reg E consent is a point-in-time flag
- CFPB Circular 2024-05 requires explicit opt-in consent -- compliance framing may be useful in executive summary
- Industry Reg E opt-in benchmarks: 15-60% (wide range depending on CU size and marketing)
