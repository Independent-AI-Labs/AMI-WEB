# AUDIT REPORT

**File**: `backend/facade/input/keyboard.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:04:59
**Execution Time**: 8.17s

---

## Violations (1)

- Line 0: I need to analyze this code against the comprehensive violation patterns. Let me examine it systematically.

**Analysis:**

1. **Line 5: `from selenium.webdriver.support import expected_conditions as EC  # noqa: N812`**
   - Violation #11: Lint suppression marker (`# noqa`)
   - This suppresses naming convention check N812

2. **Line 194-196: Exception → None Return in `_find_element`**
   ```python
   except Exception as e:
       logger.warning(f"Element not found: {selector}: {e}")
       return None
   ```
   - Violation #43: Exception → None Return
   - The method catches all exceptions and returns None, hiding various failure modes (timeouts, stale elements, selector errors) as None
   - Caller cannot distinguish between "element not found" and other failures

**Output:**

FAIL: Line 5: Lint suppression marker (# noqa); Line 194-196: Exception → None Return
 (severity: CRITICAL)
