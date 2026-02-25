# Strategic Analysis: ARS Pipeline Insights & Capabilities

## Overview

The ARS pipeline currently operates as a **comprehensive analysis engine** -- 18 registered modules across 6 sections producing 60+ individual slide-level analyses from ODD (Oracle Demand Deposit) data. This document catalogs what we can analyze today, identifies the highest-value strategic gaps, and recommends a transformation from "data presentation tool" to "strategic insights platform."

The three capabilities that would most transform the platform -- **synthesis, benchmarking, and prescription** -- require zero new data sources. Everything needed already exists in `ctx.results`.

---

## Current Analytical Capabilities

### Section 1: Portfolio Overview (3 modules, 3 slides)

| Slide | Module | What It Answers | Key Outputs |
|-------|--------|----------------|-------------|
| A1 | `overview.stat_codes` | What is the account status distribution? | Top 10 stat codes, personal/business split, % of total |
| A1b | `overview.product_codes` | What products do members hold? | Top 10 products, P/B breakdown, concentration analysis |
| A3 | `overview.eligibility` | How many accounts qualify for ARS programs? | Progressive funnel: Total -> Open -> Stat Eligible -> Product Eligible -> Mailable, drop-off rates |

**Strategic value**: Sets the stage. Tells the client "here is the universe we're working with." The eligibility funnel is the single most important context slide -- every downstream analysis operates on this subset.

---

### Section 2: Debit Card Take Rate (5 modules, ~20 slides)

| Slide Range | Module | What It Answers | Key Outputs |
|-------------|--------|----------------|-------------|
| DCTR-1 to DCTR-8 | `dctr.penetration` | What % of eligible accounts have debit cards? | Historical DCTR by year/decade, Open vs Eligible comparison, L12M monthly, P/B split, comprehensive summary |
| A7.4 to A7.15 | `dctr.trends` | Is DCTR improving or declining? | Segment trends, decade analysis, L12M trend, seasonality, vintage cohorts |
| DCTR-9, A7.10a-c, A7.13 | `dctr.branches` | Which branches activate debit cards best? | Per-branch DCTR (historical vs L12M), scatter (volume vs rate), heatmap, pivot table |
| A7.7 to A7.9 | `dctr.funnel` | Where do accounts drop out of the debit pipeline? | Historical + L12M funnels, eligible vs non-eligible comparison |
| DCTR-10 to 14, A7.11-12 | `dctr.overlays` | Which demographics have highest/lowest DCTR? | By account age, holder age, balance range, cross-tabs (age x balance) |

**Strategic value**: DCTR is the primary revenue driver for credit unions via interchange income. A 1pp increase in DCTR across 50,000 eligible accounts at $0.0050 IC rate with $500 avg monthly spend = ~$15K/year incremental revenue. The DCTR section answers "how big is the opportunity?" and "where should we focus activation efforts?"

**Cross-module data stored**: `ctx.results["dctr_1"]` through `["dctr_8"]` containing `overall_dctr`, `recent_dctr`, debit counts -- consumed by the Value module (A11.1).

---

### Section 3: Regulation E Opt-In (3 modules, ~11 slides)

| Slide Range | Module | What It Answers | Key Outputs |
|-------------|--------|----------------|-------------|
| A8.1 to A8.3, A8.12 | `rege.status` | What is the Reg E opt-in rate? | Overall status (donut), historical by year/decade, L12M monthly, 24-month trend with slope |
| A8.4a-c, A8.13 | `rege.branches` | Which branches have highest opt-in rates? | Branch horizontal bars, scatter (volume vs rate), vertical bars, monthly pivot |
| A8.5-7, A8.10-11 | `rege.dimensions` | Which demographics opt in most? | By account age, holder age, product code, all-time funnel, L12M funnel |

**Strategic value**: Reg E opt-in directly enables NSF/OD fee revenue. National average is ~20% opt-in (80% have NOT opted in per CFPB). This is often the second-largest revenue opportunity after DCTR.

**Cross-module data stored**: `ctx.results["reg_e_1"]` containing `opt_in_rate`, `l12m_rate` -- consumed by Value module (A11.2).

---

### Section 4: Account Attrition (3 modules, 13 slides)

| Slide Range | Module | What It Answers | Key Outputs |
|-------------|--------|----------------|-------------|
| A9.1-A9.3 | `attrition.rates` | How fast are we losing accounts? | Overall + L12M attrition rate, closure duration distribution, open vs closed balance comparison |
| A9.4-A9.8 | `attrition.dimensions` | Which segments attrite most? | By branch, product, personal/business, tenure, balance tier |
| A9.9-A9.13 | `attrition.impact` | What is the cost of attrition? | Debit card retention lift, mailer retention lift, est. annual revenue lost, L12M velocity + trend, ARS-eligible vs non-eligible comparison |

**Strategic value**: Attrition is the "leaky bucket" problem. Acquisition without retention is waste. The retention lift analyses (A9.9 debit, A9.10 mailer) directly support the business case for activation and engagement programs.

**Key insight already computed but underutilized**: `attrition_9["retention_lift"]` proves debit cards reduce attrition. Combined with `value_1["delta"]` (revenue per debit account), this creates a "double benefit" story: debit cards both increase revenue AND reduce losses.

---

### Section 5: Revenue Value Analysis (1 module, 2 slides)

| Slide | Module | What It Answers | Key Outputs |
|-------|--------|----------------|-------------|
| A11.1 | `value.analysis` | What is a debit card worth? | Revenue per account (with vs without debit), revenue at historical/TTM/100% DCTR |
| A11.2 | `value.analysis` | What is Reg E opt-in worth? | Revenue per account (opted in vs out), revenue at historical/TTM/100% opt-in |

**Strategic value**: This is the "headline number" of the entire review. It translates penetration rates into dollars. The three-scenario comparison (historical rate, TTM rate, 100% adoption) creates an aspirational target.

**Cross-module dependency**: Reads `ctx.results["dctr_1"]` and `ctx.results["reg_e_1"]` to get current penetration rates, then computes revenue opportunity at each scenario.

---

### Section 6: Mailer Campaign Analysis (3 modules, variable slides)

| Slide Range | Module | What It Answers | Key Outputs |
|-------------|--------|----------------|-------------|
| A12.{month}.Swipes/Spend | `mailer.insights` | Are responders spending more? | NU responder vs non-responder spend/swipes trends, TH segment averages (2 slides per mail month) |
| A13.{month}, A13.Agg, A13.5-6, A14.2 | `mailer.response` | Who responds to mailers? | Per-month summaries, aggregate, responder count trend, response rate trend, responder age distribution |
| A15.1-A15.4 | `mailer.impact` | What is the campaign ROI? | Market reach (penetration), spend share (responders vs others), IC revenue attribution, pre/post spend delta |

**Strategic value**: Direct mail response rates for house lists average 4.4-9% -- far exceeding digital channels at 0.12%. The mailer section proves (or disproves) that the mailing program generates incremental revenue.

**Dynamic behavior**: Slide count varies by client. A client with 3 mail months produces 6 A12 slides + 5 A13/A14 slides + 4 A15 slides = 15 slides. A client with no mailer data produces 0 slides (graceful degradation).

---

## Cross-Module Insights Already Possible but Not Yet Surfaced

These insights require **zero new code** -- all data points exist in `ctx.results`. They just need a synthesis layer.

### Insight 1: The Compound Effect

Data available:
- `ctx.results["dctr_1"]["insights"]["overall_dctr"]` = debit penetration
- `ctx.results["reg_e_1"]["opt_in_rate"]` = Reg E opt-in rate
- `ctx.results["attrition_9"]["retention_lift"]` = debit retention benefit
- `ctx.results["attrition_10"]["lift"]` = mailer retention benefit
- `ctx.results["value_1"]["delta"]` = revenue per debit account
- `ctx.results["value_2"]["delta"]` = revenue per opted-in account

**Unstated insight**: Accounts with debit cards AND Reg E opt-in AND who responded to mailers generate the most revenue AND have the lowest attrition. The multiplicative value of all three is greater than the sum of parts. No module currently synthesizes this.

### Insight 2: Net Revenue Opportunity

Data available:
- `ctx.results["value_1"]["pot_l12m"]` = gross revenue opportunity (debit)
- `ctx.results["attrition_11"]["total_lost"]` = annual revenue lost to closures
- `ctx.results["attrition_9"]["retention_lift"]` = debit reduces attrition by X%

**Unstated insight**: Net opportunity = gross opportunity MINUS expected attrition losses, ADJUSTED for the retention benefit of adoption. This is the most defensible ROI number possible from existing data, and no module computes it.

### Insight 3: New Account Quality Trajectory

Data available:
- `ctx.data["Date Opened"]` = can filter to L12M new accounts
- All DCTR, Reg E, balance metrics can be computed for the L12M cohort

**Unstated insight**: Are new accounts being opened with debit cards at a higher or lower rate than the historical base? Is the institution improving its onboarding, or is the eligible-but-unactivated pool growing?

### Insight 4: Branch Revenue Ranking

Data available:
- Per-branch DCTR (from `dctr.branches`)
- Per-branch Reg E rate (from `rege.branches`)
- Per-branch attrition rate (from `attrition.dimensions`)

**Unstated insight**: Combining these three into a "branch revenue effectiveness score" would create accountability and best-practice sharing. The best branch (high DCTR, high Reg E, low attrition) is the model; the worst needs targeted support.

---

## Strategic Gaps: What Should Be Built Next

### Tier 1: Immediate Impact (1-2 sessions each, existing data)

#### 1. Executive Scorecard Module
- **What**: Single slide with 6-8 KPIs, color-coded health indicators, trend arrows
- **Why**: Transforms client conversation from "here are 60 charts" to "here is your program health"
- **KPIs**: DCTR, Reg E rate, attrition rate, revenue delta (debit), revenue delta (Reg E), mailer penetration, L12M trend direction
- **Implementation**: New module `analytics/executive/scorecard.py` reading existing `ctx.results`
- **File**: `src/ars/analytics/executive/scorecard.py`

#### 2. Recommendations Engine
- **What**: Rules-based system generating 3-5 prioritized action items per client
- **Why**: Converts "here is your data" into "here is what to do about it"
- **Examples**:
  - DCTR < 70% -> "Target new account onboarding to include debit card activation within 30 days"
  - Attrition first-year > 50% -> "Consider retention-focused outreach within 90 days of opening"
  - Reg E < 25% -> "Multi-channel opt-in campaign with compliant CFPB scripting"
- **File**: `src/ars/analytics/executive/recommendations.py`

#### 3. Cross-Module Compound Effect Slide
- **What**: Single slide showing revenue + retention value of debit + Reg E + mailer engagement combined
- **Why**: The "so what" slide that connects every other section
- **File**: `src/ars/analytics/executive/compound_effect.py`

### Tier 2: Near-Term (2-4 sessions, high strategic value)

#### 4. Benchmarking Data Persistence
- **What**: After each run, append summary metrics to persistent store (JSON-lines or SQLite)
- **Why**: Unlocks peer benchmarking (300+ client dataset) and month-over-month client trending
- **File**: `src/ars/pipeline/steps/benchmark.py`

#### 5. Net Revenue Opportunity (Value Module Enhancement)
- **What**: Adjust gross revenue opportunity by attrition expectations and retention lift
- **Why**: Makes the headline ROI number defensible
- **File**: Enhance `src/ars/analytics/value/analysis.py`

#### 6. New Account Quality Module
- **What**: Compare L12M new accounts against historical averages for DCTR, Reg E, balance
- **Why**: Answers "is our program improving over time?"
- **File**: `src/ars/analytics/overview/new_account_quality.py`

#### 7. PPTX Deck Builder
- **What**: Complete the stub in `pipeline/steps/generate.py` using python-pptx
- **Why**: PowerPoint is the primary client deliverable. Currently a stub
- **File**: `src/ars/pipeline/steps/generate.py`

### Tier 3: Medium-Term (Requires accumulated data or new sources)

#### 8. Peer Benchmarking on Key Slides
- After 50+ clients run, add "vs. Peer Median" annotations to DCTR, Reg E, attrition, value slides
- Depends on: Benchmarking persistence (#4)

#### 9. Month-over-Month Client Trend
- Show "your DCTR was X% last month and Y% this month (+Xpp)"
- Depends on: Benchmarking persistence (#4)

#### 10. At-Risk Account Profiling
- Compare current open accounts to closed account profiles to flag at-risk segments
- Uses: tenure, balance, debit status, Reg E status patterns from attrition analysis

#### 11. Transaction Module Port
- Requires: Separate TXN CSV data files per client
- Provides: Merchant analysis, interchange revenue breakdown, spending category analysis

#### 12. ICS Module Port
- Requires: ICS append files + Revenue workbook
- Provides: ICS account identification, ICS source attribution (REF/DM/Both)

---

## Data Sources Inventory

### Currently Used: ODD (Oracle Demand Deposit)

| Category | Columns | Used By |
|----------|---------|---------|
| **Account Identity** | Date Opened, Stat Code, Product Code, Account Number | All modules |
| **Account Attributes** | Business?, Debit?, Branch, Mailable? | Overview, DCTR, Reg E, Attrition |
| **Demographics** | Account Holder Age, Date of Birth | DCTR overlays, Reg E dimensions |
| **Financial** | Avg Bal, Balance | Value, Attrition dimensions |
| **Reg E** | Reg E Code {YYYY.MM} (auto-detected) | Reg E modules, Value |
| **Attrition** | Date Closed | Attrition modules |
| **Mailer** | {MmmYY} Mail, {MmmYY} Resp (dynamic per month) | Mailer modules |
| **Activity** | {MmmYY} Spend, {MmmYY} Swipes (dynamic per month) | Mailer insights, Attrition revenue impact |

### Not Yet Used (Available in ODD, No Module Consumes)

| Column | Potential Use |
|--------|--------------|
| Relationship Balance | Wallet share analysis, total member value |
| Premier/VIP Status | Segment value tiers, retention priority |
| Fee Waiver flags | Revenue leakage analysis |
| Credit Score ranges | Risk-adjusted profitability |
| Online/Mobile enrollment | Digital engagement correlation with retention |
| Direct Deposit flag | PFI (Primary Financial Institution) indicator |
| Number of products | Cross-sell depth, relationship stickiness |

### Planned (Requires Separate Data Files)

| Source | Status | What It Enables |
|--------|--------|----------------|
| TXN CSV | Unported (28 analyses in txn-analysis repo) | Merchant analysis, interchange revenue, spending patterns |
| ICS Files + Revenue WB | Unported (33 analyses in ics_append repo) | ICS account identification, source attribution |

---

## Module Execution Flow with Data Dependencies

```
ODD File Load
    |
    v
[Subset Creation]
    |-- open_accounts (Stat Code = O)
    |-- eligible_data (open + eligible stat + prod codes)
    |-- eligible_personal (eligible + Business? = No)
    |-- eligible_business (eligible + Business? = Yes)
    |-- eligible_with_debit (eligible + Debit? = Yes)
    |
    v
[Overview] -- Uses: data, subsets
    |   Stores: a3 (funnel, insights)
    |
    v
[DCTR] -- Uses: data, subsets, start_date, end_date, branch_mapping
    |   Stores: dctr_1..dctr_14 (penetration metrics, branch data)
    |
    v
[Reg E] -- Uses: data, subsets, reg_e_column, reg_e_opt_in
    |   Stores: reg_e_1 (opt_in_rate, l12m_rate)
    |
    v
[Attrition] -- Uses: data (Date Closed for open/closed split)
    |   Stores: attrition_1..attrition_13 (rates, retention lift, revenue lost)
    |
    v
[Value] -- Uses: data, subsets, ic_rate, nsf_od_fee
    |   READS: dctr_1, reg_e_1 (cross-module!)
    |   Stores: value_1, value_2 (revenue deltas, opportunity scenarios)
    |
    v
[Mailer] -- Uses: data, subsets, dynamic column discovery
    |   Stores: a12_*, monthly_summaries, rate_trend, market_reach, revenue_attribution
    |
    v
[== PROPOSED NEW ==]
[Executive] -- Uses: ALL ctx.results
    |   Produces: Scorecard, Compound Effect, Recommendations
    |
    v
[Generate] -- Reads all AnalysisResult objects
    |-- Excel workbook (working)
    |-- PowerPoint deck (STUB -- needs implementation)
    |-- Chart PNGs (working)
```

---

## Questions the Pipeline Can Answer Today

### For the Executive / Board
1. "What is our debit card penetration rate?" -- DCTR-1
2. "How much revenue are we leaving on the table?" -- A11.1, A11.2
3. "Is our member retention improving or declining?" -- A9.1, A9.12
4. "Which branches are our best performers?" -- DCTR branches, Reg E branches
5. "Is our mailer program generating positive ROI?" -- A15.1-A15.4

### For the VP of Operations
6. "Which branches need activation support?" -- A7.10a/b/c (branch DCTR scatter)
7. "What is the Reg E opt-in rate by branch?" -- A8.4a-c
8. "Where are closures concentrated?" -- A9.4 (branch), A9.5 (product), A9.7 (tenure)
9. "Do debit cards actually reduce attrition?" -- A9.9 (yes, by `retention_lift`%)
10. "What is the revenue impact of closed accounts?" -- A9.11

### For the Marketing Team
11. "Which demographic segments respond best to mailers?" -- A12, A14.2
12. "What is the response rate trend over time?" -- A13.5, A13.6
13. "How much incremental spend do responders generate?" -- A15.4
14. "Should we target NU (New Users) or TH (Threshold) segments?" -- A12 per-segment analysis

### For the CSM (Consultant)
15. "Can I quickly scan which clients are ready for review?" -- `ars scan`
16. "Can I run a batch of clients in one go?" -- Batch mode in UI
17. "What modules should I run for this client?" -- Preset selection in wizard
18. "Is the data file valid before I start?" -- `ars validate`

---

## Questions the Pipeline CANNOT Answer Today (But Could)

### High-Value Gaps (Buildable from Existing Data)

19. "What is the overall health of this client's program in one number?" -- **Needs: Executive Scorecard**
20. "What should this client focus on first?" -- **Needs: Recommendations Engine**
21. "How does this client compare to peers?" -- **Needs: Benchmarking Persistence**
22. "Are new accounts being activated faster than before?" -- **Needs: New Account Quality Module**
23. "What is the NET revenue opportunity after accounting for attrition?" -- **Needs: Value Module Enhancement**
24. "What is the combined value of debit + Reg E + mailer engagement?" -- **Needs: Compound Effect Module**

### Medium-Value Gaps (Requires New Data or Accumulated History)

25. "How has this client's program improved since last review?" -- Needs: Month-over-Month Trending (requires persistence)
26. "What is the interchange revenue breakdown by merchant category?" -- Needs: Transaction Module Port
27. "Which accounts are at risk of closing?" -- Needs: At-Risk Profiling Module
28. "What seasonal patterns affect this client?" -- Needs: Seasonal Analysis Module

---

## Recommended Priority Sequence

```
Phase 1: Synthesis (make existing insights actionable)
    [x] All 18 analysis modules ported and tested (459 tests)
    [ ] Executive Scorecard (reads ctx.results, produces health summary)
    [ ] Recommendations Engine (rules-based, 15-20 rules)
    [ ] Compound Effect Slide (debit + Reg E + mailer combined value)

Phase 2: Delivery (get it into client hands)
    [ ] PPTX Deck Builder (complete the stub)
    [ ] Narrative Threading (transition slides connecting sections)
    [ ] Data Quality Report (pre-analysis validation summary)

Phase 3: Benchmarking (leverage the 300+ client dataset)
    [ ] Benchmarking Persistence (write metrics after each run)
    [ ] Peer Percentile Annotations (on key slides)
    [ ] Month-over-Month Client Trending (delta from last review)

Phase 4: Advanced Analytics (new modules from existing data)
    [ ] New Account Quality (L12M cohort vs historical)
    [ ] Net Revenue Opportunity (attrition-adjusted value)
    [ ] At-Risk Account Profiling (closed account pattern matching)
    [ ] Seasonal Pattern Analysis (monthly indexes)

Phase 5: New Data Sources (expand beyond ODD)
    [ ] Transaction Module Port (28 analyses from txn-analysis repo)
    [ ] ICS Module Port (33 analyses from ics_append repo)
```

---

## References

### Internal
- Module registry: `src/ars/analytics/registry.py:16-35`
- Pipeline context: `src/ars/pipeline/context.py:13-84`
- Value module (cross-module pattern): `src/ars/analytics/value/analysis.py`
- PPTX stub: `src/ars/pipeline/steps/generate.py:91-108`
- Client config schema: `configs/clients_config.json`

### External
- [10 KPIs Every Credit Union Should Measure](https://www.arkatechture.com/blog/10-important-kpis-for-credit-unions)
- [5 Best Practices for CU Portfolio Reviews - Equifax](https://www.equifax.com/business/blog/-/insight/article/5-best-practices-for-credit-union-portfolio-reviews/)
- [How Analytics Combats Attrition at CEFCU](https://creditunions.com/features/how-analytics-combats-attrition-at-cefcu/)
- [CFPB Circular 2024-05: Reg E Overdraft Opt-In Compliance](https://www.consumerfinance.gov/compliance/circulars/consumer-financial-protection-circular-2024-05/)
- [Four Strategies for Maximizing Debit Interchange Revenue](https://insights.co-opfs.org/blog/maximize-debit-interchange-revenue)
