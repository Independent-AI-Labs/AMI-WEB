# CONSOLIDATED AUDIT PATTERNS

**Last Updated**: 2025-10-19 15:17:45

---

## Violation Patterns

### 1. Exception → False Return
- **Severity**: CRITICAL
- **Pattern**: `try: operation(); except: return False`
- **Impact**: Error conditions masked as boolean failures, preventing proper error handling

### 2. Subprocess Exit Code Ignored
- **Severity**: CRITICAL
- **Pattern**: `subprocess.run(..., check=False)` without checking return value
- **Impact**: Silent command failures, uncaught errors propagate

### 3. Exit Code → False Return
- **Severity**: CRITICAL
- **Pattern**: `if result.returncode != 0: return False`
- **Impact**: Process failures masked as boolean, loses error context

### 4. Warning + Sentinel Return
- **Severity**: HIGH
- **Pattern**: `logger.warning(...); return None`
- **Impact**: Missing resources or invalid state treated as optional, late failures

### 5. Warning + Early Return
- **Severity**: HIGH
- **Pattern**: `logger.warning(...); return`
- **Impact**: Required operations skipped silently, incomplete setup

### 6. Warning + Continue in Loop
- **Severity**: HIGH
- **Pattern**: `if error: logger.warning(...); continue`
- **Impact**: Failures in batch operations ignored, partial results

### 7. Lint Suppression Markers
- **Severity**: MEDIUM
- **Pattern**: `# noqa`, `# type: ignore`, `# pylint: disable`
- **Impact**: Code quality issues hidden, technical debt accumulates

### 8. Exception → None Return
- **Severity**: HIGH
- **Pattern**: `try: operation(); except: return None`
- **Impact**: Silent failures without logging, invalid state propagated

### 9. Exception → Ellipsis Pass
- **Severity**: CRITICAL
- **Pattern**: `try: operation(); except: ...`
- **Impact**: Explicit exception suppression, all errors silenced

### 10. Exception → Logger Only
- **Severity**: HIGH
- **Pattern**: `try: operation(); except Exception as e: logger.error(e)`
- **Impact**: Errors logged but not propagated, execution continues incorrectly

### 11. Context Manager Suppression
- **Severity**: MEDIUM
- **Pattern**: `with contextlib.suppress(Exception): operation()`
- **Impact**: Exceptions silenced, acceptable only for cleanup operations

### 12. Nested Exception Suppression
- **Severity**: CRITICAL
- **Pattern**: `try: op(); except: with contextlib.suppress(Exception): cleanup()`
- **Impact**: Layered error suppression, failures in exception handlers hidden

### 13. Implicit Environment Defaults
- **Severity**: MEDIUM
- **Pattern**: `os.environ.get("VAR", "default_value")`
- **Impact**: Undocumented defaults, configuration behavior unclear

### 14. Dictionary Silent None Return
- **Severity**: MEDIUM
- **Pattern**: `value = dict.get("key")` without default or None check
- **Impact**: Silent None propagation, late AttributeError failures

### 15. Continue Without Logging
- **Severity**: HIGH
- **Pattern**: `if not value: continue` without logging
- **Impact**: Silent skips in iteration, no visibility into failures

### 16. Missing Input Validation
- **Severity**: CRITICAL
- **Pattern**: `value = mapping.get(input, default)` without validating input
- **Impact**: Invalid inputs silently use default, no exception for bad values

### 17. Missing Exception Handling
- **Severity**: CRITICAL
- **Pattern**: `result = func_that_raises()` without try/except wrapper
- **Impact**: Uncaught exceptions propagate unexpectedly, crash execution

### 18. Validation Method → Boolean Instead of Exception
- **Severity**: HIGH
- **Pattern**: `def is_valid(): try: validate(); return True; except: return False`
- **Impact**: Validation failures return False instead of raising, prevents proper error handling

### 19. Exception → Original Input Return
- **Severity**: HIGH
- **Pattern**: `try: parsed = parse(input); except: return input`
- **Impact**: Parse failures return raw unprocessed data, invalid data treated as valid

### 20. Exception → Default Instance Return
- **Severity**: HIGH
- **Pattern**: `try: operation(); except: return ClassName()`
- **Impact**: Errors masked by returning empty instance, caller cannot distinguish failure from success

### 21. Implicit Model Field Defaults
- **Severity**: CRITICAL
- **Pattern**: `field: Optional[T] = None` without explicit documentation
- **Impact**: Undocumented None defaults in data models, unclear API contracts

### 22. Resource Not Found → Sentinel Return
- **Severity**: HIGH
- **Pattern**: `if not resource.exists(): return {}`
- **Impact**: Missing files or resources return default values instead of raising exception, silent failures

### 23. Retry Logic Masking Failures
- **Severity**: HIGH
- **Pattern**: `for attempt in range(retries): try: operation(); except: logger.warning(...); sleep(delay)`
- **Impact**: Underlying failures hidden by retry loops, delayed error detection

### 24. Cleanup Failure Suppression
- **Severity**: MEDIUM
- **Pattern**: `try: resource.close(); except Exception as e: logger.warning(...)`
- **Impact**: Resource cleanup failures suppressed, potential resource leaks

### 25. Implicit Defaults via Truthiness
- **Severity**: MEDIUM
- **Pattern**: `if not value: initialize()` treating empty values as missing
- **Impact**: Empty strings, zero values, empty collections treated as uninitialized, incorrect behavior

### 26. File Operations with Errors Ignored
- **Severity**: HIGH
- **Pattern**: `shutil.rmtree(path, ignore_errors=True)`
- **Impact**: File deletion failures silently ignored, incomplete cleanup

### 27. Function Parameter Defaults Masking Configuration
- **Severity**: CRITICAL
- **Pattern**: `def get_config(profile: str = "default")` without validation
- **Impact**: Missing configuration values silently use defaults, invalid values not rejected

### 28. Exception → Debug Logger Only
- **Severity**: HIGH
- **Pattern**: `try: operation(); except Exception as e: logger.debug(e)`
- **Impact**: Errors logged at debug level without re-raising, failures invisible in production

### 29. Uncaught JSON/Data Parsing
- **Severity**: CRITICAL
- **Pattern**: `data = json.load(f)` or `yaml.load(f)` without try/except wrapper
- **Impact**: Malformed data files cause uncaught exceptions, crash execution

### 30. Exception → Warning Logger Only
- **Severity**: HIGH
- **Pattern**: `try: operation(); except Exception as e: logger.warning(e)`
- **Impact**: Errors logged at warning level without re-raising, failures silently continue

### 31. Exception → Numeric Sentinel Return
- **Severity**: HIGH
- **Pattern**: `try: operation(); except: return 0`
- **Impact**: Failures masked as zero value, caller cannot distinguish error from legitimate zero result

### 32. Stub/No-Op Implementation
- **Severity**: MEDIUM
- **Pattern**: `def method(self): logger.debug(...); return` or `def method(self): pass`
- **Impact**: Required functionality not implemented, methods exist but perform no action

### 33. Exception Suppression in Finally Block
- **Severity**: CRITICAL
- **Pattern**: `finally: with contextlib.suppress(Exception): cleanup()`
- **Impact**: Cleanup exceptions silenced in finally blocks, resource release failures hidden

### 34. Exception Message Inspection → Conditional Suppression
- **Severity**: CRITICAL
- **Pattern**: `except Error as e: if "text" in str(e): handle(); else: raise`
- **Impact**: Exception handling based on string inspection, brittle error handling, violations of exception hierarchies

### 35. Exception → Response Object with Error Status
- **Severity**: CRITICAL
- **Pattern**: `try: operation(); except: return ResponseObject(success=False, error=str(e))`
- **Impact**: Exceptions converted to error response objects instead of propagating, breaks exception handling chain

### 36. Exception Instance Created But Never Raised
- **Severity**: MEDIUM
- **Pattern**: `Exception("message")` created for inspection/checking without raising
- **Impact**: Exception instantiation overhead without exception behavior, unclear error handling logic

### 37. Exception Type Conversion Without Context
- **Severity**: CRITICAL
- **Pattern**: `except Exception as e: raise CustomError(f"message: {e}") from e`
- **Impact**: Original exception type lost, wrapped in custom exception, breaks type-specific exception handling

### 38. None/Invalid → Type-Appropriate Sentinel Return
- **Severity**: HIGH
- **Pattern**: `return str(x) if x is not None else ""` or `return x if isinstance(x, list) else []`
- **Impact**: Invalid values converted to type-appropriate sentinels, failures masked by default values

### 39. Exception → Empty Collection via 'or' Operator
- **Severity**: HIGH
- **Pattern**: `return operation() or []` or `return func() or {}`
- **Impact**: Falsy results (None, empty) implicitly converted to empty collection, masks failures

### 40. Missing Resource Check → Sentinel in Lambda
- **Severity**: HIGH
- **Pattern**: `lambda: self.resource.method() if self.resource else None`
- **Impact**: Missing resources return sentinel values in lambdas, errors not raised at call site

### 41. SQL Injection via String Formatting
- **Severity**: CRITICAL
- **Pattern**: `f"SELECT * FROM table WHERE field = '{user_input}'"` or similar f-string/format SQL construction
- **Impact**: Unsanitized user input in SQL queries, database compromise, data exfiltration

### 42. Syntax Errors and Typos
- **Severity**: CRITICAL
- **Pattern**: `function(x | y)` instead of `function(x, y)` or similar operator/punctuation mistakes
- **Impact**: Code does not execute, runtime errors, broken functionality

### 43. Uncaught Type Conversion
- **Severity**: HIGH
- **Pattern**: `int(value)`, `str(value)`, `float(value)` without try/except wrapper
- **Impact**: Invalid input causes uncaught ValueError/TypeError, crash execution

### 44. Exception → Logger + Empty Collection Return
- **Severity**: CRITICAL
- **Pattern**: `try: operation(); except Exception as e: logger.error(e); return []`
- **Impact**: Errors logged but masked as empty collection, caller cannot distinguish failure from valid empty result

### 45. Dictionary .get() with Explicit Sentinel Default
- **Severity**: HIGH
- **Pattern**: `dict.get("key", "")` or `dict.get("key", [])` or similar explicit default
- **Impact**: Missing keys masked as empty values instead of raising KeyError, invalid state propagated

### 46. Unvalidated Array/List Indexing
- **Severity**: CRITICAL
- **Pattern**: `collection[0]` or `items[index]` without bounds checking or exception handling
- **Impact**: IndexError crashes on empty collections or invalid indices, uncaught failures

### 47. Finally Block Unconditional Cleanup
- **Severity**: CRITICAL
- **Pattern**: `finally: await cleanup()` or `finally: resource.close()` without exception suppression
- **Impact**: Cleanup failures in finally block mask original exceptions, test/operation failures hidden

### 48. Unvalidated Chained Dictionary/List Access
- **Severity**: CRITICAL
- **Pattern**: `data["key"][0]["nested"]` without validation or exception handling
- **Impact**: KeyError or IndexError on missing keys or empty lists, brittle data access

### 49. Partial Success Return (Count-Based)
- **Severity**: CRITICAL
- **Pattern**: `for item in items: try: process(item); count += 1; except: continue; return count`
- **Impact**: Individual failures in batch operations suppressed, partial results returned as success, no visibility into which items failed

### 50. Hardcoded Credentials/Secrets
- **Severity**: CRITICAL
- **Pattern**: `password = "hardcoded_password"` or `api_key = "secret123"` in production code
- **Impact**: Credentials exposed in source code, security compromise, credential leakage

### 51. Module/Script-Level Exception Suppression
- **Severity**: CRITICAL
- **Pattern**: `try: /* entire script/module */ catch(e) {}` wrapping all code execution
- **Impact**: All errors in entire module silenced, complete loss of error visibility, debugging impossible

### 52. Missing Security Attribute → Default Allow
- **Severity**: CRITICAL
- **Pattern**: `if (feature in coreFeatures) return true` or implicit default to enabled/allowed state
- **Impact**: Security features default to permissive state, missing configuration treated as allowed, security bypass
