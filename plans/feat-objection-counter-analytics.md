# Objection-Counter Analytics Suite

New analytics modules to counter the 4 most common client objections against the ARS program.
Each module is self-contained, follows the existing `@register` + `AnalysisModule` pattern, and degrades gracefully when config/data is missing.

---

## The 4 Objections

| # | Objection | Core Counter | Key Metric |
|---|-----------|-------------|------------|
| 1 | "ARS accounts are too expensive (ICS)" | Reactivation costs $25-50 vs $562.50 new member acquisition; each active card = $150-216/yr interchange | CPA vs LTV ratio, payback period |
| 2 | "ARS isn't impacting enough people" | 14pp gap between penetration (80.5%) and active rate (66.3%); cumulative unique members touched | Addressable universe %, program penetration |
| 3 | "ARS is ineffective" | Cohort trajectory reversal (A16), YoY DCTR improvement, peer benchmarks | Incremental lift %, DCTR trend |
| 4 | "What else could we do?" | Branch scorecard, dormant opportunity targeting, competitive leakage | Opportunity $ per branch, target list size |

---

## Phase A: Program ROI (S9-S10) -- fights "too expensive"

### New config fields

Add to `ClientInfo` in `pipeline/context.py`:
```python
program_annual_cost: float = 0.0       # Annual ARS program fee ($)
program_start_date: str = ""           # ISO date, e.g. "2023-06-01"
```

Add to `_build_client_info()` in `pipeline/batch.py` to read from `clients_config.json`.

Create `config/benchmarks.json`:
```json
{
  "member_acquisition_cost": 562.50,
  "avg_annual_interchange_per_card": 216.0,
  "debit_penetration_benchmark": 0.805,
  "active_card_rate_benchmark": 0.663,
  "source": "PULSE 2024 Debit Issuer Study",
  "last_updated": "2025-06-01"
}
```

### Module: `insights/roi.py`

| Slide | Title | Chart Type | What It Shows |
|-------|-------|-----------|---------------|
| S9 | Program ROI Summary | KPI panel + waterfall | Cost-per-activation vs lifetime IC value, net ROI ratio, payback period |
| S10 | Investment Payback Timeline | Line chart | Monthly cumulative IC revenue vs program cost, breakeven month highlighted |

**Key calculations:**
- `activation_count` = total NU 5+ + TH responses across all mail months (from `ctx.results`)
- `cost_per_activation` = `program_annual_cost / activation_count`
- `annual_ic_per_card` = `ctx.client.ic_rate * avg_annual_spend` (from value module results)
- `avg_account_life` = `1 / annual_attrition_rate` (from attrition results, capped at 10yr)
- `lifetime_ic_value` = `annual_ic_per_card * avg_account_life`
- `roi_ratio` = `lifetime_ic_value / cost_per_activation`
- `payback_months` = `cost_per_activation / (annual_ic_per_card / 12)`
- Compare CPA against benchmark `member_acquisition_cost` ($562.50)

**Graceful skip:** If `program_annual_cost == 0`, return `success=False, error="Program cost not configured"`.

**Section:** `"insights"` (extends existing S1-S8 synthesis)
**Execution order:** After `insights.conclusions` (needs value + attrition + mailer results)

---

## Phase B: Cumulative Reach (A17.1-A17.3) -- fights "not enough people"

### Module: `mailer/reach.py`

| Slide | Title | Chart Type | What It Shows |
|-------|-------|-----------|---------------|
| A17.1 | Cumulative Members Reached | Combo (bars + line) | Per-month new unique accounts mailed (bars) + running total line |
| A17.2 | Program Penetration Rate | Gauge / KPI panel | Unique accounts mailed / total eligible, with benchmark comparison |
| A17.3 | Organic Activation | Grouped bar | Accounts with Debit?=Yes that were NEVER mailed vs mailed responders |

**Key calculations:**
- Scan all `MmmYY Mail` columns; track unique Account Numbers ever mailed
- `penetration_rate` = unique mailed / total eligible (from `ctx.subsets.eligible_data`)
- Organic = accounts where ALL mail columns are None/NaN but `Debit?` = "Yes"
- Use Account Number as proxy for member (note in footnote)

**Section:** `"mailer"`
**Execution order:** After `mailer.cohort`

---

## Phase C: Effectiveness Proof (A18.1-A18.3) -- fights "ineffective"

### Module: `insights/effectiveness.py`

| Slide | Title | Chart Type | What It Shows |
|-------|-------|-----------|---------------|
| A18.1 | DCTR Progression | Line chart | Historical DCTR trend with program start date marked, YoY pp change |
| A18.2 | Cumulative Value Delivered | Area chart | Running total of incremental IC revenue from activations over time |
| A18.3 | Industry Benchmarks | Horizontal bar comparison | CU's DCTR, Reg E rate, active card rate vs PULSE benchmarks |

**Key calculations:**
- A18.1: Reuse DCTR historical data from `ctx.results["dctr_1"]` through `["dctr_8"]`; add vertical line at `program_start_date`
- A18.2: For each mail month, count new activations * monthly IC per card, accumulate
- A18.3: Load `benchmarks.json`, compare CU metrics vs benchmarks with delta annotations

**Graceful skip:** A18.1 works without `program_start_date` (just shows DCTR trend without marker). A18.2 needs activation counts (skips if no mail data). A18.3 needs `benchmarks.json` (skips if missing).

**Section:** `"insights"`
**Execution order:** After `insights.roi` (needs DCTR + value results)

---

## Phase D: Consulting Value (A19-A20)

### Module: `insights/branch_scorecard.py`

| Slide | Title | Chart Type | What It Shows |
|-------|-------|-----------|---------------|
| A19.1 | Branch Performance Scorecard | Heatmap table | DCTR rank + Reg E rank + Attrition rank + $ opportunity per branch |
| A19.2 | Branch Opportunity Map | Horizontal stacked bar | Dollar opportunity breakdown per branch (IC gap + Reg E gap + retention gap) |

**Key calculations:**
- Pull branch-level DCTR from `ctx.results` (dctr.branches stores per-branch rates)
- Pull branch-level Reg E from rege.branches results
- Pull branch-level attrition from attrition.dimensions results
- Compute composite rank and dollar opportunity per branch
- Minimum 3 branches required; skip if fewer

**Section:** `"insights"`
**Execution order:** After `insights.effectiveness`

### Module: `insights/dormant.py`

| Slide | Title | Chart Type | What It Shows |
|-------|-------|-----------|---------------|
| A20.1 | Dormant Opportunity Summary | KPI panel + bar | Count and $ value of high-balance accounts without debit cards |
| A20.2 | At-Risk Member Identification | Bar + scatter | Accounts with declining spend trajectory (L12M spend trend) |
| A20.3 | Targeting Priority Matrix | Scatter plot | Balance vs spend decline, sized by account age, colored by branch |

**Key calculations:**
- High-balance no-debit: `Debit? != "Yes"` AND `Avg Bal` in top quartile
- Declining spend: Compare first-half vs second-half of spend columns; flag if decline > 20%
- Priority = balance rank * spend-decline severity
- Dollar opportunity = count * benchmark IC per card ($216/yr)

**Section:** `"insights"`
**Execution order:** After `insights.branch_scorecard`

---

## Phase E: Competitive Leakage (A21) -- deferred

### Module: `insights/leakage.py` (future)

| Slide | Title | Chart Type | What It Shows |
|-------|-------|-----------|---------------|
| A21.1 | Competitive Leakage | Grouped bar | Members WITHOUT debit cards are X% more likely to transact at competitors |

**Deferred because:** Requires TXN data loaded within ARS pipeline. Current `PipelineContext.txn_file_path` exists but no loading mechanism. Build this after the cross-pipeline data access pattern is established.

---

## Files to Create/Modify

| # | File | Action | Phase |
|---|------|--------|-------|
| 1 | `pipeline/context.py` | Add `program_annual_cost`, `program_start_date` to `ClientInfo` | A |
| 2 | `pipeline/batch.py` | Read new fields in `_build_client_info()` | A |
| 3 | `config/benchmarks.json` | CREATE -- industry benchmark values | A |
| 4 | `config.py` or `pipeline/benchmarks.py` | CREATE -- loader for benchmarks.json | A |
| 5 | `analytics/insights/roi.py` | CREATE -- S9, S10 | A |
| 6 | `analytics/mailer/reach.py` | CREATE -- A17.1, A17.2, A17.3 | B |
| 7 | `analytics/insights/effectiveness.py` | CREATE -- A18.1, A18.2, A18.3 | C |
| 8 | `analytics/insights/branch_scorecard.py` | CREATE -- A19.1, A19.2 | D |
| 9 | `analytics/insights/dormant.py` | CREATE -- A20.1, A20.2, A20.3 | D |
| 10 | `analytics/base.py` | Extend `SectionName` if needed | A |
| 11 | `analytics/registry.py` | Add 5 modules to `MODULE_ORDER` | A-D |
| 12 | `output/deck_builder.py` | Add slide IDs, section map, consolidation | A-D |
| 13 | `platform_app/core/module_registry.py` | Add 5 `ModuleInfo` entries | A-D |
| 14 | `tests/ars/conftest.py` | New fixtures with program cost + benchmarks | A |
| 15 | `tests/ars/test_analytics/test_roi.py` | CREATE | A |
| 16 | `tests/ars/test_analytics/test_reach.py` | CREATE | B |
| 17 | `tests/ars/test_analytics/test_effectiveness.py` | CREATE | C |
| 18 | `tests/ars/test_analytics/test_branch_scorecard.py` | CREATE | D |
| 19 | `tests/ars/test_analytics/test_dormant.py` | CREATE | D |

---

## Main Deck vs Appendix

| Slide | Placement | Rationale |
|-------|-----------|-----------|
| S9 (ROI Summary) | **Main** | Headline counter to "too expensive" |
| S10 (Payback Timeline) | Appendix | Supporting detail |
| A17.1 (Cumulative Reach) | Appendix | Detail chart |
| A17.2 (Penetration Rate) | **Main** | Headline counter to "not enough people" |
| A17.3 (Organic Activation) | Appendix | Supporting evidence |
| A18.1 (DCTR Progression) | **Main** | Headline counter to "ineffective" |
| A18.2 (Cumulative Value) | Appendix | Supporting detail |
| A18.3 (Benchmarks) | **Main** | Strong credibility builder |
| A19.1 (Branch Scorecard) | **Main** | High consulting value |
| A19.2 (Branch Opportunity) | Appendix | Detail breakdown |
| A20.1 (Dormant Summary) | **Main** | Actionable opportunity |
| A20.2 (At-Risk) | Appendix | Detail |
| A20.3 (Priority Matrix) | Appendix | Detail |

**Net impact:** +5 main deck slides, +8 appendix slides

---

## Execution Order

1. ~~**Phase A** (S9-S10): DEFERRED -- client pricing is per-eligible-account/month, not per-activation. Needs its own design later.~~
2. **Phase B** (A17): Cumulative reach module (~1 session) -- NO config changes needed
3. **Phase C** (A18): Effectiveness proof module (~1 session) -- needs benchmarks.json
4. **Phase D** (A19-A20): Branch scorecard + dormant opportunity (~2 sessions)
5. **Phase E** (A21): Competitive leakage (deferred)

---

## Verification

```bash
uv run pytest tests/ars/ -q
uv run pytest tests/platform/ -q
uv run ruff check packages/
```

## Checklist

### Phase A
- [ ] `program_annual_cost` + `program_start_date` added to ClientInfo
- [ ] `benchmarks.json` created with PULSE data + sources
- [ ] Benchmark loader created
- [ ] S9: ROI summary KPI panel + waterfall
- [ ] S10: Payback timeline line chart
- [ ] Graceful skip when program_annual_cost = 0
- [ ] Tests pass, ruff clean

### Phase B
- [x] A17.1: Cumulative unique accounts mailed (combo chart)
- [x] A17.2: Program penetration rate (gauge/KPI)
- [x] A17.3: Organic activation (grouped bar)
- [x] Tests pass, ruff clean

### Phase C
- [x] A18.1: DCTR progression with program start marker
- [x] A18.2: Cumulative value delivered (area chart)
- [x] A18.3: Industry benchmarks comparison (hbar)
- [x] Tests pass, ruff clean

### Phase D
- [x] A19.1: Branch performance scorecard (heatmap table)
- [x] A19.2: Branch opportunity map (stacked bar)
- [x] A20.1: Dormant opportunity summary (KPI + bar)
- [x] A20.2: At-risk member identification (bar + scatter)
- [x] A20.3: Targeting priority matrix (scatter)
- [x] Min 3 branches guard on A19
- [x] Tests pass, ruff clean
