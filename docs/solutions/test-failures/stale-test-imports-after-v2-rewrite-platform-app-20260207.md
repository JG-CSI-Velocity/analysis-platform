---
module: platform_app
date: 2026-02-07
problem_type: test_failure
component: testing_framework
symptoms:
  - "ImportError: cannot import name 'PIPELINE_ORDER' from 'platform_app.pages.batch_workflow'"
  - "ImportError: cannot import name 'PIPELINES' from 'platform_app.pages.batch_workflow'"
  - "4 tests in TestBatchPipelineRegistry fail after V2.0 page rewrite"
root_cause: test_isolation
resolution_type: test_fix
severity: medium
tags: [test-migration, v2-rewrite, import-error, stale-tests]
---

# Troubleshooting: Stale Test Imports After V2.0 Page Rewrite

## Problem
After rewriting the Streamlit UI from V1 (numbered pages with monolithic pipeline dicts) to V2 (st.navigation with core modules), 4 tests failed because they imported constants (`PIPELINE_ORDER`, `PIPELINES`) from `batch_workflow.py` that no longer exist in the V2.0 version.

## Environment
- Module: platform_app (UAP V2.0 Streamlit UI)
- Python Version: 3.11.14
- Affected Component: tests/platform/test_components.py::TestBatchPipelineRegistry
- Date: 2026-02-07

## Symptoms
- `ImportError: cannot import name 'PIPELINE_ORDER' from 'platform_app.pages.batch_workflow'`
- `ImportError: cannot import name 'PIPELINES' from 'platform_app.pages.batch_workflow'`
- 4 out of 43 platform tests fail; other 39 pass
- Error occurs at import time, not at assertion time

## What Didn't Work

**Direct solution:** The problem was identified and fixed on the first attempt.

## Solution

Replaced the `TestBatchPipelineRegistry` class (4 tests importing removed V1 constants) with 21 new tests covering the V2.0 core modules that replaced the V1 architecture:

**Code changes:**

```python
# Before (broken -- V1 constants removed in V2.0):
class TestBatchPipelineRegistry:
    def test_pipeline_order_has_three_entries(self):
        from platform_app.pages.batch_workflow import PIPELINE_ORDER
        assert len(PIPELINE_ORDER) == 3

    def test_all_ordered_keys_in_pipelines(self):
        from platform_app.pages.batch_workflow import PIPELINE_ORDER, PIPELINES
        for key in PIPELINE_ORDER:
            assert key in PIPELINES

# After (V2.0 core module tests):
class TestModuleRegistry:
    def test_build_registry_returns_list(self):
        from platform_app.core.module_registry import build_registry
        result = build_registry()
        assert isinstance(result, list)
        assert len(result) > 50  # ARS(8) + ICS(44) + TXN(31) + V4(12)

    def test_product_enum_values(self):
        from platform_app.core.module_registry import Product
        assert Product.ARS == "ars"
        # ... 5 more tests

class TestRunLogger:
    # 5 tests: run ID format, file hashing, log/load roundtrip

class TestTemplates:
    # 5 tests: builtins, save/load YAML roundtrip, delete protection

class TestSessionManager:
    # 4 tests: workspace properties, file auto-detection, folder discovery
```

New test count: 4 removed, 21 added = net +17 tests (39 -> 39 in file, but higher value coverage).

## Why This Works

1. **Root cause**: V1 `batch_workflow.py` exported `PIPELINE_ORDER = ["ars", "txn", "ics"]` and `PIPELINES = {...}` as module-level dicts. V2.0 replaced this with `core/module_registry.py` (unified `ModuleInfo` registry with `Product` enum) and the batch page uses checkboxes directly instead of a static pipeline dict. The old constants simply don't exist anymore.

2. **Why replace instead of adapt**: The V1 constants tested an architectural pattern (static pipeline dict) that no longer represents how the system works. Testing removed code provides zero value. The V2.0 core modules (`module_registry`, `run_logger`, `templates`, `session_manager`) are the new testable surface area.

3. **Underlying issue**: When a major rewrite replaces module-level exports, tests importing those exports break at import time (not assertion time), making the failure obvious but requiring a test migration strategy.

## Prevention

- When rewriting a module, search for test imports of that module's exports: `grep -r "from platform_app.pages.batch_workflow import" tests/`
- Update tests in the same PR as the rewrite -- never leave stale test imports on main
- Prefer testing core modules (pure logic, no Streamlit dependency) over page modules (which mix logic with UI rendering)
- Use `from __future__ import annotations` in test files so type-only imports don't cause failures

## Related Issues

No related issues documented yet.
