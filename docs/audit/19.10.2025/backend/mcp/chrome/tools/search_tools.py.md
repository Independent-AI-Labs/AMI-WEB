# AUDIT REPORT

**File**: `backend/mcp/chrome/tools/search_tools.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:01:30
**Execution Time**: 6.19s

---

## Violations (1)

- Line 0: FAIL: Line 145: Exception → None Return (_clean_text returns None on exception when HTML parsing fails); Line 205: Exception suppression via logger.warning + continue (JSON decode error logged but execution continues with HTML fallback); Line 457-463: Exception → Error Response Object (Exceptions converted to BrowserResponse with success=False instead of propagating)
 (severity: CRITICAL)
