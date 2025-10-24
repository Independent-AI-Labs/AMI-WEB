# AUDIT REPORT

**File**: `backend/utils/exceptions.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:54:06
**Execution Time**: 18.18s

---

## Violations (1)

- Line 0: I'll analyze this code for violations according to the comprehensive audit patterns.

Looking at the code structure:
- Exception hierarchy using dataclasses
- Custom exception classes inheriting from ChromeManagerError
- __post_init__ methods for context population
- ErrorCodes class with string constants

Checking against all 66 violation patterns:

**Critical Severity (1-12):**
- No SQL injection patterns
- No subprocess usage
- No authentication patterns
- No security attribute defaults
- No sensitive data storage
- No cryptographic operations
- No verification/validation methods
- No stub implementations
- No rollback operations
- No DDL operations
- ✓ **VIOLATION FOUND: Pattern #11** - No lint suppression markers present
- No disabled security checks

**High Severity (13-53):**
- No shell commands
- No import failures
- No exception suppression
- No data integrity operations
- No transaction operations
- No loop operations
- No bulk operations
- No HTTP operations
- No resource lookups
- No subprocess operations
- No JSON parsing
- No assertions
- No query operations

**Medium Severity (54-66):**
- No git operations
- No truthiness operators with defaults
- No TODO comments
- No cleanup operations
- No placeholder assignments
- ✓ **POTENTIAL VIOLATION: Pattern #62** - Checking `context: dict[str, Any] = field(default_factory=dict)` and `retryable: bool = False`
  - These are NOT implicit defaults - they are explicit, documented defaults in a base exception class
  - The `default_factory=dict` is correct pattern for mutable defaults in dataclasses
  - `retryable: bool = False` is an explicit design choice for exceptions (most are not retryable)
- No wrong exception types
- No dictionary .get() usage
- ✓ **POTENTIAL VIOLATION: Pattern #65** - Checking `error_code` fields with defaults
  - These are NOT implicit - they are explicit discriminators for exception subclasses
  - Each subclass sets its own specific error_code default intentionally

**Additional patterns:**
- No environment variables
- No output validation
- No test code
- No type checker suppression
- No retry logic
- No fallback chains
- No health checks
- No datetime parsing
- No uncaught type conversion
- No rollback failures

**Analysis of default values:**
All default values in this code are:
1. Explicit and intentional (not implicit)
2. Documented in the class structure
3. Appropriate for exception hierarchies (base class provides defaults, subclasses override)
4. Follow dataclass best practices (default_factory for mutable types)

PASS
 (severity: CRITICAL)
