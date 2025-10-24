# AUDIT REPORT

**File**: `tests/unit/test_antidetection.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:08:55
**Execution Time**: 9.64s

---

## Violations (1)

- Line 0: I'll analyze this test code against all 66 violation patterns with zero tolerance.

```
FAIL: Line 38: Exception → False Return (test_scripts_exist uses assert which masks FileNotFoundError as test failure); Line 48: Exception → False Return (test_extension_files_exist uses assert which masks FileNotFoundError as test failure); Line 58: Missing Exception Handling (json.load without try/except wrapper); Line 82: Missing Exception Handling (json.load without try/except wrapper); Line 104: Missing Exception Handling (file read without try/except wrapper); Line 125: Missing Exception Handling (file read without try/except wrapper); Line 138: Missing Exception Handling (file read without try/except wrapper); Line 153: Missing Exception Handling (file read without try/except wrapper); Line 179: Missing Exception Handling (file read without try/except wrapper); Line 191: Missing Exception Handling (driver.get without try/except wrapper); Line 194: Missing Exception Handling (file open without try/except wrapper); Line 198: Missing Exception Handling (driver.execute_script without try/except wrapper); Line 201: Missing Exception Handling (driver.execute_script without try/except wrapper); Line 221: Missing Exception Handling (driver.get without try/except wrapper); Line 224: Missing Exception Handling (file open without try/except wrapper); Line 228: Missing Exception Handling (driver.execute_script without try/except wrapper); Line 231: Missing Exception Handling (driver.execute_script without try/except wrapper)
```
 (severity: CRITICAL)
