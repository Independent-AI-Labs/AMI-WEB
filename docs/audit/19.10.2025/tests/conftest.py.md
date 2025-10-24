# AUDIT REPORT

**File**: `tests/conftest.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:53:16
**Execution Time**: 21.31s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66 violation patterns and additional common violations.

**ANALYSIS:**

**CRITICAL VIOLATIONS:**

1. **Line 81-86 (Pattern #39: Exception → logger.error() Without Raise)**
```python
except Exception as exc:  # pragma: no cover - defensive
    logger.error(f"Failed to query Chrome version at {chrome_path}: {exc}")
    return False
```
Exception suppressed via logging, execution continues with False return.

2. **Line 104 (Pattern #43: Exception → None Return)**
```python
except Exception:
    return False
```
Generic Exception catch returning False sentinel.

3. **Line 119-123 (Pattern #17: Exception → Empty Collection Return + Pattern #39)**
```python
except Exception:
    with contextlib.suppress(Exception):
        await mgr.shutdown()
    return False
```
Exception converted to False, nested suppression in cleanup.

4. **Line 171-172 (Pattern #39: Exception → logger.error() Without Raise)**
```python
except Exception as e:
    logger.warning(f"Error stopping manager: {e}")
```
Exception suppressed via logging in critical cleanup.

5. **Line 193-194 (Pattern #17: Exception suppression in loop)**
```python
except Exception:
    logger.debug(f"Tab {handle} may already be closed")
```
Tab cleanup failures hidden.

6. **Line 209-210 (Pattern #39)**
```python
except Exception as e:
    logger.warning(f"Error cleaning up instance {instance.id}: {e}")
```
Cleanup failures suppressed.

7. **Line 298 (Pattern #39 + Pattern #60: Cleanup failure suppression)**
```python
except Exception as e:
    logger.warning(f"Error cleaning up tabs: {e}")
```

8. **Line 328-332 (Pattern #19: contextlib.suppress)**
```python
with contextlib.suppress(Exception):
    for test_dir in data_dir.glob("test_*"):
        if test_dir.is_dir():
            shutil.rmtree(test_dir, ignore_errors=True)
```
File operations suppressed, failures hidden.

9. **Line 341-343 (Pattern #17 + Pattern #19)**
```python
except (ValueError, AttributeError, RuntimeError):
    # Logger or stderr might be closed during cleanup
    pass
```
Multiple exception types suppressed.

10. **Line 365 (Pattern #19: contextlib.suppress in critical path)**
```python
with contextlib.suppress(Exception):
    logger.remove()
```

**MEDIUM VIOLATIONS:**

11. **Line 23 (Pattern #62: Implicit Defaults)**
```python
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"
```
Environment variable with implicit default.

12. **Line 90 (Pattern #64: Dictionary .get() Silent None Return)**
```python
driver_path = _cfg.get("backend.browser.chromedriver_path")
```

13. **Line 222 (Pattern #59: TODO/Production Comment)**
Function scope comment implies production concerns: "NEVER use session scope!"

**FAIL: Line 81-86: Exception → logger.error() Without Raise (Pattern #39); Line 104: Exception → False Return (Pattern #43); Line 119-123: Exception → False + nested contextlib.suppress (Patterns #17, #19); Line 171-172: Exception → logger.warning() Without Raise (Pattern #39); Line 193-194: Exception suppression in loop (Pattern #17); Line 209-210: Exception → logger.warning() Without Raise (Pattern #39); Line 298: Exception → logger.warning() Without Raise (Pattern #39); Line 328-332: contextlib.suppress with file operations (Pattern #19); Line 341-343: Multiple exception types suppressed with pass (Pattern #17); Line 365: contextlib.suppress in cleanup (Pattern #19); Line 23: Environment variable with implicit default (Pattern #62); Line 90: Dictionary .get() Silent None Return (Pattern #64)**
 (severity: CRITICAL)
