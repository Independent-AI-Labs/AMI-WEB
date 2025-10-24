# AUDIT REPORT

**File**: `backend/facade/navigation/extractor.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 15:03:12
**Execution Time**: 16.74s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66+ violation patterns with zero tolerance.

Examining the code systematically:

1. **Exception handlers** - Lines 24-26, 42-44, 53-55, 72-74, 100-102, 139-141, 151-153, 164-166, 184-186, 203-205, 217-219, 230-232:
   - All follow pattern: `except Exception as e: raise NavigationError(f"...: {e}") from e`
   - This is **Pattern #30: Exception Type Conversion Without Context**
   - VIOLATION: Original exception type lost, wrapped in NavigationError

2. **Sentinel returns** - Lines 26, 43, 54, 102, 141, 153:
   - Pattern: `return str(result) if result is not None else ""`
   - This is **Pattern #20: Invalid Input → Type-Appropriate Sentinel**
   - VIOLATION: None results converted to empty string sentinel

3. **Sentinel returns** - Lines 185, 205, 232:
   - Pattern: `return result if isinstance(result, list) else []`
   - Pattern: `return await self.execute_script(script) or []`
   - This is **Pattern #17: Exception → Empty Collection Return** (implicit via `or`)
   - VIOLATION: Invalid/None results converted to empty list sentinel

4. **Lambda with None check** - Lines 25, 133, 138:
   - Pattern: `lambda: str(self.driver.page_source) if self.driver else ""`
   - Pattern: `lambda: self.driver.execute_script(...) if self.driver else None`
   - This is **Pattern #20: Invalid Input → Type-Appropriate Sentinel**
   - VIOLATION: Missing driver returns sentinel values instead of raising exception

**FAIL: Line 24-26: Exception type conversion without context (wraps in NavigationError, loses original type); Line 26: None → empty string sentinel return; Line 25: Missing driver → empty string sentinel in lambda; Line 42-44: Exception type conversion without context; Line 43: None → empty string sentinel return; Line 53-55: Exception type conversion without context; Line 54: None → empty string sentinel return; Line 72-74: Exception type conversion without context; Line 100-102: Exception type conversion without context; Line 102: None → empty string sentinel return; Line 133: Missing driver → None sentinel in lambda; Line 138: Missing driver → None sentinel in lambda; Line 139-141: Exception type conversion without context; Line 141: None → empty string sentinel return; Line 151-153: Exception type conversion without context; Line 153: None → empty string sentinel return; Line 164-166: Exception type conversion without context; Line 184-186: Exception type conversion without context; Line 185: Non-list result → empty list sentinel; Line 203-205: Exception type conversion without context; Line 205: Non-list result → empty list sentinel; Line 217-219: Exception type conversion without context; Line 219: None → empty list via or operator; Line 230-232: Exception type conversion without context**
 (severity: CRITICAL)
