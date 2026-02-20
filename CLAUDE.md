# Analysis Platform -- Claude Code Instructions

## Session Pickup: 2.21.26

### What just shipped (2/20)
- **PR #9** (`feat/referral-intelligence-engine`): Referral Intelligence Engine added to ICS Toolkit
  - https://github.com/JG-CSI-Velocity/analysis-platform/pull/9
  - 58 files, ~4,100 lines, 212 tests, lint clean
  - 8-step pipeline: load -> normalize -> decode -> temporal -> network -> score -> analyze -> chart
  - 8 analysis artifacts (R01-R08), 5 Plotly chart builders, Excel + PPTX export
  - CLI: `python -m ics_toolkit referral data/file.xlsx`
  - REPL: `from ics_toolkit import run_referral; run_referral("data/file.xlsx")`
  - Settings: `ReferralScoringWeights`, `ReferralStaffWeights`, `ReferralSettings` (Pydantic v2)

### TODO for 2/21
1. **Merge PR #9** -- review and merge the referral engine into main
2. **Close PR #6 on standalone repo** -- `JG-CSI-Velocity/ics_toolkit` PR #6 targeted the wrong repo (standalone instead of monorepo). Close it with a note pointing to PR #9.
3. **Update README.md** -- add Referral Pipeline section alongside ARS/TXN/ICS (CLI usage, Python API, what it does)
4. **Update test counts in README** -- currently says "976 tests", actual is now 1410+
5. **Add `referral:` section to config.example.yaml** if one exists in monorepo (scoring weights, thresholds, code_prefix_map)
6. **Pre-existing failures** -- 4 tests in `tests/platform/test_components.py` fail on main (BatchPipelineRegistry tests expect 3 pipelines but platform_app page structure changed). Fix or update those tests.

### Notes
- ICS analysis PPTX uses `DeckBuilder` class; referral PPTX has its own self-contained slide helpers. Both work fine, just two patterns in the same package.
- `kaleido==0.2.1` pinned; deprecation warnings are noisy but harmless.

---

## Project Structure

```
analysis_platform/
  packages/
    shared/           Shared types, context, config
    ars_analysis/     ARS pipeline (70+ analyses, PPTX deck)
    txn_analysis/     Transaction pipeline (M1-M10 + V4 S1-S9)
    ics_toolkit/      ICS pipeline (37 analyses + append + referral)
    platform_app/     Orchestrator, CLI, Streamlit UI
  tests/
    ars/              ARS tests (141)
    txn/              Transaction tests
    ics/              ICS tests (including ics/referral/ -- 212 tests)
    shared/           Shared tests (50)
    platform/         Platform tests
    integration/      E2E tests
```

## Commands

```bash
make test          # all tests
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package
.venv/bin/python -m pytest tests/ics/referral/ -v   # referral only
.venv/bin/python -m pytest tests/ics/ -v             # all ICS
.venv/bin/python -m pytest tests/ -v                 # everything
```

## Conventions
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push (except 4 pre-existing platform_app failures)
