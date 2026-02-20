# Fix Chart Formatting: Spines, Positioning, and Funnel Sizing

**Date:** 2026-02-07
**Branch:** `test/close-coverage-gaps`
**Type:** fix / visual polish

---

## Problem Statement

Several formatting issues across DCTR and Reg E chart slides:

1. **All charts show left/bottom spines** -- only top/right are removed today
2. **Single-chart slides feel left-bottom aligned** -- no centering when height-constrained
3. **DCTR by Product Type (A7.19)** -- chart sits too low, needs to move up and center
4. **DCTR funnels (A7.7 + A7.8)** -- not the same visual height on the merged slide, positioned too far left
5. **Reg E funnels (A8.10 + A8.11)** -- different aspect ratio from DCTR funnels; should match
6. **New slides lack visual impact** -- font sizes too small, inconsistent with established slides

---

## Sprint 1: Remove All Spines Globally

### 1A. Update `apply_matplotlib_defaults()` in deck_builder.py

**File:** `packages/ars_analysis/src/ars_analysis/deck_builder.py` line 985-1006

Add `axes.spines.left: False` and `axes.spines.bottom: False` to the rcParams:

```python
plt.rcParams.update({
    ...
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,      # NEW
    "axes.spines.bottom": False,     # NEW
    ...
})
```

This removes spines from **all** DCTR and Reg E charts at once since the pipeline calls `apply_matplotlib_defaults()` before any analysis runs.

### 1B. Remove redundant per-chart spine hiding

Clean up all the `ax.spines["top"].set_visible(False)` / `ax.spines["right"].set_visible(False)` calls scattered across:

- `dctr/_core.py` (~20 locations)
- `dctr/_visualizations.py` (~15 locations)
- `reg_e/_core.py` (~12 locations)

These are now redundant since rcParams handles it globally. Remove them to reduce noise.

**Keep** the `for spine in ax.spines.values(): spine.set_visible(False)` calls in branch trend charts (A7.10a, A7.10b, A8.4b) -- those already hide all spines and are fine.

### 1C. Update `ars.mplstyle`

**File:** `packages/ars_analysis/src/ars_analysis/ars.mplstyle`

Add left/bottom spine settings to match:

```
axes.spines.top    : false
axes.spines.right  : false
axes.spines.left   : false
axes.spines.bottom : false
```

This only affects attrition (which loads this style file), but keeps both sources consistent.

---

## Sprint 2: Fix Single-Chart Slide Centering

### 2A. Center images horizontally in `_add_fitted_picture()`

**File:** `packages/ars_analysis/src/ars_analysis/deck_builder.py` lines 306-318

Current behavior: When a chart is height-constrained, its width shrinks but it stays pinned to the `left` coordinate -- appearing left-aligned.

Fix: Calculate actual rendered width and center the image within the allocated `max_width` slot:

```python
def _add_fitted_picture(self, slide, img_path, left, top, max_width, max_height=None):
    effective_max_h = max_height or self.MAX_CHART_HEIGHT
    from PIL import Image
    with Image.open(img_path) as img:
        native_w, native_h = img.size
    aspect = native_h / native_w

    height_at_width = int(max_width * aspect)
    if height_at_width > effective_max_h:
        # Height-constrained: center horizontally within the allocated width
        actual_width = int(effective_max_h / aspect)
        offset = (max_width - actual_width) // 2
        slide.shapes.add_picture(img_path, left + offset, top, height=effective_max_h)
    else:
        slide.shapes.add_picture(img_path, left, top, width=max_width)
```

This ensures charts that don't fill their width slot are centered rather than left-pinned. Uses EMU arithmetic since `Inches()` returns EMU values.

### 2B. Nudge single-chart layouts up slightly

**File:** `packages/ars_analysis/src/ars_analysis/deck_builder.py` lines 278-301

Adjust layout 9 (most common) and layout 8 top values:

| Layout | Current Top | New Top | Notes |
|--------|------------|---------|-------|
| 8      | 2.2"       | 1.8"    | Full-width (Product Type, Exec Summary) |
| 9      | 1.8"       | 1.6"    | Standard single chart |
| 4, 5, 11 | 1.8"    | 1.6"    | Variants of single chart |

This moves all single-chart slides up ~0.2" to avoid the bottom-heavy feel.

---

## Sprint 3: Fix Funnel Slide Sizing and Positioning

### 3A. Make Reg E funnels match DCTR aspect ratio

**File:** `packages/ars_analysis/src/ars_analysis/reg_e/_core.py`

Change figsize from `(12, 10)` landscape to `(10, 12)` portrait to match DCTR:

- Line 1665: `fig, ax = plt.subplots(figsize=(10, 12))` (was `(12, 10)`)
- Line 1764: `fig, ax = plt.subplots(figsize=(10, 12))` (was `(12, 10)`)

Both DCTR funnels already use `(10, 12)`. This makes all four funnels the same aspect ratio, so they render at the same size on merged slides.

### 3B. Center merged funnel slides

**File:** `packages/ars_analysis/src/ars_analysis/deck_builder.py` lines 320-331

Current multi-chart positioning: left=0.5", right=6.8" with width=5.8" each.

On a 13.33" slide, two 5.8" images with a gap = 0.5 + 5.8 + gap + 5.8 = 12.6" max. But portrait funnels (10:12) at 5.5" max height only render ~4.58" wide each.

Adjust the multi positioning for layout 6 to move the charts right and center them better:

```python
if layout_index == 6:
    return (Inches(1.8), Inches(0.8), Inches(7.0), Inches(5.5))
```

This moves the top up from 2.0" to 1.8", shifts both images slightly right, and tightens the width to better match the actual rendered funnel size.

### 3C. Add centering to multi-screenshot builder

Apply the same centering logic from Sprint 2A to `_build_multi_screenshot_slide()`. When each funnel image is height-constrained, center it within its allocated width slot so both funnels appear evenly spaced.

---

## Sprint 4: Improve New Slide Formatting

The new slides (Opportunity, Exec Summary, Cohort, Seasonality) use noticeably smaller fonts than the established slides.

### 4A. Standardize font sizes on new chart slides

Established slide convention (from chart_style.py constants):
- Title: 24pt bold
- Axis labels: 20pt bold
- Data labels: 20pt bold
- Tick labels: 18pt
- Legend: 16pt

New slides currently use:
- Title: 16pt
- Axis labels: 12-14pt
- Data labels: 9-10pt
- Tick labels: 12pt
- Legend: 11-12pt

**Files to update:**

| File | Function | Current Sizes | Target Sizes |
|------|----------|--------------|--------------|
| `dctr/_core.py` | `run_dctr_by_product` (A7.19) | title=16, axis=14, data=10, tick=12, legend=11 | title=22, axis=18, data=14, tick=16, legend=14 |
| `dctr/_core.py` | `run_dctr_opportunity` (A7.14) | title=16, axis=14, data=14, tick=12 | title=22, axis=18, data=16, tick=16 |
| `dctr/_core.py` | `run_dctr_cohort_capture` | similar small sizes | match convention |
| `reg_e/_core.py` | `run_reg_e_opportunity` (A8.14) | title=16, axis=14, data=14, tick=12 | title=22, axis=18, data=16, tick=16 |
| `reg_e/_core.py` | `run_reg_e_cohort` (A8.15) | title=16, axis=14, data=9, tick=12, legend=12 | title=22, axis=18, data=14, tick=16, legend=14 |
| `reg_e/_core.py` | `run_reg_e_seasonality` (A8.16) | title=14-18, axis=12, data=10-12, tick=12 | title=22, axis=18, data=14, tick=16 |

Note: Executive Summary slides (A7.0, A8.0) are KPI dashboards with `figsize=(20, 10)` and use `axis("off")`. Their internal font sizes are fine since they render in a self-contained canvas. Leave them as-is.

### 4B. Remove black bar edges on new slides

Several new charts use `edgecolor="black", linewidth=1` on bars, which looks heavy. The established style uses `edgecolor="none"` or `edgecolor="white"`:

- `dctr/_core.py` line 1640: `edgecolor="black"` on Product Type bars
- `dctr/_core.py` line 1650: same
- `reg_e/_core.py` line 2083: `edgecolor="black"` on Opportunity bars

Change all to `edgecolor="white", linewidth=0.5` to match the clean aesthetic of established charts.

### 4C. Bump "+N accts" annotation size

In both opportunity functions, the `+N accts` annotations use fontsize=10 which is tiny:

- `dctr/_core.py` ~line 1466: `fontsize=10` → `fontsize=14`
- `reg_e/_core.py` line 2098: `fontsize=10` → `fontsize=14`

---

## Verification

After each sprint:
1. Run the pipeline against a test ODD file with `deck_only=True`
2. Open the PPTX and visually verify:
   - No spines visible on any chart
   - Single charts centered on slides (not left-pinned)
   - DCTR funnels: same height, centered on merged slide
   - Reg E funnels: same size/aspect ratio as DCTR funnels
   - New slides have readable, consistent font sizes
3. Run full test suite: `make test` (1180 tests should pass)

---

## Files Modified

| File | Changes |
|------|---------|
| `deck_builder.py` | Remove all spines in rcParams, center images in `_add_fitted_picture`, adjust layout top values, center multi-screenshot images |
| `ars.mplstyle` | Add left/bottom spine = false |
| `dctr/_core.py` | Remove redundant spine code, bump font sizes on new slides, clean bar edges |
| `dctr/_visualizations.py` | Remove redundant spine code |
| `reg_e/_core.py` | Remove redundant spine code, change funnel figsize to (10,12), bump font sizes, clean bar edges |
