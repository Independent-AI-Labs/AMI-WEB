# AUDIT REPORT

**File**: `backend/facade/media/video.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:05:20
**Execution Time**: 14.24s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66 violation patterns and additional common violations.

## Analysis

Examining exception handlers:
- Line 95: `with contextlib.suppress(asyncio.CancelledError)` - **VIOLATION #19**
- Line 172-178: Exception handler with logging - **VIOLATION #39**
- Line 172: Bare `except Exception` - overly broad

Examining cleanup:
- Line 99-100: Writer cleanup in stop_recording - proper
- Line 180-185: Finally block cleanup - proper

Examining return statements:
- Line 149: Returns None if session not found - **VIOLATION #2** (documented behavior pattern but missing explicit documentation)

Examining defaults and validation:
- Line 155: RuntimeError for missing driver - proper
- Line 184: Cleanup in finally - proper

Examining type conversions:
- Line 53-54: `int(fps)`, `str(codec)` - **VIOLATION #81** (uncaught type conversion)

Examining loops:
- No continue/skip on exception patterns

Examining security:
- No SQL injection patterns
- No authentication issues
- No sensitive data issues

Examining stubs:
- No stub implementations

Examining suppression markers:
- No lint suppression markers

## Key Violations Found

1. **Line 95**: `contextlib.suppress(asyncio.CancelledError)` - Violation #19 (Exception Suppression via contextlib.suppress)
2. **Line 172-178**: Exception caught, logged with `logger.error()`, but not re-raised - Violation #39 (Exception → logger.error() Without Raise)
3. **Line 149**: `get_session()` returns None if not found without documented behavior - Violation #34 (Resource Not Found → Sentinel Return) - missing docstring clarification
4. **Line 53-54**: `int(fps)`, `str(codec)` - Violation #81 (Uncaught Type Conversion)

FAIL: Line 95: Exception Suppression via contextlib.suppress; Line 172-178: Exception → logger.error() Without Raise; Line 149: Resource Not Found → Sentinel Return (undocumented); Line 53-54: Uncaught Type Conversion
 (severity: CRITICAL)
