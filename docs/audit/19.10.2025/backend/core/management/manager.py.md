# AUDIT REPORT

**File**: `backend/core/management/manager.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:58:04
**Execution Time**: 7.81s

---

## Violations (1)

- Line 0: FAIL: Line 4: contextlib.suppress usage (Pattern #19); Line 14-34: lint suppression markers (# noqa) (Pattern #11); Line 102: exception suppressed in finally block via suppress (Pattern #60); Line 112: exception suppressed via suppress (Pattern #19); Line 133: exception suppressed via suppress (Pattern #19); Line 154: exception → None return (Pattern #43); Line 191-194: exception → None return (Pattern #43); Line 212: exception → False return (Pattern #22); Line 232: exception suppressed via suppress (Pattern #19); Line 246: exception suppressed via suppress (Pattern #19); Line 269: exception → None return (Pattern #43); Line 286: exception suppressed via suppress (Pattern #19); Line 316: exception → None return after cleanup (Pattern #43); Line 344: exception → None return (Pattern #43); Line 372: exception → False return (Pattern #22); Line 388: exception → False return (Pattern #22)
 (severity: CRITICAL)
