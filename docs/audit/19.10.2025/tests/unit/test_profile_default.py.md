# AUDIT REPORT

**File**: `tests/unit/test_profile_default.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:09:12
**Execution Time**: 15.38s

---

## Violations (1)

- Line 0: I'll analyze this code against the comprehensive violation patterns.

Reading the test file to check for all 66+ violation patterns systematically:

**Checking Critical Severity (1-12):**
- No SQL injection, subprocess calls, auth fallbacks, or sensitive data handling
- No cryptographic operations or verification functions
- No stub/no-op implementations
- No lint suppression markers (`# noqa`, `# type: ignore`, etc.)
- No disabled security checks

**Checking High Severity (13-53):**
- No shell operations
- No exception suppression via `contextlib.suppress`
- No exception → False/None/sentinel returns
- No missing exception handling around risky operations
- No exception → response object conversions
- No validation methods returning booleans instead of raising
- No stub implementations with safe defaults
- No exception type conversions
- No missing imports
- No uncaught operations (HTTP, JSON, etc.)
- No subprocess calls
- No assert-only validations

**Checking Medium Severity (54-66):**
- No git operations
- No exception → original input returns
- No implicit defaults via truthiness operators
- No TODO/production comment stubs
- No cleanup failure suppression
- No wrong exception types
- No dictionary `.get()` calls that could hide missing keys
- No hardcoded retry logic

**Checking Additional Common Violations:**
- No environment variable access
- No retry/fallback chains
- No health checks
- No datetime parsing
- No type conversions without proper error handling
- No uncaught operations

**Test-Specific Checks:**
- All `pytest.raises()` uses have proper assertions (none found - not using this pattern)
- No tests validating stub implementations
- All fixtures return appropriate test data
- No type checker suppression in configuration

**Code Quality:**
- Proper type hints on all functions
- Clear test names describing behavior
- Appropriate use of fixtures
- No exception handling at all (which is acceptable in unit tests)
- Tests verify expected behavior without masking failures

PASS
 (severity: CRITICAL)
