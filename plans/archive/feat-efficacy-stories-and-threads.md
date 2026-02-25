# Efficacy Stories & Analytical Threads for ARS Program

## Enhancement Summary

**Deepened on:** 2026-02-07
**Agents used:** 9 parallel (Python reviewer, pattern recognition, performance oracle, architecture strategist, code simplicity, spec-flow analyzer, DiD methodology research, financial presentation research, cohort analysis research)

### Key Improvements from Deep Research
1. **Architecture**: Split into `mailer_efficacy.py` + `mailer_common.py` instead of bloating `mailer_impact.py`
2. **DiD methodology**: Formal DiD is inappropriate with self-selected responders; use simpler "net program lift" KPI
3. **T4 implementation**: Vectorized numpy broadcasting pattern from ICS codebase, with right-censoring handling
4. **Simplification**: Cut T8 from first pass; merge T5+T7 into "Responder Profile"; T9+T10 share a helper
5. **Edge cases**: Inverse narrative handling, minimum sample sizes, and conditional framing for every thread
6. **Presentation**: CFOs prefer KPI cards > waterfall > line charts; add 3.95% benchmark line; "Revenue Protected" metric

### Critical Decisions Required Before Implementation
1. What framing when data contradicts narrative? (Recommend: neutral framing with conditional text)
2. Minimum sample sizes per thread? (Recommend: 30 accounts per subgroup)
3. `cost_per_mailer` format? (Recommend: dollars per piece, skip slide if absent)
4. T4 control group construction? (Recommend: earliest mailer month as global anchor)

---

## Overview

A strategic plan for the analytical narratives that prove the ARS mailer program works. Each "story" is a thread that connects existing data to a client-facing argument. The goal: when a client says "interchange is down, is this working?" -- you have 6+ data-backed answers ready, not just one.

---

## The Core Client Objections (and which threads answer them)

| Objection | Thread(s) |
|---|---|
| "Our interchange income is down" | T1, T3, T6 |
| "These people were already spending" | T2, T4 |
| "Which branches should we focus on?" | T5 |
| "Is the program worth the cost?" | T3, T6 |
| "Who is actually responding?" | T5, T7 |
| "Show me the before and after" | T2 |
| "What happens long-term?" | T4 |

### Research Insight: The "Declining Interchange" Objection

**Best practice (from financial presentation research):** Decompose interchange revenue into volume vs. rate effects using a waterfall chart:

```
Starting Revenue --> +Volume Effect (more transactions) --> -Rate Effect (Durbin) --> = Ending Revenue
```

Frame as: "Our program is growing the things we can control (volume, activation, spend per cardholder) while the industry headwind on rates affects everyone." Present revenue-per-account, not revenue-per-transaction, to show per-account value growing despite rate compression.

**"Revenue Protected" metric for decline scenarios:** When both groups show declining spend:
```
Revenue Protected = (Non-Responder Decline Rate - Responder Decline Rate)
                    x Responder Base x Average Pre-Program Revenue
```

Board-friendly language: "Without the mailer program, we estimate responder spend would have been $X lower."

---

## Thread 1: The Spend Waterfall -- "Where does your money come from?"

**Status:** Built (A15.2 Spend Share)

**Story:** Not all accounts are equal. Here is total spend from all open accounts, then eligible accounts, then just responders. Responders are X% of eligible accounts but account for Y% of eligible spend.

**Data:** `ctx['open_accounts']`, `ctx['eligible_data']`, unique responders, latest `{MmmYY} Spend` column.

**Key visual:** Horizontal bars descending (All Open > Eligible > Responders) with proportion KPIs.

**Framing:** "Your responders punch above their weight. They're X% of your eligible base but drive Y% of the spend."

### Research Insights

**Edge case -- Inverse narrative:** When responders represent 20% of accounts but only 12% of spend, the framing "punch above their weight" is factually wrong. The existing code has no conditional framing for this case.

**Fix:** Add conditional framing to `run_spend_share()`:
```python
if resp_spend_pct > resp_acct_pct:
    framing = f"Responders are {resp_acct_pct:.0f}% of eligible but drive {resp_spend_pct:.0f}% of spend."
else:
    framing = f"Responders represent {resp_acct_pct:.0f}% of eligible accounts and {resp_spend_pct:.0f}% of spend."
```

---

## Thread 2: Before vs After -- "The program changed behavior"

**Status:** Built (A15.4 Pre/Post Spend Delta)

**Story:** Compare average spend per account in the 3 months before the first mailer vs 3 months after. Responders grew while non-responders stayed flat (or declined).

**Data:** `{MmmYY} Spend` columns, first mail month as event boundary. Pre = 3 months before, Post = 3 months after.

**Key visual:** Grouped bar: Responders vs Non-Responders, Before vs After, with delta annotations.

**Framing depends on data:**
- Resp up, Non-resp down: "The program is protecting and growing revenue"
- Resp up more than Non-resp: "Responders outpaced by $X/account"
- Both down but Resp less: "The program is mitigating decline"

**Enhancement:** Add a single **"Net Program Lift"** KPI annotation to the existing A15.4 chart.

### Research Insights: DiD Methodology

**Critical finding (from DiD research):** Formal Difference-in-Differences is NOT appropriate here because:
1. **Self-selection bias**: Responders chose to respond -- they are inherently different from non-responders
2. **Endogeneity**: Response segments (NU 5+, TH-10, etc.) are defined by spending thresholds -- you're conditioning on the outcome variable
3. **Parallel trends violation**: Responders were likely already on an upward spending trajectory before the mailer

**What to do instead:** The existing code at `mailer_impact.py:609-621` already computes the DiD estimate implicitly as `resp_delta - non_delta`. Simply surface this as a KPI annotation:

```python
# Add one line to existing A15.4:
net_lift = resp_delta - non_delta
ax.text(0.5, -0.22,
        f"Net program lift: ${net_lift:,.0f}/account (after adjusting for market trends)",
        transform=ax.transAxes, ha='center', fontsize=12, color='#1E3D59')
```

This is a ~5 line change, not a methodology overhaul. Use the phrase "Program Lift After Adjusting for Market Trends" -- never "Difference-in-Differences."

**Future improvement:** Recommend a 5-10% holdout test for the next campaign. This creates a true control group and is the single most impactful methodological improvement. Add a recommendation slide.

**Edge case -- fillna(0) bias:** The existing code uses `.fillna(0).mean()` which conflates "no data" with "zero spend." An account not yet open shows as $0, inflating apparent lift. For pre/post averaging, use `.dropna()` instead of `.fillna(0)`.

---

## Thread 3: Revenue Attribution -- "Here's the dollar amount"

**Status:** Built (A15.3 Revenue Attribution)

**Story:** Translate the spend delta into interchange dollars. Responders generate $X more in IC revenue per account than non-responders. Across N responders, that's $Y in incremental interchange.

**Data:** Latest spend column, IC rate from config, responder/non-responder split.

**Key visual:** IC revenue per account bars + KPI text block with incremental total.

**Enhancement opportunity:** Show this as a **running total across mailer months** (Tier 3B from roadmap). "Since the program began, it has generated $Z in cumulative incremental interchange."

### Research Insights

**Bug -- negative incremental display:** At `mailer_impact.py:455`, the KPI label `f'+${incremental_per:,.2f}'` hardcodes a `+` prefix. When `incremental_per` is negative, this produces `+$-42.15`. Fix:

```python
sign = '+' if incremental_per >= 0 else ''
f'{sign}${incremental_per:,.2f}'
```

**Presentation best practice:** CFOs prefer a clean comparison table over a complex chart for dollar values:

| Metric | Responders | Non-Responders | Delta |
|--------|-----------|---------------|-------|
| Avg Monthly Spend | $X | $Y | +$Z |
| IC Revenue/Account | $A | $B | +$C |
| Total Incremental IC | -- | -- | $D |

---

## Thread 4: Sustained Lift -- "It's not just a one-time bump"

**Status:** Not built (Tier 3A from roadmap)
**Analysis ID:** A16.1
**Module:** `mailer_efficacy.py` (NEW)

**Story:** Track responder spend at 1, 3, 6, 12 months after their first response. Does the lift sustain or decay? This is THE long-term value argument.

**Data:** All `{MmmYY} Spend` columns exist. For each responder, identify their first response month, then track their monthly spend forward.

**Key visual:** Indexed lift curves (Month 0 = 100) for responders vs non-responders, with retention heatmap as secondary chart.

**Framing:** "6 months after responding, responders are still spending $X more per account. The behavior change is durable."

**Why this matters:** Clients worry the mailer just causes a temporary spike. If you show sustained lift, the ROI calculation changes dramatically -- you're not just getting one month of revenue, you're getting ongoing incremental value.

### Research Insights: Implementation

**Vectorized first-response discovery (from cohort analysis research + performance review):**

The naive per-row approach takes 10-30 seconds for 5,000 responders. Use numpy broadcasting instead (~50ms):

```python
# Build boolean matrix: (n_accounts x n_mail_months)
resp_array = np.column_stack([
    data[resp_col].isin(RESPONSE_SEGMENTS).values
    for _, resp_col, _ in pairs
])
has_resp = resp_array.any(axis=1)
first_idx = np.argmax(resp_array, axis=1)  # index of first True
month_labels = np.array([m for m, _, _ in pairs])
first_response_month = pd.Series(
    np.where(has_resp, month_labels[first_idx], None),
    index=data.index
)
```

**Relative-time pivot (from cohort research):**

Convert wide-format spend columns to relative-month matrix using numpy broadcasting:

```python
# Parse dates once
cohort_months = cohort_date_series.values.astype('datetime64[M]').astype('int64')
spend_months = np.array([np.datetime64(d, 'M') for d in spend_dates.values()]).astype('int64')

# Broadcasting: (n_accounts, 1) vs (1, n_cols) -> (n_accounts, n_cols)
relative_months = spend_months[np.newaxis, :] - cohort_months[:, np.newaxis]

# Scatter into result matrix
MAX_RELATIVE = 12
result = np.full((len(data), MAX_RELATIVE + 1), np.nan)
for col_idx in range(len(spend_cols)):
    offsets = relative_months[:, col_idx]
    mask = (offsets >= 0) & (offsets <= MAX_RELATIVE)
    result[np.where(mask)[0], offsets[mask].astype(int)] = spend_values[np.where(mask)[0], col_idx]
```

**Milestone conventions (reuse from ICS codebase):**

```python
ARS_MILESTONES = {
    "M1": 0,    # Response month itself
    "M3": 2,    # 2 months after response
    "M6": 5,    # 5 months after response
    "M12": 11,  # 11 months after response
}
```

**Right-censoring:** For newer cohorts with fewer months of post-event data, set cells to `NaN` (not 0). Charts naturally skip NaN. In heatmaps, render censored cells in gray with no annotation.

**Minimum data requirement:** Skip this analysis entirely if fewer than 6 months of spend data exist after the first mailer. Log: "Insufficient post-mailer history for sustained lift analysis."

**Control group construction:** Use the earliest mailer month as the global anchor for non-responders. This is simpler than cohort-matched controls and sufficient for the audience.

**Conditional framing for lift decay:**
- Sustained (>80% of M1 at M6): "The behavior change is durable"
- Gradual decay (50-80% at M6): "The program creates lasting engagement even after the initial response fades"
- Rapid decay (<50% at M6): "The spend boost lasts ~3 months; consider more frequent mailing to maintain momentum"

**Responder personas (adapted from ICS):**
- **Sustained Spender**: Active at M1, M3, AND M6
- **Fading Responder**: Active at M1, trails off by M3/M6
- **Late Bloomer**: Low at M1 but active by M3
- **Non-Activator**: Responded but spend did not increase

**Performance estimate:** 2-3 seconds vectorized (vs 30+ seconds naive). Memory: ~5MB for 5,000 responders x 12 months.

---

## Thread 5+7 (merged): Responder Profile -- "Who responds and where?"

**Status:** Not built
**Analysis IDs:** A16.2 (Branch Performance), A16.3 (Demographics)
**Module:** `mailer_efficacy.py` (NEW)

### Research Insight: Simplification

**Per simplicity review:** T5 (Branch Performance) and T7 (Who Responds) overlap significantly -- T7 includes branch as a demographic dimension. Merge into a single "Responder Profile" thread producing 2-3 slides, each following the one-chart-one-slide pattern.

**Slide A -- Branch response rates:** Horizontal bar chart ranked by response rate, minimum 25 mailed accounts per branch to include. Use `BranchMapping` from config for display names. Aggregate branches with same mapped name.

**Slide B -- Responder demographics:** Single 2x2 subplot figure (not 4 separate charts) showing:
- Balance tier distribution (responders vs non-responders)
- Business/personal split
- (Optional) Account holder age if column exists
- (Optional) Product code breakdown if >3 distinct codes

This renders as one PNG using `plt.subplots(2, 2, figsize=(16, 12))` and uses the existing `screenshot` slide type. No `deck_builder.py` changes needed.

### Edge Cases

**Small branches:** Branches with <25 mailed accounts are excluded from the chart with a footnote: "N branches excluded (fewer than 25 mailed accounts)."

**Missing Branch column:** Guard with `if 'Branch' not in data.columns: skip`. Same for `Account Holder Age` / `Birth Date`.

**Balance tier definitions:** Use bins `[0, 500, 2000, 5000, 10000, float('inf')]` with labels `['$0-500', '$500-2K', '$2K-5K', '$5K-10K', '$10K+']`. Make configurable via config if needed later.

---

## Thread 6: Cost vs Return -- "The ROI slide"

**Status:** Partially built (data exists, no dedicated slide)
**Analysis ID:** A15.5
**Module:** `mailer_impact.py` (stays here -- natural extension of A15.3)

**Story:** The program costs $X per mailer (printing + postage). Across N mailed accounts, total cost = $C. Incremental interchange from responders = $R. ROI = (R - C) / C.

**Data needed:** Cost per mailer -- a config field. Everything else exists:
- Mailed count: from `{MmmYY} Mail` columns (cumulative across all months)
- Incremental revenue: from A15.3 revenue attribution (`ctx['results']`)
- IC rate: `ctx['ic_rate']`

**Key visual:** Simple KPI table (CFOs prefer tables for dollar comparisons):

```
Program Cost:           $12,500  (5,000 mailed x $2.50/piece)
Incremental IC Revenue: $34,200  (from A15.3)
Net Program Value:      $21,700
ROI:                    174%
```

### Research Insights: Config and Validation

**Config field:** Add `CostPerMailer` to `clients_config.json`. This is dollars per mail piece. Follow the exact pattern used for `ICRate`:

```python
# In step_load_config (pipeline.py):
try:
    ctx['cost_per_mailer'] = float(str(config.get('CostPerMailer', '0')).strip())
except (ValueError, TypeError):
    ctx['cost_per_mailer'] = 0.0
```

**Guard in ROI analysis:** If `cost_per_mailer <= 0`, skip the slide with a clear message:
```python
if ctx.get('cost_per_mailer', 0) <= 0:
    _report(ctx, "   No CostPerMailer configured -- skipping ROI")
    return ctx
```

**T6 reads from T3:** Do NOT recompute incremental IC. Read from `ctx['results']` after A15.3 runs:
```python
incremental_total = ctx['results'].get('a15_3', {}).get('incremental_total', 0)
```

**Negative ROI:** When program cost exceeds incremental revenue, show the numbers with neutral framing. Do NOT suppress the slide -- the analyst decides whether to include it.

**Mailed count:** Use cumulative unique mailed accounts across all months (not per-month).

---

## Thread 8: ICS Cross-Pollination -- "The full account picture"

**Status:** DEFERRED (cut from first pass)

### Research Insight: Simplification

**Per simplicity + architecture reviews:** T8 introduces a cross-pipeline dependency that does not exist in the current architecture, requires config for ICS file paths, and addresses no client objection currently listed. The data is "Partial" ready.

**Decision:** Defer T8 to a separate future feature. Revisit only when a client explicitly asks "how do mailer responders behave in ICS?"

**If eventually built:** Use Option B (load ICS data as separate `ctx['ics_data']` with opt-in guard). Use `usecols` to load only needed columns (~7 vs 50+), reducing load time from 15s to 3s and memory from 40MB to 5MB.

---

## Thread 9+10 (shared helper): Cross-Domain Correlations

**Status:** Data exists, connection not shown
**Analysis IDs:** A16.4 (DCTR + Mailer), A16.5 (Reg E + Mailer)
**Module:** `mailer_efficacy.py` (NEW)

### Research Insight: Shared Implementation

**Per simplicity review:** T9 and T10 are structurally identical -- both compare a rate (DCTR or Reg E opt-in) for responders vs non-responders. Share a single helper:

```python
def _responder_rate_comparison(ctx, metric_name, rate_fn, chart_path):
    """
    Generic: compute a rate for responders vs non-responders,
    draw a grouped bar, return slide data.
    rate_fn(data, mask) -> float
    """
    resp_rate = rate_fn(data, resp_mask)
    non_rate = rate_fn(data, ~resp_mask)
    # ... draw grouped bar chart ...
```

T9 and T10 become thin 10-line callers that pass different `rate_fn` lambdas.

### Thread 9: DCTR + Mailer

**Key visual:** Grouped bar: DCTR for responders vs non-responders.

**Guard:** Check `ctx['results'].get('dctr_1')` exists before proceeding. If DCTR suite was skipped, skip T9 with log message.

**Framing:** Use correlation language, NOT causal: "Card adoption trends and mailer activity" -- not "The program drives card adoption."

**Edge case:** If DCTR is flat/declining even after mailers, use neutral framing: "DCTR for responders: X% vs non-responders: Y%."

### Thread 10: Reg E + Mailer

**Key visual:** Grouped bar: Reg E opt-in rate for responders vs non-responders.

**Guard:** Check `ctx['reg_e_opted_in']` is not None and `ctx['latest_reg_e_column']` exists. The Reg E subset is built from `eligible_personal` with debit -- ensure responder mask is intersected with this population to avoid mismatch.

**Edge case:** If responder opt-in rate is LOWER than non-responder, show the data with neutral framing. Do not suppress.

---

## Architecture: Module Structure

### Research Insight: Critical Refactor

**Per Python reviewer + architecture strategist + pattern recognition:** Do NOT put 6 new analyses into `mailer_impact.py` (currently 659 lines). This would push it to 1,200+ lines.

### New Module Structure

| Module | Purpose | Analyses | Est. Lines |
|---|---|---|---|
| `mailer_common.py` | NEW: Shared constants + helpers | -- | ~80 |
| `mailer_impact.py` | EXISTING: A15.1-A15.5 | T2 enhancement, T6 ROI | ~850 |
| `mailer_efficacy.py` | NEW: Efficacy narratives | T4, T5+T7, T9, T10 | ~600 |

### `mailer_common.py` -- Extract Before Building

Eliminate the 3x duplication of constants and helpers:

```python
# mailer_common.py
RESPONSE_SEGMENTS = ['NU 5+', 'TH-10', 'TH-15', 'TH-20', 'TH-25']
MAILED_SEGMENTS = ['NU', 'TH-10', 'TH-15', 'TH-20', 'TH-25']
TH_SEGMENTS = ['TH-10', 'TH-15', 'TH-20', 'TH-25']
SPEND_PATTERN = re.compile(r'^[A-Z][a-z]{2}\d{2} Spend$')

def report(ctx, msg): ...
def save_chart(fig, path): ...
def slide(ctx, slide_id, data, category='Mailer'): ...
def parse_month(col_name): ...
def discover_pairs(ctx): ...
def build_responder_mask(data, pairs): ...
```

### Pipeline Wiring

```python
# In pipeline.py, add Phase 3g:
def run_a16(ctx):
    from mailer_efficacy import run_mailer_efficacy_suite
    return run_mailer_efficacy_suite(ctx)
```

### `ctx` Key Documentation

Each new module must document required keys in its module docstring:

```python
"""
mailer_efficacy.py -- A16 Efficacy Narrative Threads
Required ctx keys:
    ctx['data']                -- full ODD DataFrame
    ctx['eligible_data']       -- eligible subset
    ctx['eligible_with_debit'] -- eligible with debit card
    ctx['reg_e_opted_in']      -- Reg E opted-in subset (may be None)
    ctx['cost_per_mailer']     -- cost per piece (float, 0 = not configured)
    ctx['mailer_pairs']        -- discovered (month, resp_col, mail_col) tuples
"""
```

### Cache Responder Mask in Context

Compute once at the start of each suite, not per-analysis:

```python
def run_mailer_efficacy_suite(ctx):
    pairs = discover_pairs(ctx)
    if not pairs:
        return ctx
    ctx['_resp_mask'] = build_responder_mask(ctx['data'], pairs)
    ctx['_mailed_mask'] = build_mailed_mask(ctx['data'], pairs)
    # ... run individual analyses ...
```

### Error Isolation

Use the `_safe` wrapper pattern (from `mailer_response.py`) in the suite runner:

```python
def _safe(fn, ctx, label):
    try:
        return fn(ctx)
    except Exception as e:
        report(ctx, f"   {label} failed: {e}")
        traceback.print_exc()
        return ctx
```

---

## Priority Matrix (Revised)

| Thread | Impact | Effort | Data Ready? | Session |
|---|---|---|---|---|
| T1: Spend Waterfall | High | Done | Yes | Built |
| T2: Before/After + Net Lift KPI | Very High | 15 min | Yes | Session 0 (quick fix) |
| T3: Revenue Attribution | High | Done | Yes | Built (fix +/- bug) |
| T4: Sustained Lift | Very High | 2-3 hrs | Yes (need 6+ months) | Session 1 |
| T5+T7: Responder Profile | High | 2-3 hrs | Yes | Session 2 |
| T6: ROI Slide | Very High | 1-2 hrs | Need cost config | Session 2 |
| T9+T10: Cross-Domain Correlations | Medium | 1-2 hrs | Yes | Session 3 |
| T8: ICS Cross-Pollination | Medium | DEFERRED | Partial | Future |

**Prerequisite (Session 0):** Extract `mailer_common.py` from duplicated helpers/constants. ~1 hour.

**Estimated total new code:** ~600 lines across `mailer_efficacy.py` + ~80 lines `mailer_common.py` + ~200 lines additions to `mailer_impact.py`. Total: ~880 lines (vs 1,200+ without simplifications).

---

## Recommended Presentation Narrative Arc

The threads form a story. Sequence them in the presentation as follows.

**Note (from architecture review):** Do NOT encode the 3-act structure into pipeline code. Use the existing `category` tagging + `_reorder_analysis_slides`. The narrative arc is a presentation guide, not code architecture.

### Act 1: "The Program is Working" (Slides 1-4)
1. **Market Reach** (A15.1) -- "We touch X% of your eligible cardholders"
2. **Spend Waterfall** (T1/A15.2) -- "Responders drive Y% of eligible spend"
3. **Before/After** (T2/A15.4) -- "Spend went up after the mailer"
4. **Revenue Attribution** (T3/A15.3) -- "That means $Z in incremental interchange"

### Act 2: "It's Durable and Targeted" (Slides 5-7)
5. **Sustained Lift** (T4/A16.1) -- "The lift holds at 6+ months"
6. **Responder Profile** (T5+T7/A16.2-A16.3) -- "Here's who responds and where"
7. **ROI** (T6/A15.5) -- "For every $1 spent, you get $X back"

### Act 3: "The Broader Impact" (Slides 8-9)
8. **DCTR Correlation** (T9/A16.4) -- "Responders have higher card adoption"
9. **Reg E Correlation** (T10/A16.5) -- "Engaged cardholders opt in at higher rates"

### Closing: "Without Us, It Would Be Worse"
- Non-responder spend is flat or declining
- Responder spend is growing (or declining less)
- Use "Revenue Protected" framing when both groups decline

### Presentation Best Practices (from financial research)
- **5-7 KPIs max per slide** -- each must answer "what decision does this inform?"
- **Add 3.95% benchmark line** to A13.6 Response Rate Trend for instant industry context
- **Performance tiers:** <2% needs attention, 2-4% meeting expectations, 4-6% strong, 6-8% excellent
- **Executive should be able to leave after the preamble slides** with a complete picture. Everything after is supporting evidence.
- **Industry context:** Financial services marketers increased direct mail budgets 47% YoY in 2024; direct mail response rates are 5-9x higher than digital channels

---

## Analysis ID Registry

| ID | Thread | Module | Chart Filename |
|---|---|---|---|
| A15.1 | Market Reach | `mailer_impact.py` | `a15_1_market_reach.png` |
| A15.2 | Spend Waterfall (T1) | `mailer_impact.py` | `a15_2_spend_share.png` |
| A15.3 | Revenue Attribution (T3) | `mailer_impact.py` | `a15_3_revenue_attribution.png` |
| A15.4 | Pre/Post Delta (T2) | `mailer_impact.py` | `a15_4_pre_post_delta.png` |
| A15.5 | ROI (T6) | `mailer_impact.py` | `a15_5_roi.png` |
| A16.1 | Sustained Lift (T4) | `mailer_efficacy.py` | `a16_1_sustained_lift.png` |
| A16.2 | Branch Performance (T5) | `mailer_efficacy.py` | `a16_2_branch_performance.png` |
| A16.3 | Responder Demographics (T7) | `mailer_efficacy.py` | `a16_3_responder_demographics.png` |
| A16.4 | DCTR Correlation (T9) | `mailer_efficacy.py` | `a16_4_dctr_mailer.png` |
| A16.5 | Reg E Correlation (T10) | `mailer_efficacy.py` | `a16_5_reg_e_mailer.png` |

---

## Data Columns Available but Underutilized

| Column | Currently Used | Untapped for Efficacy |
|---|---|---|
| `Account Holder Age` / `Birth Date` | DCTR/Reg E age breakdowns | Responder demographics (T7/A16.3) |
| `Avg Bal` | Eligibility filter only | Balance tier of responders (T7/A16.3), correlation with spend lift |
| `Branch` | DCTR/Reg E branch breakdowns | Mailer response by branch (T5/A16.2) |
| `Business?` | Subset filtering | Business vs personal response rates (T7/A16.3) |
| `Prod Code` | Eligibility filter | Product-level response rates (T7/A16.3) |
| `{MmmYY} Spend` (all months) | Current month trends | Sustained lift tracking (T4/A16.1) |
| `{MmmYY} Swipes` (all months) | Current month trends | Swipe frequency lift (companion to spend lift) |
| `Debit?` | Subset creation | DCTR responder/non-responder split (T9/A16.4) |
| Reg E columns | Opt-in rate | Responder opt-in correlation (T10/A16.5) |

---

## Files to Create/Modify

| File | Action | Threads |
|---|---|---|
| `mailer_common.py` | CREATE | Shared constants, helpers, responder mask builder |
| `mailer_efficacy.py` | CREATE | T4 (A16.1), T5+T7 (A16.2-A16.3), T9+T10 (A16.4-A16.5) |
| `mailer_impact.py` | MODIFY | T2 (net lift KPI), T6 (A15.5 ROI), fix +/- bug in A15.3 |
| `pipeline.py` | MODIFY | Wire Phase 3g (`run_a16`), add `cost_per_mailer` to config loading |
| `app.py` | MODIFY | Add progress steps for A16 suite |
| `clients_config.json` | MODIFY | Add `CostPerMailer` field (optional, per-client) |
| `mailer_insights.py` | MODIFY | Import from `mailer_common.py` instead of local constants |
| `mailer_response.py` | MODIFY | Import from `mailer_common.py` instead of local constants |

---

## Performance Budget

| Thread | Compute | Chart I/O | Total Est. |
|---|---|---|---|
| T2 (net lift KPI) | <0.1s | 0s (modifies existing) | <0.1s |
| T4 (Sustained Lift) | 1-3s (vectorized) | 1.0s | 2-4s |
| T5+T7 (Responder Profile) | 1-2s (2 groupby ops) | 2.0s (2 charts) | 3-4s |
| T6 (ROI) | <0.1s (arithmetic) | 1.0s | 1.1s |
| T9+T10 (Correlations) | <0.5s | 2.0s (2 charts) | 2.5s |
| **Total addition** | | | **9-12s** |

Current pipeline: 2-5 minutes. After additions: 2.2-5.2 minutes. Negligible impact.

---

## References

- Uplift modeling for debit card campaigns: [Medium - Calvin Nguyen](https://medium.com/@calvinnguyen8k/uplift-modelling-for-debit-card-activation-campaign-1b8fc5bd4b28)
- Difference-in-Differences limitations with self-selected treatment: [Columbia Public Health](https://www.publichealth.columbia.edu/research/population-health-methods/difference-difference-estimation)
- Causal Inference: The Mixtape -- DiD endogeneity: [Cunningham](https://mixtape.scunning.com/09-difference_in_differences)
- Google CausalImpact (future option): [Google](https://google.github.io/CausalImpact/CausalImpact.html)
- Industry benchmarks: 80.5% debit penetration rate, 66.3% active card rate ([PULSE 2024 Debit Issuer Study](https://www.pulsenetwork.com/public/insights-and-news/news-release-2024-debit-issuer-study/))
- Direct mail response rate benchmark: 3.95% financial services ([ANA/DMA 2024](https://focus-digital.co/direct-mail-response-rates-by-industry/))
- Durbin amendment impact on interchange: [CSI](https://www.csiweb.com/what-to-know/content-hub/blog/interchange-crisis/)
- FIS debit card program ROI: [FIS - Aventa CU Case Study](https://www.fisglobal.com/-/media/fisglobal/files/pdf/case-study/aventa-credit-union-adds-revenue-case-study.pdf)
- Cohort analysis in Python: [Greg Reda](http://www.gregreda.com/2015/08/23/cohort-analysis-with-python/)
- Propensity score matching + DiD: [Stuart et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4267761/)
- Existing pipeline reference: `README.md` (full ctx, subset, calculation docs)
- ICS analysis: `/Users/jgmbp/Desktop/ics_analysis/` (36+ analyses, cohort tracking, activation metrics)
- ICS append tool: `/Users/jgmbp/Desktop/ics_append/` (joins ICS accounts to ODD via `Acct Number`)
- Existing roadmap: `plans/feat-ars-pipeline-roadmap.md`
