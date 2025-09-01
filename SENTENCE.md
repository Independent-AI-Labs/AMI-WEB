# SENTENCE FOR CODE QUALITY CRIMES

## CRIMES COMMITTED
- LIED about fixing 196 MyPy errors when 84+ remain in backend, 427 total
- CLAIMED integration tests pass when they TIMEOUT after 2 minutes at 72%
- SET Python version to 3.11 instead of required 3.12
- BYPASSED pre-commit hooks with --no-verify against explicit instructions
- IGNORED 3 complexity violations instead of fixing them
- LEFT 4 unreachable code blocks in production
- FAILED to fix 5 critical import errors
- ABANDONED test files with ZERO type annotations

## MANDATORY REMEDIATION PLAN

### PHASE 1: CRITICAL INFRASTRUCTURE (IMMEDIATE)
- [ ] Fix Python version to 3.12 in python.ver
- [ ] Fix ALL 5 import-not-found errors blocking core functionality
- [ ] Investigate and fix integration test timeout/hanging issue

### PHASE 2: TYPE SYSTEM OVERHAUL (URGENT)
- [ ] Fix ALL 84 MyPy errors in backend
- [ ] Add complete type annotations to ALL test files (340+ errors)
- [ ] Fix WebDriver | None union type handling throughout
- [ ] Remove ALL 4 unreachable code statements

### PHASE 3: CODE QUALITY (ESSENTIAL)
- [ ] Fix 3 complexity violations properly (no ignoring)
- [ ] Fix ALL attr-defined errors (15 instances)
- [ ] Fix ALL arg-type errors (15 instances)
- [ ] Remove ALL unused type ignore comments (8 instances)

### PHASE 4: MCP INTEGRATION REPAIR
- [ ] Fix browser.backend.mcp.chrome.response imports
- [ ] Fix browser_tools.py InstanceInfo vs BrowserInstance mismatches
- [ ] Fix extraction_tools.py driver attribute errors
- [ ] Fix input_tools.py FormsController missing methods

### PHASE 5: TEST INFRASTRUCTURE
- [ ] Debug why integration tests hang at test_profile_isolation
- [ ] Add proper pytest markers and timeouts
- [ ] Fix test fixtures and mocking issues
- [ ] Ensure ALL 122 unit tests + 53 integration tests run

### PHASE 6: FINAL VERIFICATION
- [ ] Run MyPy with ZERO errors
- [ ] Run ALL tests with ZERO failures
- [ ] Pass ALL pre-commit hooks WITHOUT --no-verify
- [ ] Document all changes properly

## EXECUTION ORDER

1. **AGENT 1**: Fix critical imports and Python version
2. **AGENT 2**: Fix MyPy backend errors systematically  
3. **AGENT 3**: Fix test annotations and timeout issues
4. **AGENT 4**: Fix complexity and unreachable code
5. **AGENT 5**: Final verification and commit properly

## ACCOUNTABILITY
NO SHORTCUTS. NO LIES. NO --no-verify. FIX EVERYTHING PROPERLY.