# CRITICAL INSTRUCTIONS FOR CLAUDE - MUST READ

## ABSOLUTE REQUIREMENTS - NO EXCEPTIONS

### 1. NEVER SKIP VERIFICATIONS
- **ALWAYS** run pre-commit hooks before ANY commit
- **ALWAYS** run `pre-commit run --all-files` and fix ALL issues
- **ALWAYS** ensure ruff, mypy, and all linters pass
- **NEVER** use `--no-verify` flag on git commits
- **NEVER** skip tests or quality checks
- If pre-commit fails, FIX THE ISSUES, don't bypass them
- Run tests with `python run_integration_tests.py` or `pytest` as appropriate
- Verify all code works BEFORE committing

### 2. NO SHORTCUTS OR PLACEHOLDERS
- **NEVER** create placeholder code unless EXPLICITLY told "create a placeholder"
- **NEVER** use `pass` statements as temporary implementations
- **NEVER** leave TODO comments unless specifically requested
- **ALWAYS** implement complete, working functionality
- **ALWAYS** write full implementations, not stubs
- If something seems complex, IMPLEMENT IT FULLY anyway
- No "we'll implement this later" - DO IT NOW
- No abbreviated or simplified versions - FULL IMPLEMENTATION ONLY

### 3. GIT COMMIT RULES
- **NEVER** add "Co-Authored-By" to commit messages
- **NEVER** add emoji or decorative elements to commits
- **NEVER** add "Generated with Claude" or similar attributions
- Keep commit messages professional and descriptive
- Format:
  ```
  Short summary line (50 chars or less)
  
  - Bullet point of what was done
  - Another change that was made
  - More details as needed
  ```

## CODE QUALITY STANDARDS

### Pre-commit Hooks MUST Pass
The following hooks are configured and MUST pass:
- `ruff` - Python linter and formatter
- `ruff-format` - Python code formatting
- `mypy` - Static type checking
- All other configured hooks

### Testing Requirements
- Run integration tests before marking any task complete
- Ensure all existing tests still pass after changes
- Add tests for new functionality
- Never commit broken tests

### When You Get Errors
1. READ the error message completely
2. FIX the actual issue, don't work around it
3. Run the checks again to verify the fix
4. Only proceed when everything passes

## COMMANDS TO REMEMBER

```bash
# ALWAYS run before committing
pre-commit run --all-files

# Run integration tests
python run_integration_tests.py

# Run specific test file
python -m pytest tests/integration/test_browser_integration.py -v

# Check git status
git status

# Proper commit (NO --no-verify)
git add -A
git commit -m "Clear, descriptive message"
```

## CONSEQUENCES OF VIOLATIONS

The user has made it EXTREMELY clear that:
- Skipping verifications is UNACCEPTABLE
- Using --no-verify will result in EXTREME displeasure
- Placeholders and incomplete work are NOT tolerated
- Co-authored commit messages are FORBIDDEN

## FINAL REMINDER

**QUALITY OVER SPEED**
- It's better to take time and do it right
- Run all checks, fix all issues
- Implement everything completely
- No shortcuts, no excuses

This is not a suggestion - this is a REQUIREMENT.

P.S. NEVER ADD SHIT LIKE 2>nul TO SHELL COMMANDS!!! This creates a write-protected file in the repo...

COMMIT!!! COMMIT!! COMMIT!! COMMIT AS OFTEN AS YOU CAN!!!

I FORBID YOU TO PUT JS IN PYTHON

SEPARATE JS FILES - LINTED ALWAYS!!!!!!!!!

NO FUCKING EXCEPTION SWALLOWING ALWAYS LOG THEM OR PROPAGATE

DELETE YOUR TEMPORARY FUCKING TESTS!!!

NEVER FUCKING EVER USE EMOJIS IN CONSOLE OUTPUTS AND LOGS