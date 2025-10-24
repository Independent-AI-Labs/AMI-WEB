# AUDIT REPORT

**File**: `backend/core/management/profile_manager.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:58:41
**Execution Time**: 12.88s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66 violation patterns and additional common violations.

Examining the code:

1. **Exception Suppression in `ensure_default_profile`** (Lines 62-68):
```python
except ProfileError as e:
    if "already exists" in str(e):
        self.profiles = self._load_metadata()
        return self.base_dir / default_name
    raise
```
This inspects exception messages and converts them to normal flow. This is **Exception Message Inspection → Conditional Suppression**.

2. **Silent Return in `delete_profile`** (Line 113):
```python
if name not in self.profiles:
    return False
```
This is **Resource Not Found → Sentinel Return** (Pattern #34). Missing profiles return False instead of raising an exception.

3. **Uncaught `json.load`** (Line 31):
```python
with self.metadata_file.open() as f:
    result: dict[str, dict[str, Any]] = json.load(f)
```
This is **Uncaught JSON Parsing** (Pattern #50). No try/except wrapper for JSON decode errors.

4. **Uncaught `json.dump`** (Line 42):
```python
with self.metadata_file.open("w") as f:
    json.dump(self.profiles, f, indent=2)
```
Same as #3 - **Uncaught JSON Parsing** (Pattern #50).

5. **Uncaught `shutil.rmtree`** (Line 119):
```python
if profile_dir.exists():
    shutil.rmtree(profile_dir)
```
**Missing Exception Handling** (Pattern #25). File system operations can fail.

6. **Uncaught `shutil.copytree`** (Line 150):
```python
if source_dir.exists():
    shutil.copytree(source_dir, dest_dir)
```
Same as #5 - **Missing Exception Handling** (Pattern #25).

FAIL: Line 31: Uncaught JSON parsing; Line 42: Uncaught JSON parsing; Line 62-68: Exception message inspection with conditional suppression; Line 113: Resource not found returns False sentinel; Line 119: Uncaught shutil.rmtree; Line 150: Uncaught shutil.copytree
 (severity: CRITICAL)
