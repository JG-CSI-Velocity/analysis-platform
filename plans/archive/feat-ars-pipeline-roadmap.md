# ARS Pipeline Roadmap: Improvements, New Insights & Automation

## Current State Summary

**What's automated (47+ slides):**
- 16 DCTR analyses (A6+A7), consolidated into ~8 narrative + appendix
- 13 Reg E analyses (A8), consolidated into ~7 narrative + appendix
- 2 Value analyses (A11.1 debit card, A11.2 Reg E)
- 5 Core analyses (A1-A5: stat codes, debit, funnel, openings, branches)
- Per-month mailer summaries with donut + hbar + KPIs (A13)
- Per-month swipes + spend trend charts (A12)
- Responder count trend (A13.5)
- Responder account age distribution (A14.2)
- All-time aggregate mailer summary
- Market reach bubble + responder spend lift (A15.1, A15.2)
- Section dividers, consolidation, appendix ordering — all automatic

**What's still manual (10 preamble slides):**

| Slide | Title | Why Manual |
|---|---|---|
| P01 | Client intro title | Template — auto-generated already |
| P02 | Agenda | Static layout — could auto-populate |
| P03 | Program Performance divider | Template — auto-generated already |
| P04 | Financial Performance | **Manual table** — needs revenue data |
| P05 | Monthly Revenue (L12M) | **Manual chart** — needs revenue data |
| P06 | ARS Lift Matrix | **Manual table** — needs before/after data |
| P07 | Mailer Revisit divider | Template — auto-generated already |
| P10 | Data Check Overview | **Manual text** — summary commentary |
| P11 | Mailer Summaries divider | Template — auto-generated already |
| P12 | All Program Results | **Manual table** — needs aggregated results |

**Truly manual = 5 slides** (P04, P05, P06, P10, P12). The other 5 are section dividers already auto-generated.

---

## Priority Tiers

### Tier 1: Quick Wins — Better Success Story (1-2 sessions each)

These add high-impact insights using data that already exists in the pipeline.

#### 1A. Responder Revenue Attribution (new A15.3)
**File:** `mailer_impact.py`
**What:** Calculate actual interchange revenue from responders vs non-responders.
```
Responder IC Revenue = Responder Spend x IC Rate
Non-Responder IC Revenue = Non-Responder Spend x IC Rate
Incremental Revenue = (Resp Avg - NonResp Avg) x Responder Count x IC Rate
```
**Visual:** Side-by-side revenue bars with "incremental revenue" callout.
**Why:** Directly answers "is the program generating revenue?" in dollar terms.
**Data needed:** Already have spend columns + IC rate in config. Just math.

#### 1B. Branch-Level Mailer Performance (new A15.4)
**File:** `mailer_impact.py`
**What:** Response rate + spend lift by branch. Which branches respond best?
**Visual:** Horizontal bar chart ranked by response rate, with spend lift color-coded.
**Data needed:** `Branch` column + mailer response data. All available.
**Why:** Clients always ask "which branches are performing?" — gives them actionable data.

#### 1C. Pre/Post Mailer Spend Delta (new A16.1)
**File:** New `mailer_delta.py`
**What:** Compare avg spend in the 3 months BEFORE mailer vs 3 months AFTER.
**Visual:** Grouped bar or waterfall: "Before Mailer" → "After Mailer" for responders vs control (non-responders).
**Data needed:** Monthly spend columns already exist (`MmmYY Spend`). Just need to identify which months are pre vs post relative to mail date.
**Why:** This is THE "without us it would be worse" chart. If responder spend went up while non-responder stayed flat, the program is creating lift.

#### 1D. Responder Demographics Expansion (enhance A14)
**File:** `mailer_response.py`
**What:** Add holder age distribution, balance tier distribution, and business/personal split for responders.
**Data needed:** `Account Holder Age`, `Avg Bal`, `Business?` — all in the data.
**Why:** Helps answer "who is responding?" beyond just account age.

---

### Tier 2: Automate Manual Slides (2-3 sessions each)

#### 2A. P04 — Financial Performance Table
**What:** Auto-generate the revenue summary table from A11 results.
**Data:** `ctx['results']['value_1']` already has revenue with/without debit, NSF/OD split, IC split.
**Approach:** Build a `_build_financial_table_slide()` method in deck_builder.py that renders a formatted table from value analysis results.
**Slide type:** New `financial_table` builder.

#### 2B. P06 — ARS Lift Matrix
**What:** Auto-generate a before/after comparison matrix.
**Data:** Pre/post mailer spend deltas (from Tier 1C) + DCTR changes + Reg E changes.
**Approach:** Matrix showing: Metric | Before | After | Lift | for key metrics.
**Depends on:** Tier 1C (pre/post delta).

#### 2C. P10 — Data Check Overview (DCO)
**What:** Auto-generate summary text from data quality stats.
**Data:** Account counts, eligibility rates, debit penetration — all computed in subsets.
**Approach:** Template text with placeholders filled from `ctx` data:
```
Total Records: {n_total:,}
Open Accounts: {n_open:,} ({pct_open:.0f}%)
Eligible: {n_eligible:,} ({pct_eligible:.0f}%)
With Debit Card: {n_debit:,} (DCTR: {dctr:.1f}%)
Reg E Opted In: {n_reg_e:,} ({pct_reg_e:.1f}%)
```

#### 2D. P12 — All Program Results Table
**What:** Auto-generate aggregate results table across all mail months.
**Data:** `ctx['results']['monthly_summaries']` has per-month totals.
**Approach:** Summary table: Month | Mailed | Responded | Rate | Spend Lift.

---

### Tier 3: New Insight Modules (3-5 sessions each)

#### 3A. Sustained Lift Tracking (A16.2)
**What:** Track responder behavior 1, 3, 6, 12 months after responding. Does the lift sustain or decay?
**Visual:** Line chart showing avg spend over time for responders vs non-responders, starting from mail month.
**Why:** Proves long-term value, not just a one-time bump.

#### 3B. Cumulative Program Value (A16.3)
**What:** Total incremental revenue attributed to all mailers combined.
**Visual:** Running total bar chart by month: "Program has generated $X in incremental interchange."
**Why:** The ultimate ROI slide. Shows cumulative value over time.

#### 3C. Account Profitability Curves (A16.4)
**What:** Revenue per account by age cohort, balance tier, and product code.
**Why:** Identifies which accounts are most profitable and where to target.

#### 3D. NSF/OD Frequency Analysis (A16.5)
**What:** NSF/OD item frequency by segment (responders vs non-responders, by balance tier).
**Why:** Some clients care more about NSF fee revenue than interchange.

---

### Tier 4: Process & UX Improvements

#### 4A. Performance Optimization
- **kaleido pin** is already at 0.2.1 (good)
- Chart generation is sequential — could parallelize independent modules
- Large branch charts (28x14 figsize) could be optimized

#### 4B. Client-Specific Logic Cleanup
- Client 1200 has hardcoded date filters in 3 modules
- Move to config: `"date_cutoff": "Apr24"` in clients_config.json

#### 4C. Data Dictionary Generation
- Auto-discover all columns in the ODD file
- Generate a data dictionary slide or report
- Flag columns not used in any analysis

#### 4D. Batch Processing UX
- Current batch mode processes clients sequentially
- Could show per-client progress cards instead of sequential status

---

## Recommended Implementation Order

**Session 1-2: Tier 1A + 1C** (Revenue Attribution + Pre/Post Delta)
These are the highest-impact "success story" visuals. They directly answer:
- "How much revenue is the program generating?" (1A)
- "Are responders actually spending more, or were they already high spenders?" (1C)

**Session 3: Tier 1B + 1D** (Branch Performance + Demographics)
Fills out the story: "who is responding and where?"

**Session 4-5: Tier 2A + 2C + 2D** (Automate Financial, DCO, Results)
Eliminates 3 of 5 manual slides.

**Session 6: Tier 2B** (Lift Matrix — depends on pre/post data from Tier 1C)
Eliminates the last major manual slide.

**Later: Tier 3 + 4** as needed.

---

## Data Already Available but Not Used

| Column | Currently Used For | Untapped Potential |
|---|---|---|
| `Account Holder Age` | DCTR/Reg E breakdowns | Responder demographics, targeting |
| `Avg Bal` | Eligibility filter only | Balance tier revenue, NSF frequency |
| `Branch` | DCTR/Reg E breakdowns | Mailer response by branch, branch ROI |
| `Business?` | Subset filtering | Business vs personal response rates |
| `Prod Code` | Eligibility filter, Reg E A8.7 | Product profitability, product-level DCTR |
| `{MmmYY} Spend` (historical) | Current month trends | Pre/post comparison, sustained lift |
| `{MmmYY} Items` (if exists) | L12M total in A11 | NSF frequency by segment |
| `Has_Valid_ProdCode` | Created but never used | Data quality reporting |
| `Has_Valid_Branch` | Created but never used | Data quality reporting |

---

## What Would Make the Biggest Difference for Client Presentations

1. **Pre/Post Spend Delta** (Tier 1C) — "Here's the before and after"
2. **Revenue Attribution** (Tier 1A) — "Here's what that means in dollars"
3. **Automated Financial Table** (Tier 2A) — Eliminates most tedious manual work
4. **Branch Performance** (Tier 1B) — Clients love seeing their branches ranked
5. **Cumulative Program Value** (Tier 3B) — The ultimate "was it worth it?" answer
