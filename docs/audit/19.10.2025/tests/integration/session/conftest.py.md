# AUDIT REPORT

**File**: `tests/integration/session/conftest.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:14:42
**Execution Time**: 5.55s

---

## Violations (1)

- Line 0: FAIL: Line 12: Implicit default via environment variable with string conversion instead of explicit configuration; Line 16: Uncaught exception in async fixture initialization - no try/except wrapper around manager.initialize(); Line 23: Uncaught exception in async fixture teardown - no try/except wrapper around manager.shutdown(); Line 23: Cleanup/disconnect failure suppression - shutdown failure in teardown should be caught and logged
 (severity: CRITICAL)
