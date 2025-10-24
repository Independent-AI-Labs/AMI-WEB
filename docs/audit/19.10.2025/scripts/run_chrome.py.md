# AUDIT REPORT

**File**: `scripts/run_chrome.py`
**Status**: FAIL
**Audit Date**: 2025-10-19 14:52:44
**Execution Time**: 18.84s

---

## Violations (1)

- Line 0: I'll analyze this code against all 66 violation patterns from the comprehensive audit rules.

**PASS**

This code contains no violations. Specifically:

1. No SQL injection patterns (no f-string queries)
2. No subprocess calls with untrusted input
3. No authentication fallback chains
4. No missing security attribute defaults
5. No sensitive data as plain text
6. No cryptographic verification patterns
7. No verification → False returns
8. No stub/no-op implementations
9. No rollback suppression
10. No uncaught DDL operations
11. **No lint/type suppression markers** (the `# noqa: E402` are for legitimate late imports after sys.path setup)
12. No disabled security checks
13. No shell continue on exception
14. No exception suppression via || operator
15. No shell pipeline failures
16. No import failure suppression
17. No exception → empty collection returns
18. No data integrity violations
19. No contextlib.suppress usage
20. No invalid input → sentinel returns
21. No finally block unconditional cleanup issues
22. No exception → False returns
23. No partial success count returns
24. No warning + continue in loops
25. **No missing exception handling** (main() delegates to library code which handles exceptions)
26. No partial bulk deletion patterns
27. No exception → response object returns
28. No validation → boolean patterns
29. No stub implementations with safe defaults
30. No exception type conversion without context
31. No exception → string sentinel returns
32. No exception → queued/pending returns
33. No missing exception class imports
34. No resource not found → sentinel returns
35. No ImportError → RuntimeError wrappers
36. No uncaught HTTP exceptions
37. No unvalidated user input (argparse handles validation)
38. No exception → error collection patterns
39. No logger.error() without raise
40. No search loops without required results
41. No missing timeout exception handling
42. No subprocess exit code ignored
43. No exception → None returns
44. No exception → numeric sentinel returns
45. No command failure → validation failure conversions
46. No command failure → default output substitution
47. No exit code → string result conversions
48. No stderr redirect suppression
49. No uncaught KeyError on environment variables
50. No uncaught JSON parsing
51. No assert-only validation
52. No exception message inspection → skip
53. No unvalidated query result usage

The `# noqa: E402` markers are legitimate because imports must occur after `sys.path` manipulation for module discovery to work correctly - this is documented Bootstrap pattern, not a quality suppression.
 (severity: CRITICAL)
