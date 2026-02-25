# feat: Market Reach & Responder Impact Visuals

## Overview

Two new analysis slides that tell the "without us it would be worse" story with data:

1. **A15.1 — Market Reach Bubble** — Proportional nested circles: outer = "Eligible with a Debit Card", inner = "Unique Responders". Shows how much of the addressable market the mailer program touches.

2. **A15.2 — Responder Spend Lift** — Side-by-side comparison showing responder vs non-responder spend behavior. Frames success as "responders are driving incremental activity" rather than "claiming credit for existing spend."

Both go into a new `mailer_impact.py` module and slot into the preamble or mailer section of the deck.

---

## Problem Statement / Motivation

Clients say: "Our interchange income is down — is the mailer program even working?"

The current pipeline shows response rates and segment breakdowns, but lacks a visual that:
- Shows **market penetration** — what fraction of eligible cardholders are responding
- Proves **incremental lift** — responders spend more AND that gap is widening
- Frames the narrative as **"without the program, it would be worse"** — non-responder spend is flat/declining while responder spend grows

---

## Proposed Solution

### A15.1 — Market Reach Bubble

A single matplotlib figure with two concentric circles (proportional area), plus KPI callouts.

```
+----------------------------------------------------+
|                                                    |
|          +--------------------------+              |
|          |                          |              |
|          |    Eligible w/ Card      |   KPIs:      |
|          |       (12,450)           |   Mailed: N  |
|          |                          |   Resp: N    |
|          |     +----------+         |   Rate: X%   |
|          |     | Unique   |         |              |
|          |     | Respndrs |         |              |
|          |     |  (1,890) |         |              |
|          |     +----------+         |              |
|          |                          |              |
|          +--------------------------+              |
|                                                    |
+----------------------------------------------------+
```

**Data sources** (all already in `ctx`):
- `eligible_with_debit` — outer circle count (from `pipeline.py:613`)
- Unique responders — union of all `{Month} Resp` columns where value is in `RESPONSE_SEGMENTS` (computed per mailer_response.py pattern)
- Mailed count — union of all `{Month} Mail` columns where value is in `MAILED_SEGMENTS`

**Chart approach**: `matplotlib.patches.Circle` with proportional radii (area = count), plus `ax.text` for labels. Clean, minimal style.

### A15.2 — Responder Spend Lift

A grouped bar chart or diverging bar showing avg spend per account for responders vs non-responders, with a "lift" annotation.

```
+----------------------------------------------------+
|  Avg Monthly Spend per Account                     |
|                                                    |
|  Responders     ████████████████  $482/mo          |
|                                                    |
|  Non-Responders ██████████       $298/mo           |
|                                                    |
|  Lift: +$184/acct (+62%)                           |
|  "Responders generate 62% more interchange activity|
|   per account than non-responding cardholders"      |
+----------------------------------------------------+
```

**Data sources** (computed in `mailer_insights.py`):
- NU responder avg spend — from `_calc_nu_metrics` (`avg_resp` on spend cols)
- NU non-responder avg spend — from `_calc_nu_metrics` (`avg_non_resp` on spend cols)
- TH responder avg spend — from `_calc_th_metrics` (average across TH segments)
- TH non-responder avg spend — from `_calc_th_metrics` (`TNR` key)

The chart uses the **latest month's** averages. A secondary annotation shows the 6-month trend direction for each group.

**Framing language** (auto-generated subtitle):
- If responder spend is growing faster than non-responder: "Responders are driving incremental activity — the gap is widening"
- If non-responder spend is declining: "Non-responding cardholders show declining engagement — the program is protecting revenue"
- If both are growing but responders more: "All cardholders are active, but responders outpace by ${lift}/account"

---

## Technical Approach

### New file: `mailer_impact.py`

Follows the exact same pattern as other modules (dctr.py, reg_e.py, value.py):

```python
# mailer_impact.py — A15 Market Impact & Responder Lift Visuals

def _report(ctx, msg): ...
def _save_chart(fig, path): ...
def _slide(ctx, slide_id, data, category='Mailer'): ...

def run_market_reach(ctx):
    """A15.1 — Nested bubble: eligible w/ card vs unique responders."""
    # 1. Get eligible_with_debit count from ctx
    # 2. Compute unique responders across all mail months
    # 3. Compute total mailed across all mail months
    # 4. Draw concentric circles (area-proportional)
    # 5. Add KPI callouts (mailed, responded, rate, penetration %)
    # 6. _slide(ctx, 'A15.1 - Market Reach', {...})

def run_spend_lift(ctx):
    """A15.2 — Responder vs non-responder spend comparison."""
    # 1. Discover latest mail month with spend data
    # 2. Compute avg spend for responders vs non-responders (all segments combined)
    # 3. Compute lift ($, %)
    # 4. Compute 6-month trend for each group
    # 5. Draw horizontal bar chart with lift annotation
    # 6. Generate framing subtitle
    # 7. _slide(ctx, 'A15.2 - Responder Spend Lift', {...})

def run_mailer_impact_suite(ctx):
    """Run all A15 market impact analyses."""
    ctx = run_market_reach(ctx)
    ctx = run_spend_lift(ctx)
    return ctx
```

### Pipeline integration: `pipeline.py`

1. Import `run_mailer_impact_suite` in `_run_all_analyses()`
2. Call after `run_mailer_response_suite` (Phase 3e)
3. Add progress triggers for the new phase
4. Register slides with `category='Mailer'` so they slot into the mailer section
5. The `_reorder_analysis_slides` function already has a `mailer_agg` bucket for `A13.`, `A14.`, etc. — extend the pattern to `A15.` or add them to `mailer_agg` explicitly

### Slide layout

Both use **layout 13** (full-width, HEADERONLY) — same as value slides and mailer summaries.

### Deck positioning

These go after the mailer summary slides but before the DCTR appendix:
- Recent mailer clusters (Summary + Swipes + Spend)
- **A15.1 Market Reach**
- **A15.2 Responder Spend Lift**
- A1-A5 Overview
- DCTR section
- ...

Alternatively, wire A15.1 into a preamble slot for maximum visibility.

---

## Acceptance Criteria

- [ ] A15.1 renders concentric circles with correct proportional areas
- [ ] A15.1 shows KPI callouts: eligible w/ card, mailed, responded, response rate, penetration %
- [ ] A15.2 shows responder vs non-responder avg spend as horizontal bars
- [ ] A15.2 shows lift in $ and % with annotation text
- [ ] A15.2 subtitle auto-generates appropriate framing language
- [ ] Both slides use layout 13 and appear in correct deck position
- [ ] Progress bar + checklist updated for new phase
- [ ] Pipeline handles edge cases: no mailer data, single month, missing spend columns

---

## Files to Create/Modify

| File | Action | What |
|---|---|---|
| `mailer_impact.py` | **CREATE** | New module with `run_market_reach()`, `run_spend_lift()`, `run_mailer_impact_suite()` |
| `pipeline.py` | MODIFY | Import + call `run_mailer_impact_suite`, add to reorder logic |
| `app.py` | MODIFY | Add progress triggers + sub-steps for A15 phase |

---

## Narrative Framing Notes

The key insight your boss articulated — **"without us it would be worse"** — is best shown through:

1. **A15.1 (Market Reach)**: "We're activating X% of your eligible cardholders"
2. **A15.2 (Spend Lift)**: "Responders generate ${lift} more per account — that's ${lift * responder_count:,} in incremental interchange activity your program is driving"

The auto-generated subtitle avoids claiming credit for all spend. Instead it shows the **differential** — the gap between responders and non-responders — which is the program's measurable contribution.

If non-responder spend is flat or declining while responder spend grows, the chart literally shows "without the program (non-responders), activity stagnates."

---

## References

- Existing responder/non-responder metrics: `mailer_insights.py:164-198` (`_calc_nu_metrics`, `_calc_th_metrics`)
- Eligible with debit: `pipeline.py:613` (`ctx['eligible_with_debit']`)
- Response segments: `mailer_response.py:41-48` (`RESPONSE_SEGMENTS`, `MAILED_SEGMENTS`)
- Slide registration pattern: `_slide(ctx, id, data_dict)` used in all modules
- Value module (similar narrative framing): `value.py:252-424`
