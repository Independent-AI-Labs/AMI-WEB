# AUDIT REPORT

**File**: `backend/models/browser_properties.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:55:16
**Execution Time**: 11.75s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66+ violation patterns with zero tolerance.

Reading through the entire file systematically:

**Lines 11-12**: Import statements with `# noqa: E402` - This is **Pattern #11: Lint/Type/Coverage Suppression Markers**

**Line 257-260**: Exception handling in `_load_user_agents_config()`:
```python
def _load_user_agents_config() -> dict[str, Any]:
    """Load user agents configuration from JSON file."""
    config_path = MODULE_ROOT / "config" / "user_agents.json"
    if config_path.exists():
        with config_path.open() as f:
            result: dict[str, Any] = json.load(f)
            return result
    return {"presets": {}, "device_emulation": {}}
```

This function has:
- **Pattern #50: Uncaught JSON Parsing** - `json.load(f)` with no try/except wrapper (line 259)
- **Pattern #34: Resource Not Found → Sentinel Return** - Returns empty dict when file doesn't exist instead of raising exception (line 260)

**Line 263-320**: The `get_preset_properties()` function uses multiple `if` statements with `.get()` calls that have hardcoded defaults, which is **Pattern #58: Implicit Default via Truthiness Operator** and **Pattern #62: Implicit Defaults in Optional Fields**

FAIL: Line 11: Lint suppression marker (# noqa: E402); Line 12: Lint suppression marker (# noqa: E402); Line 259: Uncaught JSON parsing without try/except wrapper; Line 260: Resource not found returns sentinel value {"presets": {}, "device_emulation": {}} instead of raising exception
 (severity: CRITICAL)
