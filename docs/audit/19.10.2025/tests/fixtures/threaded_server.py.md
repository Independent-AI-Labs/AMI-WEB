# AUDIT REPORT

**File**: `tests/fixtures/threaded_server.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:11:40
**Execution Time**: 6.99s

---

## Violations (1)

- Line 0: FAIL: Line 63: Exception → logger.error() Without Raise (pragma: no cover suppresses coverage but exception still suppressed); Line 93: Cleanup/Disconnect Failure Suppression (pragma: no cover suppresses coverage but exception still suppressed); Line 105: Hardcoded password in credential validation (S105 marker acknowledges security issue); Line 31-35: Multiple fields have implicit None defaults without explicit validation; Line 57: Exception suppressed via logging only without raise in finally block
 (severity: CRITICAL)
