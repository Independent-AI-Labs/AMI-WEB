# AUDIT REPORT

**File**: `backend/mcp/chrome/tools/extraction_tools.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:00:38
**Execution Time**: 11.88s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66+ violation patterns systematically.

**ANALYSIS:**

Checking all exception handlers:
- Line 83: `except ChunkComputationError as exc: return BrowserResponse(success=False, error=str(exc))` - **VIOLATION #27** (Exception → Response Object)
- Line 124: `except Exception: exists = False` - **VIOLATION #22** (Exception → False Return)
- No other try/except blocks present

Checking for uncaught exceptions:
- Line 112: `instance.driver.find_element(By.CSS_SELECTOR, selector)` - No exception handling (used in try/except at line 119-124)
- Line 145: `wait.until(EC.visibility_of_element_located(...))` - **VIOLATION #25** (Missing Exception Handling)
- Line 147: `wait.until(EC.presence_of_element_located(...))` - **VIOLATION #25** (Missing Exception Handling)
- Line 159: `instance.driver.get_cookies()` - **VIOLATION #25** (Missing Exception Handling)
- Line 195: `await extractor.get_element_html(selector)` - **VIOLATION #25** (Missing Exception Handling)
- Line 205: `await extractor.get_html_with_depth_limit(...)` - **VIOLATION #25** (Missing Exception Handling)

Checking for lint suppression markers:
- Line 3: `# noqa: N812` - **VIOLATION #11** (Lint Suppression Marker)

Checking for missing validation:
- All functions accept `instance_id` parameters but validation is delegated to `manager.get_instance_or_current()`

Checking attribute access patterns:
- No violations found

Checking SQL injection patterns:
- No SQL code present

Checking security patterns:
- No authentication/authorization code present

**VERDICT:**

```
FAIL: Line 3: Lint suppression marker (# noqa: N812); Line 83: Exception converted to response object without propagation; Line 124: Exception suppressed via False return; Line 145: Missing exception handling for WebDriverWait.until(); Line 147: Missing exception handling for WebDriverWait.until(); Line 159: Missing exception handling for get_cookies(); Line 195: Missing exception handling for get_element_html(); Line 205: Missing exception handling for get_html_with_depth_limit()
```
 (severity: CRITICAL)
