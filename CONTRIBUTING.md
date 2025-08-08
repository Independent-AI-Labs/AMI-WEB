# Contributing to AMI-WEB

Thank you for your interest in contributing to AMI-WEB! This document outlines our development standards, requirements, and guidelines. **Please read this carefully before submitting any contributions.**

## 🚨 Critical Requirements

### Zero Tolerance Policies

We maintain strict quality standards. The following are **non-negotiable**:

1. **All pre-commit hooks MUST pass** - No exceptions
2. **No placeholder code** - Every implementation must be complete
3. **No skipping tests** - All tests must pass before commits
4. **No emojis in code** - Keep console outputs and logs professional
5. **No exception swallowing** - Always log or propagate exceptions

Violations of these policies will result in rejected pull requests.

## 📋 Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Security Guidelines](#security-guidelines)

## Development Environment Setup

### Prerequisites

1. **Python 3.12+** - Required for all development
2. **Chrome/Chromium** - Located at `./chromium-win/chrome.exe`
3. **ChromeDriver** - Located at `./chromedriver.exe`
4. **Git** with pre-commit hooks support

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/Independent-AI-Labs/AMI-WEB.git
cd AMI-WEB

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Chrome Configuration

**IMPORTANT**: Chrome and ChromeDriver paths are pre-configured:
- Chrome: `./chromium-win/chrome.exe`
- ChromeDriver: `./chromedriver.exe`
- Configuration: `chrome_manager/utils/config.py`

Never ask about Chrome locations - they're already configured.

## Code Standards

### Python Style Guide

We use `ruff` for linting and formatting with strict configuration:

- **Line length**: 160 characters maximum
- **Target version**: Python 3.12
- **Quote style**: Double quotes for strings
- **Import sorting**: Automatic via ruff
- **Complexity limits**:
  - Max cyclomatic complexity: 10
  - Max function arguments: 16
  - Max local variables: 64
  - Max statements: 96
  - Max branches: 16

### Required Linting Rules

Our `ruff.toml` enforces comprehensive checks including:
- Security scanning (bandit rules)
- Code quality (pylint rules)
- Performance optimizations
- Naming conventions (PEP8)
- Import organization
- Complexity analysis

### Type Hints

**All code must be fully type-hinted:**

```python
# ✅ Good
async def launch_browser(
    headless: bool = False,
    anti_detect: bool = True,
    profile: str | None = None
) -> BrowserInstance:
    """Launch a browser instance with specified options."""
    ...

# ❌ Bad - missing type hints
async def launch_browser(headless=False, anti_detect=True, profile=None):
    ...
```

### Error Handling

**Never swallow exceptions silently:**

```python
# ✅ Good - Log the error
try:
    await browser.navigate(url)
except Exception as e:
    logger.error(f"Navigation failed: {e}")
    raise

# ❌ Bad - Silent failure
try:
    await browser.navigate(url)
except:
    pass  # NEVER DO THIS
```

### JavaScript in Python Files

**JavaScript must be in separate files:**

```python
# ✅ Good
script_path = Path(__file__).parent / "scripts" / "antidetect.js"
with open(script_path) as f:
    script = f.read()

# ❌ Bad - Inline JavaScript
script = """
    // JavaScript code directly in Python
    window.navigator.webdriver = undefined;
"""
```

## Testing Requirements

### Test Coverage

- **Minimum coverage**: 80% for new code
- **Critical paths**: 100% coverage required
- **Anti-detection**: Must pass bot.sannysoft.com tests

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chrome_manager --cov-report=html

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/integration/test_antidetection.py -v

# Run pre-commit checks
pre-commit run --all-files
```

### Writing Tests

Every new feature requires:
1. Unit tests for individual components
2. Integration tests for end-to-end functionality
3. Anti-detection verification if browser-related

Example test structure:

```python
import pytest
from chrome_manager.core.instance import BrowserInstance

class TestBrowserFeature:
    """Test new browser feature."""
    
    @pytest.mark.asyncio
    async def test_feature_success(self, browser_instance):
        """Test successful feature execution."""
        # Arrange
        instance = browser_instance
        
        # Act
        result = await instance.new_feature()
        
        # Assert
        assert result.success is True
        assert result.data is not None
    
    @pytest.mark.asyncio
    async def test_feature_error_handling(self, browser_instance):
        """Test feature error handling."""
        # Test error conditions
        ...
```

### Test Fixtures

Use session-scoped fixtures for resource management:

```python
@pytest_asyncio.fixture(scope="session")
async def session_manager():
    """Shared ChromeManager for all tests."""
    manager = ChromeManager()
    await manager.start()
    yield manager
    await manager.shutdown()
```

## Commit Guidelines

### Pre-Commit Workflow

**MANDATORY before EVERY commit:**

```bash
# 1. Run pre-commit hooks
pre-commit run --all-files

# 2. Fix any issues (don't bypass)
# If ruff finds issues, fix them
# If mypy finds type errors, add type hints
# If tests fail, fix the code

# 3. Run tests
pytest

# 4. Only commit when everything passes
git add -A
git commit -m "Your message"
```

**NEVER use `--no-verify` flag!**

### Commit Message Format

```
Short summary (50 chars max)

- Detailed bullet point of changes
- Another change that was made
- Additional context if needed

Fixes #123  (if applicable)
```

**Rules:**
- No emojis in commit messages
- No "Co-Authored-By" attributions
- No "Generated with [Tool]" messages
- Keep it professional and descriptive

### Good Commit Examples

```
Fix WebDriver detection on second tabs

- Add CDP script injection with runImmediately parameter
- Update SimpleTabInjector to monitor new tabs
- Fix plugin count mismatch on window.open() tabs
- Pass all bot.sannysoft.com detection tests

Fixes #456
```

```
Refactor test fixtures for session-scoped browser pool

- Create single ChromeManager shared across tests
- Reduce Chrome instance spawning
- Improve test execution speed by 40%
- Fix user data directory conflicts
```

## Pull Request Process

### Before Submitting

1. **Ensure all tests pass**: `pytest`
2. **Run pre-commit**: `pre-commit run --all-files`
3. **Update documentation** if adding features
4. **Add tests** for new functionality
5. **Check anti-detection** still works

### PR Requirements

Your PR must:
- Have a clear title describing the change
- Include detailed description of what and why
- Reference any related issues
- Pass all CI checks
- Include tests for new features
- Update relevant documentation

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] Added new tests
- [ ] Anti-detection verified

## Checklist
- [ ] Pre-commit hooks pass
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No console.log/print statements left
```

## Project Structure

```
AMI-WEB/
├── chrome_manager/          # Core library
│   ├── core/               # Core components
│   │   ├── instance.py     # BrowserInstance class
│   │   ├── manager.py      # ChromeManager orchestration
│   │   ├── pool.py         # Instance pooling
│   │   └── antidetect.py   # Anti-detection logic
│   ├── facade/             # High-level controllers
│   │   ├── navigation.py   # Navigation operations
│   │   ├── input.py        # Input simulation
│   │   └── media.py        # Screenshots/media
│   ├── mcp/                # MCP server implementation
│   │   └── server.py       # WebSocket server
│   ├── scripts/            # JavaScript files (SEPARATE!)
│   │   └── complete-antidetect.js
│   └── utils/              # Utilities
│       ├── config.py       # Configuration
│       └── exceptions.py   # Custom exceptions
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Shared fixtures
├── mcp_stdio_server.py    # Stdio MCP server
├── ruff.toml              # Linting configuration
├── .pre-commit-config.yaml # Pre-commit hooks
└── requirements.txt       # Dependencies
```

## Security Guidelines

### Sensitive Data

- **Never commit credentials** - Use environment variables
- **No hardcoded URLs** with authentication
- **Sanitize logs** - Remove sensitive information
- **Use Config class** for all configuration

### Browser Security

- **Validate all input** before browser operations
- **Sanitize JavaScript** execution
- **Limit resource access** through proper scoping
- **Implement timeouts** for all operations

### Code Security

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

## Common Pitfalls to Avoid

### 1. Incomplete Implementations

```python
# ❌ Bad - Placeholder
async def new_feature():
    # TODO: Implement this
    pass

# ✅ Good - Complete implementation
async def new_feature():
    """Implement the new feature completely."""
    result = await perform_operation()
    validate_result(result)
    return process_result(result)
```

### 2. Ignoring Linter Warnings

```python
# ❌ Bad - Suppressing warnings
result = dangerous_operation()  # noqa: S106

# ✅ Good - Fix the issue
result = safe_operation()
```

### 3. Poor Error Messages

```python
# ❌ Bad - Generic error
raise Exception("Error occurred")

# ✅ Good - Descriptive error
raise BrowserError(
    f"Failed to navigate to {url}: "
    f"Status {response.status_code}, "
    f"Message: {response.text}"
)
```

### 4. Test Pollution

```python
# ❌ Bad - Creating new instances per test
async def test_feature():
    browser = BrowserInstance()
    await browser.launch()
    # ... test ...
    await browser.terminate()

# ✅ Good - Using fixtures
async def test_feature(browser_instance):
    # Use shared fixture
    result = await browser_instance.feature()
    assert result.success
```

## Getting Help

### Resources

- **Documentation**: Read existing code and docstrings
- **Tests**: Look at test files for usage examples
- **Issues**: Check GitHub issues for similar problems
- **Discussions**: Open a discussion for design questions

### Contact

- **GitHub Issues**: For bugs and feature requests
- **Pull Requests**: For code contributions
- **Discussions**: For questions and ideas

## Recognition

Contributors who consistently follow these guidelines and make quality contributions will be:
- Added to the contributors list
- Mentioned in release notes
- Given collaborator access for regular contributors

## Final Notes

**Remember:**
- Quality over speed - Take time to do it right
- Test everything - Never assume it works
- Document your code - Help future contributors
- Follow the standards - They exist for good reasons

**Your contributions make AMI-WEB better for everyone. Thank you for maintaining our high standards!**

---

*This document is enforced by automated checks. Attempting to bypass these checks will result in rejected contributions.*