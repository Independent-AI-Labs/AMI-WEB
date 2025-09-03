# CRITICAL MODULE FIX INSTRUCTIONS

## YOUR MISSION:
Fix ALL issues in BROWSER module and push with ALL checks passing. NO CHEATING.

---

### STEP 1: GO TO MODULE
```bash
cd browser
pwd
```

### STEP 2: FIX MYPY.INI 
**THE MOST CRITICAL ISSUE: mypy.ini has `files = backend/` which ONLY checks backend folder**
```bash
# Read current mypy.ini
cat mypy.ini

# Edit mypy.ini and REMOVE the line "files = backend/" completely
# Also REMOVE "mypy_path = .." if present
# This makes mypy scan EVERYTHING
```

### STEP 3: RUN RUFF AND FIX ALL
```bash
# Auto-fix what's possible
../.venv/Scripts/ruff check . --fix

# Check what remains
../.venv/Scripts/ruff check .

# Fix remaining issues manually - NO SUPPRESSION
```

### STEP 4: RUN MYPY AND FIX ALL
```bash
# Run mypy on ENTIRE module
../.venv/Scripts/python -m mypy . --show-error-codes

# Fix EVERY type error - NO "type: ignore"
```

### STEP 5: RUN TESTS AND FIX ALL
```bash
# Run all tests
../.venv/Scripts/python -m pytest tests/ -v --tb=short

# Fix EVERY failing test - NO "pytest.skip"
```

### STEP 6: RUN PRE-COMMIT
```bash
# Run all pre-commit hooks
../.venv/Scripts/pre-commit run --all-files

# If anything fails, fix and re-run
```

### STEP 7: FINAL VERIFICATION
```bash
# ALL must pass:
../.venv/Scripts/ruff check .
../.venv/Scripts/python -m mypy . --show-error-codes  
../.venv/Scripts/python -m pytest tests/ -v
../.venv/Scripts/pre-commit run --all-files
```

### STEP 8: COMMIT AND PUSH
```bash
git add -A
git commit -m "fix: Complete BROWSER module code quality overhaul"
# NO --no-verify EVER

git push origin HEAD
# Use 600000ms (10 minute) timeout for push
```

---

## ABSOLUTE RULES:
1. **REMOVE `files = backend/` from mypy.ini** - MUST scan entire module
2. **REMOVE `mypy_path = ..` from mypy.ini** - Causes double detection
3. **ZERO ruff violations**
4. **ZERO mypy errors**  
5. **ALL tests pass**
6. **ALL pre-commit hooks pass**
7. **NO --no-verify**
8. **NO type: ignore**
9. **NO # noqa**
10. **NO pytest.skip**
11. **FIX ACTUAL PROBLEMS, not symptoms**

---

## IF YOU FAIL ANY CHECK:
**STOP. FIX IT. DON'T PROCEED.**

## SPECIFIC BROWSER MODULE ISSUES:
- Remove mypy_path = .. from mypy.ini (causes double module detection)
- Fix browser automation dependencies
- Ensure Playwright/Selenium types are correct