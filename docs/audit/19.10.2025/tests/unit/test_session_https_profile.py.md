# AUDIT REPORT

**File**: `tests/unit/test_session_https_profile.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:10:35
**Execution Time**: 16.88s

---

## Violations (1)

- Line 0: I need to analyze this test file for code quality violations according to the comprehensive audit patterns.

Let me examine the code systematically:

**Checking for all 66 violation patterns:**

1. **SQL Injection**: No SQL queries present ✓
2. **Subprocess fallbacks**: No subprocess calls ✓
3. **Auth downgrade**: No authentication logic ✓
4. **Missing security attributes**: No security checks ✓
5. **Sensitive data plain text**: No sensitive data storage ✓
6. **Crypto verification**: No cryptographic operations ✓
7. **Verification → False**: No verification methods ✓
8. **Stub implementations**: No stub methods ✓
9. **Rollback suppression**: No rollback logic ✓
10. **Uncaught DDL**: No database operations ✓
11. **Lint suppression markers**: No suppression comments ✓
12. **Disabled security**: No security checks ✓
13-53. **Exception handling patterns**: Examining all async functions...
54-66. **Other patterns**: Checking defaults, TODO comments, etc.

**Key observations:**

1. All `await session_manager.save_session()` calls are NOT wrapped in try/except blocks - **VIOLATION #25: Missing Exception Handling**
2. File I/O operations `session_file.open()` and `json.load(f)` are NOT wrapped in try/except - **VIOLATION #50: Uncaught JSON Parsing** and **VIOLATION #25: Missing Exception Handling**
3. Multiple assertions on `session_file.exists()` and dictionary access to `session_data` without exception handling

**Specific violations:**

- Lines 64-65, 92-94, 119-121, 139-141, 163-165, 186-188, 212-216: `json.load(f)` without try/except (Uncaught JSON Parsing)
- Lines 59, 84, 109, 129, 177, 203: `await session_manager.save_session()` without try/except (Missing Exception Handling)
- Lines 70-71, 98-99, 125-126, 145-146, 191-192, 221-224: Direct dictionary key access `session_data["profile"]`, `session_data["url"]`, `session_data["cookies"]` without validation (Unvalidated Query Result Usage)

FAIL: Line 59: Missing exception handling (save_session); Line 64: Uncaught JSON parsing; Line 70: Unvalidated dictionary access; Line 84: Missing exception handling (save_session); Line 92: Uncaught JSON parsing; Line 98: Unvalidated dictionary access; Line 109: Missing exception handling (save_session); Line 119: Uncaught JSON parsing; Line 125: Unvalidated dictionary access; Line 129: Missing exception handling (save_session); Line 139: Uncaught JSON parsing; Line 145: Unvalidated dictionary access; Line 163: Uncaught JSON parsing; Line 177: Missing exception handling (save_session); Line 186: Uncaught JSON parsing; Line 203: Missing exception handling (save_session); Line 212: Uncaught JSON parsing
 (severity: CRITICAL)
