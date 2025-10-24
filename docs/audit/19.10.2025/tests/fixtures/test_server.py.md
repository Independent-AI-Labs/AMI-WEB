# AUDIT REPORT

**File**: `tests/fixtures/test_server.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:11:15
**Execution Time**: 7.38s

---

## Violations (1)

- Line 0: FAIL: Line 60: Exception → None Return (bare except suppressing all exceptions without raising); Line 93: Hardcoded test password in production code (S105 suppression marker hiding security issue); Line 93: Lint/Type/Coverage Suppression Markers (# noqa suppressing security warning)
 (severity: CRITICAL)
