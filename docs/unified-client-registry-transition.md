# Unified Client Registry -- Transition Plan

**Status:** Phase 1 complete (ICS standalone), Phases 2-4 pending
**Date:** 2026-02-07

---

## Problem

Each pipeline (ARS, TXN, ICS) handles client configuration differently:

| Pipeline | Format | Location | Fields |
|----------|--------|----------|--------|
| **ARS** | JSON | `M:\ARS\Config\clients_config.json` | `eligible_stat_code`, `eligible_prod_code`, `ICRate`, `BranchMapping`, `NSF_OD_Fee` |
| **TXN** | YAML | `config.yaml` (local) | `ic_rate` auto-derived from filename |
| **ICS** | YAML | `config.yaml` (local) | `open_stat_codes`, `closed_stat_codes` per-client |

This means:
- Client-specific settings are scattered across 3 files in 2 formats
- Adding a new client requires editing multiple config files
- Branch mapping, product codes, and stat codes are duplicated or inconsistent
- No single source of truth for "what do we know about client 1759?"

---

## Vision: Single Master Registry

One file, all clients, all pipelines:

```
M:\Config\clients_registry.yaml   (or .json)
```

```yaml
"1759":
  client_name: "Pacific Coast CU"
  csm: "JamesG"

  # Shared fields (used by multiple pipelines)
  interchange_rate: 0.0195
  branch_mapping:
    "HQ": "Headquarters"
    "BR1": "Downtown"
  prod_code_mapping:
    "100": "Regular Checking"
    "200": "Savings"

  # ICS-specific
  ics:
    open_stat_codes: ["A"]
    closed_stat_codes: ["C"]

  # ARS-specific
  ars:
    eligible_stat_code: "A"
    eligible_prod_code: "100"
    eligible_mailable: "Y"
    nsf_od_fee: 25.0

  # TXN-specific
  txn:
    ic_rate: 0.0195

"1776":
  client_name: "Liberty Federal CU"
  csm: "GMiller"
  # Uses defaults for all pipelines
```

---

## Phase 1: ICS Standalone (DONE)

**Implemented in:** `JG-CSI-Velocity/ics_toolkit` on `main`

### What was built

| File | Purpose |
|------|---------|
| `ics_toolkit/client_registry.py` | `MasterClientConfig` Pydantic model, `resolve_master_config_path()`, `load_master_config()`, `get_client_config()` |
| `ics_toolkit/settings.py` | `client_config_path` field, `_apply_master_config()` in model validator, `branch_mapping` / `prod_code_mapping` fields |
| `ics_toolkit/analysis/data_loader.py` | `_enrich_labels()` step replaces coded Branch/Prod Code values with readable labels |

### How it works

1. `AnalysisSettings.client_config_path` points to the master file
2. Path resolution: explicit path > `ICS_CLIENT_CONFIG` env var > default M drive paths
3. On settings init, `derive_client_fields` calls `_apply_master_config()`:
   - Loads master file (JSON or YAML)
   - Looks up `client_id` (auto-extracted from data filename)
   - Merges non-None fields as the base layer
4. config.yaml `clients:` entries override master file (higher priority)
5. CLI args override everything
6. `_enrich_labels()` runs after data normalization, before analyses

### Key design decisions

- **`extra="ignore"`** on `MasterClientConfig` -- tolerates ARS-only fields without error
- **ARS key normalization** -- `BranchMapping` -> `branch_mapping`, `ICRate` -> `interchange_rate`
- **Graceful degradation** -- missing file, missing client, or unmounted M drive logs a warning and uses defaults
- **No new dependencies** -- uses only `pydantic`, `yaml`, `json` (all already in the project)

### Test coverage

- 31 tests in `tests/test_client_registry.py` (model, path resolution, JSON/YAML loading, error handling)
- 14 tests in `tests/test_settings.py` (integration, priority chain, graceful degradation)
- 5 tests in `tests/analysis/test_data_loader.py::TestEnrichLabels` (label mapping)
- Full suite: 827 tests passing

---

## Phase 2: Extract to `packages/shared/`

**Goal:** Move `client_registry.py` from ICS to the shared package so all pipelines can use it.

### Steps

1. **Copy module:**
   ```
   ics_toolkit/client_registry.py -> packages/shared/src/shared/client_registry.py
   ```

2. **Update imports in ICS:**
   ```python
   # Before
   from ics_toolkit.client_registry import load_master_config
   # After
   from shared.client_registry import load_master_config
   ```

3. **Remove standalone copy** from `ics_toolkit/`

4. **Add to shared `__init__.py`:**
   ```python
   from shared.client_registry import (
       MasterClientConfig,
       load_master_config,
       resolve_master_config_path,
       get_client_config,
   )
   ```

5. **Update `PlatformConfig`** to include `client_registry_path`:
   ```python
   class PlatformConfig(BaseModel):
       client_registry_path: Path | None = None  # NEW
       # ... existing fields
   ```

6. **Wire into orchestrator:**
   ```python
   def run_pipeline(pipeline, input_files, ..., client_config=None):
       if client_config is None and platform_config.client_registry_path:
           registry = load_master_config(platform_config.client_registry_path)
           client_config = get_client_config(client_id, registry)
   ```

### Tests

- Move `test_client_registry.py` to `tests/shared/`
- Verify ICS still passes with shared import
- Add shared test that loads a multi-pipeline config file

---

## Phase 3: ARS Migration

**Goal:** ARS reads from the unified registry instead of its own `clients_config.json`.

### Steps

1. **Merge ARS fields into the master schema:**
   ```python
   class MasterClientConfig(BaseModel):
       # ... existing fields ...
       # ARS-specific (extracted from current clients_config.json)
       eligible_stat_code: str | None = None
       eligible_prod_code: str | None = None
       eligible_mailable: str | None = None
       reg_e_opt_in: str | None = None
       nsf_od_fee: float | None = None
   ```

2. **Migration script** (`scripts/migrate_ars_config.py`):
   - Reads existing `M:\ARS\Config\clients_config.json`
   - Merges into the unified registry format
   - Writes to `M:\Config\clients_registry.yaml`
   - Preserves all manually-entered fields (`ICRate`, `NSF_OD_Fee`, `BranchMapping`)

3. **Update `ars_config.py`:**
   - `CONFIG_PATH` points to unified registry
   - `step_load_config(ctx)` uses `shared.client_registry` instead of raw JSON

4. **Backward compatibility:**
   - Keep `clients_config.json` as read-only fallback for 1 release cycle
   - ARS pipeline logs deprecation warning if falling back to old file
   - Remove after all clients are in the unified registry

### Tests

- ARS unit tests: load from unified format, verify all fields
- Migration script test: old format -> new format roundtrip
- Integration: ARS pipeline end-to-end with unified config

---

## Phase 4: TXN Integration + Code Sheet Scanner

**Goal:** TXN reads from the unified registry. Automate populating the registry from code sheet templates.

### Steps

1. **TXN settings integration:**
   - Add `client_config_path` to TXN `Settings`
   - TXN-specific fields in registry: `ic_rate`
   - `_enrich_labels()` for TXN merchant categories

2. **Code sheet scanner** (`scripts/scan_code_sheet.py`):
   - Reads a standardized Excel code sheet template
   - Extracts: branch mapping, product codes, account types, stat codes
   - Writes/updates entries in the unified registry
   - Validates against schema before writing

3. **Template:**
   - Create `templates/code_sheet_template.xlsx` with expected columns
   - Provide instructions for CSMs to fill out per client

### Code Sheet Template Schema

| Sheet | Columns | Maps To |
|-------|---------|---------|
| Branches | `Code`, `Name` | `branch_mapping` |
| Product Codes | `Code`, `Name` | `prod_code_mapping` |
| Account Types | `Code`, `Name` | `account_type_mapping` |
| Settings | `Key`, `Value` | `open_stat_codes`, `interchange_rate`, etc. |

---

## File Structure (Final State)

```
analysis_platform/
├── config/
│   └── platform.yaml                     # References client_registry_path
├── packages/
│   ├── shared/
│   │   └── src/shared/
│   │       ├── client_registry.py        # Unified loader (from Phase 2)
│   │       └── config.py                 # PlatformConfig + client_registry_path
│   ├── ars_analysis/
│   │   └── src/ars_analysis/
│   │       └── ars_config.py             # Uses shared.client_registry (Phase 3)
│   ├── txn_analysis/
│   │   └── src/txn_analysis/
│   │       └── settings.py               # Uses shared.client_registry (Phase 4)
│   └── ics_toolkit/
│       └── src/ics_toolkit/
│           └── settings.py               # Uses shared.client_registry (Phase 2)
├── scripts/
│   ├── migrate_ars_config.py             # Phase 3: one-time migration
│   └── scan_code_sheet.py                # Phase 4: code sheet -> registry
└── templates/
    └── code_sheet_template.xlsx          # Phase 4: CSM-facing template
```

**M Drive (final state):**
```
M:\Config\
└── clients_registry.yaml                # THE single source of truth
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| M drive not mounted | Graceful degradation: logs warning, uses defaults from config.yaml |
| ARS format drift | ARS key normalization in `MasterClientConfig.normalize_ars_keys()` |
| Concurrent edits | File is read-only at runtime; edits only via scripts or manual YAML editing |
| Missing client | `get_client_config()` returns None; pipeline uses defaults |
| Schema evolution | `extra="ignore"` tolerates unknown fields; add new fields with None defaults |

---

## Timeline (Suggested)

| Phase | Scope | Effort | Dependency |
|-------|-------|--------|------------|
| Phase 1 | ICS standalone | DONE | None |
| Phase 2 | Extract to shared/ | 1-2 hours | Phase 1 |
| Phase 3 | ARS migration | 3-4 hours | Phase 2 |
| Phase 4 | TXN + code sheet scanner | 4-6 hours | Phase 2 |
