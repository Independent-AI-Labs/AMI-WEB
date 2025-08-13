# Contributing to AMI-WEB

This document outlines our development standards and requirements. **Read this before contributing.**

## 🚨 Zero Tolerance Policies

The following are **non-negotiable** and will result in rejected PRs:

1. **All pre-commit hooks MUST pass** - No exceptions
2. **No placeholder code** - Every implementation must be complete
3. **No skipping tests** - All tests must pass before commits
4. **No emojis in code** - Crashes Claude Code's shell
5. **No exception swallowing** - Always log or propagate exceptions
6. **Never use `--no-verify`** - Fix issues, don't bypass them

## Development Setup

### Prerequisites
- Python 3.12+
- Chrome/Chromium at `./chromium-win/chrome.exe`
- ChromeDriver at `./chromedriver.exe`
- Git with pre-commit support

### Quick Start
```bash
git clone https://github.com/Independent-AI-Labs/AMI-WEB.git
cd AMI-WEB

# Install uv for fast dependency management
pip install uv

# Create virtual environment with uv
uv venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Install dependencies (much faster with uv)
uv pip install -r requirements.txt -r requirements-test.txt

# Install pre-commit hooks
pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Code Standards

### Ruff Configuration
- Line length: 160 chars max
- Python 3.12 target
- Cyclomatic complexity: 10 max
- See `ruff.toml` for full rules

### Type Hints Required
```python
# ✅ Good
async def launch_browser(
    headless: bool = False,
    profile: str | None = None
) -> BrowserInstance:
    ...

# ❌ Bad
async def launch_browser(headless=False, profile=None):
    ...
```

### JavaScript Separation
```python
# ✅ Good - Separate file
script_path = Path(__file__).parent / "scripts" / "antidetect.js"
with open(script_path) as f:
    script = f.read()

# ❌ Bad - Inline JavaScript
script = """window.navigator.webdriver = undefined;"""
```

### Error Handling
```python
# ✅ Good - Log and propagate
try:
    await browser.navigate(url)
except Exception as e:
    logger.error(f"Navigation failed: {e}")
    raise

# ❌ Bad - Silent failure
try:
    await browser.navigate(url)
except:
    pass
```

## Testing

### Requirements
- 80% minimum coverage for new code
- 100% coverage for critical paths
- Must pass bot.sannysoft.com anti-detection

### Commands
```bash
# Using the test runner script (handles environment)
python scripts/run_tests.py                        # Run all tests
python scripts/run_tests.py --cov=backend          # With coverage
python scripts/run_tests.py tests/integration/test_antidetection.py -v  # Specific tests

# Pre-commit checks
pre-commit run --all-files                         # Run all checks
pre-commit run ruff --all-files                    # Just ruff linting
```

### Test Structure
```python
@pytest.mark.asyncio
async def test_feature(browser_instance):  # Use fixtures
    """Test with shared browser instance."""
    result = await browser_instance.new_feature()
    assert result.success is True
```

## Commit Process

### Pre-Commit Workflow
```bash
# 1. Run checks
pre-commit run --all-files

# 2. Fix ALL issues - don't bypass

# 3. Run tests
python scripts/run_tests.py

# 4. Commit only when everything passes
git add -A
git commit -m "Clear, descriptive message"
```

### Commit Message Format
```
Short summary (50 chars max)

- Bullet point of changes
- Another change made
- Additional context

Fixes #123
```

**No emojis, no attributions, no "Generated with" messages**

## Pull Request Checklist

### Before Submitting
- [ ] All tests pass
- [ ] Pre-commit hooks pass
- [ ] Documentation updated
- [ ] Anti-detection verified

### PR Template
```markdown
## Description
What and why

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change

## Testing
- [ ] Tests pass
- [ ] Tests added
- [ ] Anti-detection verified
```

## Security

### Never Commit
- Credentials or API keys
- Hardcoded auth URLs
- Unsanitized logs

### Always Use
- Environment variables for secrets
- Parameterized queries
- Input validation
- Timeouts on operations

```python
# ✅ Good - Parameterized
await browser.execute_script(
    "return document.querySelector(arguments[0]).textContent",
    selector
)

# ❌ Bad - String concatenation
await browser.execute_script(
    f"return document.querySelector('{selector}').textContent"
)
```

## Common Pitfalls

### Incomplete Implementation
```python
# ❌ Bad
async def feature():
    pass  # TODO

# ✅ Good
async def feature():
    result = await operation()
    validate(result)
    return process(result)
```

### Test Pollution
```python
# ❌ Bad - New instance per test
async def test():
    browser = BrowserInstance()
    await browser.launch()

# ✅ Good - Shared fixture
async def test(browser_instance):
    await browser_instance.action()
```

## Getting Help

- **Code Examples**: Check existing tests
- **Issues**: GitHub issues for bugs
- **Discussions**: GitHub discussions for design questions

---

**Quality over speed. Test everything. No shortcuts.**

*This document is enforced by automated checks.*