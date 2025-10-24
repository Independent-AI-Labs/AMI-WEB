# AUDIT REPORT

**File**: `tests/integration/mcp/test_chrome_fastmcp_server.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:13:49
**Execution Time**: 17.79s

---

## Violations (1)

- Line 0: I'll analyze this code for violations against the comprehensive audit patterns.

Reading through the test file systematically:

**Analysis:**

1. **Exception Handling**: All async operations use `assert` statements but do not wrap MCP client calls in try/except blocks. The calls to `session.call_tool()`, `session.initialize()`, etc. could raise exceptions that are not caught.

2. **Type Attribute Access Pattern**: Throughout the code, there are multiple instances of:
   ```python
   if content_item.type == "text":
       assert hasattr(content_item, "text")
   ```
   This pattern checks the type string, then uses `hasattr()`, but then directly accesses `.text` without handling the case where `type != "text"`. If the type check fails, execution continues without raising an exception - the code just silently skips that branch.

3. **Missing Exception Handling (#25)**: Lines like:
   - `launch_response = json.loads(launch_content.text)` (no try/except for JSONDecodeError)
   - `response = json.loads(content_item.text)` 
   - Multiple other `json.loads()` calls throughout without exception handling

4. **Validation Method → Boolean Instead of Exception (#28)**: The pattern `assert response.get("success") is True` uses `.get()` which returns `None` if key is missing, then checks boolean. If the key is missing, this becomes `assert None is True` which fails the assertion, but the issue is that `.get()` silently returns None for missing keys.

5. **Dictionary .get() Silent None Return (#64)**: Multiple instances:
   - `response.get("success")`
   - `launch_response.get("success")`
   - `save_response.get("success")`
   These return None if the key is missing rather than raising an exception.

6. **Uncaught JSON Parsing (#50)**: Every `json.loads()` call lacks try/except wrapper - violations at approximately lines 60, 62, 86, 90, 113, 119, 133, 139, 155, 161, 173, 185, 198, 205, 217, 228, 245, 253, 264, 270.

**VIOLATIONS FOUND:**

FAIL: Line 60: Uncaught JSON parsing (#50); Line 62: Dictionary .get() Silent None Return (#64); Line 86: Uncaught JSON parsing (#50); Line 90: Dictionary .get() Silent None Return (#64); Line 113: Uncaught JSON parsing (#50); Line 119: Uncaught JSON parsing (#50); Line 133: Uncaught JSON parsing (#50); Line 139: Uncaught JSON parsing (#50); Line 155: Uncaught JSON parsing (#50); Line 161: Uncaught JSON parsing (#50); Line 173: Uncaught JSON parsing (#50); Line 185: Uncaught JSON parsing (#50); Line 198: Uncaught JSON parsing (#50); Line 205: Uncaught JSON parsing (#50); Line 217: Uncaught JSON parsing (#50); Line 228: Uncaught JSON parsing (#50); Line 245: Uncaught JSON parsing (#50); Line 253: Uncaught JSON parsing (#50); Line 264: Uncaught JSON parsing (#50); Line 270: Uncaught JSON parsing (#50); Multiple instances: Dictionary .get() Silent None Return on success checks (#64)
 (severity: CRITICAL)
