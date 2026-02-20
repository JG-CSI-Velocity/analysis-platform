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

### Done (2/21)
1. ~~Merge PR #9~~ -- merged into main
2. ~~Close PR #6 on standalone repo~~ -- closed with note pointing to PR #9
3. ~~Update README.md~~ -- added Referral Pipeline section, Python API, CLI usage
4. ~~Update test counts~~ -- 976 -> 1431
5. ~~config.example.yaml~~ -- no config.example.yaml exists in monorepo, skipped
6. ~~Pre-existing platform test failures~~ -- already fixed by platform_app v2 rewrite (merged with PR #9); all 39 platform tests pass

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
- Tests must pass before push
- CI coverage floor is 80% (`--cov-fail-under=80`) -- currently at 88%. 2301 tests, passing.
