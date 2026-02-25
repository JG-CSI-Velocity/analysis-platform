# Impact Analysis: Reviewer Recommendations vs. Real Scale

**Context correction:** This is a **team tool for 300+ client reviews**, not a solo developer tool for 12 clients. Multiple CSMs will operate it concurrently. The tool is being presented to a VP for team-wide rollout.

This changes the calculus on nearly every reviewer recommendation.

---

## Recommendation-by-Recommendation Verdict

### 1. Kill the plugin registry / ABC pattern → Use plain function list

| Reviewer | Recommendation |
|----------|---------------|
| DHH | Kill it. Use a list of functions. |
| Simplicity | Kill it. Use a list of functions. |
| Kieran | Keep but fix the code (type annotations, error handling). |

**Impact at 300+ clients / team scale:**

| Factor | Plain Functions | ABC + Registry (Current Plan) |
|--------|----------------|-------------------------------|
| Adding a new analysis module | Add function + add to list | Create class, set attributes, add `@register`, add to `MODULE_ORDER` |
| Onboarding new developer | Read a list, write a function | Learn ABC, decorator pattern, registry, `__init_subclass__` |
| Column validation per module | Each function validates its own inputs (ad hoc) | Centralized `validate()` on base class (consistent) |
| Skipping modules per client | Caller filters the list by name/flag | `module.validate(ctx)` returns errors; runner skips gracefully |
| Logging which modules ran/failed | Caller wraps each call in try/except + log | Runner iterates `ordered_modules()`, logs each uniformly |
| Error isolation | Caller must remember try/except around each call | Runner handles isolation; one module failure doesn't kill the batch |

**Verdict: KEEP the ABC + registry, but simplify it.**

At 300+ clients, the pipeline runs in batch mode for hours. When module 11 of 15 fails for client 247 of 300, you need:
- Structured logging of which module failed, for which client, with what error
- The ability to skip that module and continue the batch
- A `validate()` check that catches missing columns *before* wasting 10 minutes of processing

A plain function list pushes all of this into the runner loop as ad-hoc `try/except` blocks. The ABC centralizes it. The overhead of the ABC is ~50 lines of code. The operational benefit at scale is significant.

**What to cut from the current plan:**
- Drop `__init_subclass__` enforcement (nice but unnecessary complexity)
- Drop `importlib.import_module` dynamic loading — use explicit imports like the reviewers suggest, but keep the `@register` decorator so the registry stays a single source of truth for "what modules exist"
- Apply Kieran's fixes: `tuple[str, ...]` for required_columns, type annotations, error handling in `load_all_modules()`

**Net change:** ~20 lines removed, ~15 lines of type fixes added. Registry stays.

---

### 2. Cut the scheduling system entirely

| Reviewer | Recommendation |
|----------|---------------|
| DHH | Premature. Build when requirement exists. |
| Simplicity | Cut it. Zero specification. |
| Kieran | Did not comment (code-focused review). |

**Impact at 300+ clients / team scale:**

With 300+ clients, scheduling is not a "nice to have" — it's how the team knows **who runs what, when**. Without it:
- CSMs manually track which clients are due this month in a spreadsheet
- No visibility into which reviews were completed vs. overdue
- The VP cannot see pipeline utilization or compliance status

**However**, the reviewers are right that the *current specification is zero*. Building a scheduling system without knowing the VP's requirements risks building the wrong thing.

**Verdict: KEEP scheduling, but DEFER the implementation to Phase 4 (after the core pipeline works).**

Move scheduling out of Phase 3 (which is already the mega-phase) and into Phase 4 alongside Streamlit. This way:
- Phase 3 delivers a working pipeline + CLI without schedule complexity
- Phase 4 can incorporate VP feedback on what scheduling means to them
- The `scheduling/` package is still in the plan but not blocking the critical path

**Net change:** Resequence, don't cut. ~0 lines changed, reduced risk of Phase 3 scope creep.

---

### 3. Drop Typer / Rich / Questionary → Use argparse

| Reviewer | Recommendation |
|----------|---------------|
| DHH | Drop all three. Use argparse or just Streamlit. |
| Simplicity | Keep Typer but reduce to 4 commands. Cut questionary. |
| Kieran | Keep but fix dependency double-pinning. |

**Impact at 300+ clients / team scale:**

| Factor | argparse | Typer + Rich |
|--------|----------|-------------|
| `ars batch` processing 300 clients | Plain text output | Rich progress bars showing 147/300, ETA, per-client status |
| Error display for non-technical CSM | Stack trace | Rich error panel: "File Locked — Close the file in Excel and try again" |
| `ars --help` for new team member | Basic help text | Colored, grouped commands with descriptions |
| Tab completion for client IDs | Manual implementation | Built into Typer |
| Batch processing time visibility | None (silent until done) | Live progress: which client, which step, how many remaining |

At 12 clients, Rich progress bars are vanity. At 300 clients with a batch run taking 30+ minutes, they're operational visibility.

**Verdict: KEEP Typer + Rich. CUT questionary.**

The `ars wizard` with questionary is a valid cut — CSMs use Streamlit, not a terminal wizard. But Typer + Rich earn their place for batch operations at scale.

**Net change:** Remove `questionary>=2.0` from dependencies. Remove `ars wizard` command. Keep all other CLI commands. Saves ~100 lines of wizard code + 1 dependency.

---

### 4. Drop Pydantic Settings → Use tomllib + dataclass

| Reviewer | Recommendation |
|----------|---------------|
| DHH | Drop Pydantic entirely. tomllib + dataclass. |
| Simplicity | Keep but flatten from 4 classes to 1. |
| Kieran | Keep but fix settings_customise_sources signature. |

**Impact at 300+ clients / team scale:**

| Factor | tomllib + dataclass | Pydantic Settings |
|--------|--------------------|--------------------|
| CSM edits config with wrong type | Silent failure at runtime, possibly 200 clients deep | Immediate validation error with field name + expected type |
| Environment variable overrides | Manual implementation | Built-in: `ARS__PATHS__ARS_BASE=/new/path` |
| Config from multiple sources (default + override) | Manual merge logic | Built-in TOML source chain |
| Team member sets `chart_dpi = "high"` | `int("high")` fails somewhere downstream | `ValidationError: chart_dpi - Input should be a valid integer` |

With multiple team members editing config files, validation prevents cascading failures. A bad config value at client 1 shouldn't be discovered at client 300.

**Verdict: KEEP Pydantic Settings. KEEP nested structure.**

The 4-class nesting maps to TOML sections (`[paths]`, `[pipeline]`, `[logging]`, `[review_schedule]`). Flattening would make the TOML file a flat list of 15+ keys with no grouping — worse for the humans editing it.

Apply Kieran's fix: explicit parameter signature on `settings_customise_sources`.

**Net change:** ~5 lines of signature fix. Structure unchanged.

---

### 5. Cut agent-native CLI commands (ars config show, ars scan, ars history)

| Reviewer | Recommendation |
|----------|---------------|
| DHH | Premature. No agent exists. |
| Simplicity | Cut config show, scan, history. Keep --json on run/batch only. |
| Kieran | Did not comment. |

**Impact at 300+ clients / team scale:**

| Command | Solo dev value | Team (300+ clients) value |
|---------|---------------|--------------------------|
| `ars scan --month 2026.02 --json` | Low | **High** — "which clients have data ready this month?" across 300+ clients |
| `ars history --client 1200 --json` | Low | **Medium** — "when was client 1200 last processed? by whom?" |
| `ars config show --json` | Low | **Medium** — "what config is this machine using?" for debugging across team |
| `--json` on all commands | Low | **High** — enables Task Scheduler scripts, batch orchestration |
| JSONL log sink | Low | **Medium** — enables centralized log aggregation if team grows |

**Verdict: KEEP `ars scan` and `--json` flag. DEFER `ars history` and `ars config show` to Phase 4. CUT JSONL sink for now.**

`ars scan` is the most valuable command at 300+ clients — it answers "what's ready to process this month?" which is the first question every CSM asks. `--json` enables scripting batch workflows across the team.

`ars history` and `ars config show` are useful but not critical path. Add them alongside scheduling in Phase 4.

JSONL sink can be added with a single `logger.add()` call later if centralized logging becomes a need.

**Net change:** Remove JSONL sink (~15 lines). Move 2 commands to Phase 4. Keep `ars scan` and `--json`.

---

### 6. Cut ProgressCallback protocol

| Reviewer | Recommendation |
|----------|---------------|
| Simplicity | Cut it. Use Loguru. |
| DHH | Simplify to a single callback function. |
| Kieran | Protocol is correct. No issues. |

**Impact at 300+ clients / team scale:**

When a CSM runs a batch of 50 clients through Streamlit, they need to see:
- "Processing client 23 of 50: Guardians CU"
- "Step 2 of 3: Analyzing data..."
- "Client 23 complete. 27 remaining. ~14 min left."

This cannot come from reading log files. It requires real-time progress updates pushed to the Streamlit UI.

**Verdict: KEEP the ProgressCallback protocol.**

At 300+ clients with batch runs, progress reporting is a core UX requirement, not a nice-to-have. The Protocol pattern is the right abstraction — it keeps the pipeline runner UI-agnostic while letting both Streamlit and CLI show progress in their own way.

DHH's suggestion to simplify to a single function `on_progress(step, message)` is reasonable. But the 4-method protocol maps cleanly to the batch workflow lifecycle and is only 6 lines of code.

**Net change:** 0 lines. Keep as-is.

---

### 7. Strangler fig migration → Clean break

| Reviewer | Recommendation |
|----------|---------------|
| DHH | Wrong pattern. Do a clean break in one shot. |
| Simplicity | Did not challenge directly. |
| Kieran | Did not comment. |

**Impact at 300+ clients / team scale:**

If the tool is being used by a team processing 300+ clients, there may be active users during migration. A clean break means:
- One day the tool works with flat files
- Next day it requires `pip install -e .` and new import paths
- Any team member who didn't get the memo is broken

The strangler fig means:
- Flat files still work during migration
- Team members can update at their own pace
- If Phase 3 has a regression, Phase 2 code still runs

**However:** If you control the deployment (single machine / shared drive) and can coordinate a cutover, a clean break is faster.

**Verdict: CONTEXT-DEPENDENT.**

- If team deploys from a shared location (M: drive) → **clean break is fine** (you update once, everyone gets it)
- If team members have local installations → **strangler fig is safer**

The plan already has the strangler fig approach. Keep it unless you confirm single-point deployment.

**Net change:** 0 lines. Keep current approach, revisit during Phase 3.

---

### 8. PipelineContext: 8 fields vs. 40+ fields needed

| Reviewer | Recommendation |
|----------|---------------|
| Kieran | Must include all 40+ fields from existing ctx dict or migration fails silently. |
| Simplicity | Keep but remove untyped dict escape hatches. |
| DHH | A dict is fine. |

**Impact at 300+ clients / team scale:**

This is a correctness issue, not a scale issue. Kieran is right: the current `ctx` dict has ~40 keys, and the proposed dataclass has 8 fields with 2 untyped `dict` escape hatches. This will cause runtime failures during migration.

**Verdict: APPLY Kieran's recommendation.**

Expand `PipelineContext` to include the real fields (or use Kieran's suggested two-layer structure: `ClientInfo` + `DataSubsets` + `PipelineContext`). Type the `results` field as `dict[str, list[AnalysisResult]]`. Replace `config: dict` with `config: ARSSettings`.

**Net change:** ~40 lines added to `context.py`. Prevents silent migration failures.

---

## Summary: What Changes, What Stays

### KEEP (plan is correct at 300+ scale)

| Item | Reason at Scale |
|------|----------------|
| ABC + @register + MODULE_ORDER | Error isolation + validation across 300+ client batch runs |
| Pydantic Settings (nested) | Config validation prevents cascading failures across team |
| Typer + Rich CLI | Batch progress visibility for 30+ minute runs |
| ProgressCallback protocol | Real-time Streamlit progress for 50-client batches |
| Scheduling system | 300+ clients need "who runs what, when" tracking |
| `--json` flag | Enables scripted batch orchestration |
| `ars scan` command | "What's ready this month?" across 300+ clients |
| 5-phase structure | User preference; phases are well-scoped |
| Strangler fig migration | Safer for team deployment |

### CUT (reviewers are right regardless of scale)

| Item | Lines Saved | Reason |
|------|-------------|--------|
| `ars wizard` + `questionary` dependency | ~100 | CSMs use Streamlit. Third interface adds complexity with no user. |
| `__init_subclass__` enforcement on ABC | ~10 | Nice but unnecessary. Caught by tests anyway. |
| `pkgutil.walk_packages` auto-discovery | ~0 | Already cut in enhanced plan. Confirm explicit imports. |
| JSONL log sink | ~15 | No consumer exists today. Single `logger.add()` to add later. |
| `multi_chart_figure` context manager | ~10 | Add when a multi-panel chart needs it. |

**Total cut: ~135 lines**

### MODIFY (adjust based on reviewer feedback)

| Item | Change | Impact |
|------|--------|--------|
| `PipelineContext` | Expand from 8 → 40+ fields using Kieran's two-layer structure | +40 lines, prevents migration failure |
| `required_columns` | Change `list[str]` → `tuple[str, ...]` (mutable default fix) | 2-line change |
| All registry functions | Add return type annotations | +10 lines |
| `ordered_modules()` | Raise on missing module instead of silent skip | 3-line change |
| `get_module()` | Wrap `KeyError` in `ConfigError` | 5-line change |
| `load_all_modules()` | Add per-module error handling | +10 lines |
| `settings_customise_sources` | Use explicit params instead of `**kwargs` | 5-line change |
| `LoggingConfig.log_dir` | `str` → `Path` | 1-line change |
| Loguru file sinks | Add `encoding="utf-8"` for Windows | 3 lines |
| `AnalysisResult.excel_data` | `dict` → `dict[str, pd.DataFrame]` | 1-line change |
| `section` attribute | `str` → `Literal[...]` | 2-line change |
| pyproject.toml | Add upper bounds: `matplotlib<4.0`, `pydantic<3.0`, `ruff<1.0` | 3-line change |
| pyproject.toml | Remove `questionary` dependency | 1-line change |
| `PIPELINE_STEPS` | Raw tuple → `NamedTuple` or frozen `dataclass` | +8 lines |
| Chart context manager | Add return type annotation + consider `save_path` param | +5 lines |
| `ARSError` | Add `__repr__` that includes `detail` | +5 lines |

### DEFER (move to later phase, don't cut)

| Item | Move To | Reason |
|------|---------|--------|
| `ars history` command | Phase 4 | Useful but not critical path |
| `ars config show` command | Phase 4 | Useful but not critical path |
| Scheduling implementation | Phase 4 | Keep in plan but build after core pipeline works + VP feedback |

---

## Net Impact on Plan

| Metric | Before | After |
|--------|--------|-------|
| Phases | 5 | 5 (unchanged) |
| Dependencies | 12 | 11 (drop questionary) |
| Planned code removed | — | ~135 lines |
| Planned code added | — | ~95 lines (type fixes, expanded PipelineContext) |
| Code quality fixes | — | 15 specific changes from Kieran review |
| Risk reduction | — | PipelineContext migration failure prevented |
| Phase 3 scope | Pipeline + CLI + Scheduling | Pipeline + CLI (scheduling deferred to Phase 4) |
