# AUDIT REPORT

**File**: `tests/unit/test_search_tools.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:09:38
**Execution Time**: 16.39s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66+ violation patterns.

Examining the test file systematically:

1. **Exception handlers**: None present - all operations execute without try/except blocks
2. **Loops**: No loops present
3. **Default values**: SimpleNamespace, Config usage - checking for implicit defaults
4. **Return statements in except blocks**: None - no exception handling
5. **Retry logic**: None
6. **SQL injection**: None - no SQL operations
7. **Security attributes**: None - test file
8. **Lint/type suppression**: None visible
9. **Uncaught operations**: Multiple risky operations without exception handling

**Critical violations found**:

1. **Line 32-38** (`_start_test_server`): Missing exception handling for `runner.setup()`, `site.start()` - uncaught async operation failures
2. **Line 40-42**: Unsafe socket access - `sockets[0].getsockname()[1]` can raise IndexError or AttributeError if server startup fails (Pattern #25: Missing Exception Handling)
3. **Line 71** (`finally: await runner.cleanup()`): Cleanup in finally block without exception suppression - if cleanup fails, masks test exceptions (Pattern #21: Finally Block Unconditional Cleanup)
4. **Line 81**: Unvalidated dictionary access `response.result.get("results")` followed by `results[0]["url"]` - can raise KeyError/IndexError without validation (Patterns #53: Unvalidated Query Result Usage, #25: Missing Exception Handling)
5. **Line 109** (repeated at line 127): Same unsafe `finally: await runner.cleanup()` pattern
6. **Line 120-122**: Unvalidated dictionary/list access `results[0]["title"]`, `results[0]["url"]` without bounds checking

**Output**:

FAIL: Line 32-38: Missing exception handling for async server operations; Line 40-42: Uncaught IndexError/AttributeError on socket access; Line 71: Finally block cleanup without exception suppression masks test failures; Line 81: Unvalidated dictionary/list access can raise KeyError/IndexError; Line 109: Finally block cleanup without exception suppression; Line 120-122: Unvalidated array access without bounds checking
 (severity: CRITICAL)
