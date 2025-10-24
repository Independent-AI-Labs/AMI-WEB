# AUDIT REPORT

**File**: `scripts/setup_chrome.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:52:54
**Execution Time**: 8.25s

---

## Violations (1)

- Line 0: FAIL: Line 101: Exception suppression via contextlib.suppress (cleanup only - borderline); Line 155: Exception suppression via contextlib.suppress (cleanup only - borderline); Line 169: Missing exception handling (_ensure_chromium_permissions can raise); Line 173: Exception → False (no exception raised); Line 244: Exception suppression via contextlib.suppress (cleanup only - borderline); Line 300: Exception → None return (no exception raised for invalid version output); Line 353: Exception → bare '...' (equivalent to 'pass', suppresses all exceptions); Line 430: Exception suppression via contextlib.suppress (cleanup only - borderline); Line 461: Exception → bare '...' (equivalent to 'pass', suppresses all exceptions); Line 476: Exception suppression via contextlib.suppress (cleanup only - borderline); Line 547: Uncaught subprocess exception (no try/except wrapper around subprocess.run in verify_installation); Line 552: Exception → logger.error without raise (prints error but continues execution instead of propagating exception)
 (severity: CRITICAL)
