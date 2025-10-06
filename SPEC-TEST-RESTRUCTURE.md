# Browser Test Restructure Specification

**Version**: 1.0
**Date**: 2025-10-06
**Status**: Implementation in Progress

---

## Executive Summary

This specification defines the complete restructure of browser module tests to eliminate useless mocked tests, fix configuration issues, improve test isolation, and enable parallel execution.

**Current State**: 341 tests (229 unit, 114 integration), 7-8 minute runtime, Chrome segfaults, flaky tests
**Target State**: ~249 tests (137 unit, 114 integration), 3-5 minute runtime, no segfaults, no flaky tests

---

## Phase 1: Delete Useless Unit Tests

### Problem

92 unit tests (40% of all unit tests) mock the entire class being tested, then test that the mock behaves as mocked. These tests provide ZERO value and don't test any real code.

### Pattern Example

```python
# USELESS TEST - tests mock library, not ProfileManager:
@pytest.mark.asyncio
async def test_create_profile(self) -> None:
    with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
        manager = mock_manager_class()
        manager.create_profile = AsyncMock(side_effect=lambda name, _props: f"profile-{name}")

        profile_id = await manager.create_profile("test", {"userAgent": "Custom UA"})

        assert profile_id == "profile-test"  # Mock returns what we told it to return
        manager.create_profile.assert_called_once_with("test", {"userAgent": "Custom UA"})  # Mock was called
```

**Why USELESS**: No ProfileManager code executes. Only tests that `unittest.mock` works.

### Files to Delete

| File | Tests | Reason |
|------|-------|--------|
| tests/unit/test_profile_manager.py | 18 | Mocks ProfileManager, tests mock |
| tests/unit/test_chrome_manager.py | 20 | Mocks ChromeManager, tests mock |
| tests/unit/test_session_manager.py | 14 | Mocks SessionManager, tests mock |
| tests/unit/test_browser_instance.py | ~15 | Mocks BrowserInstance, tests mock |
| tests/unit/test_browser_navigation.py | ~10 | Mocks navigation methods, tests mock |
| tests/unit/test_mcp_protocol.py | ~15 | Mocks MCP server/transport, tests mock |

**Total**: 92 tests deleted

### Action

```bash
cd /home/ami/Projects/AMI-ORCHESTRATOR/browser
rm tests/unit/test_profile_manager.py
rm tests/unit/test_chrome_manager.py
rm tests/unit/test_session_manager.py
rm tests/unit/test_browser_instance.py
rm tests/unit/test_browser_navigation.py
rm tests/unit/test_mcp_protocol.py
```

### Verification

```bash
# Before: 229 unit tests
# After: 137 unit tests
scripts/ami-run.sh scripts/run_tests.py tests/unit/ --collect-only | grep "test session"
```

---

## Phase 2: Fix Configuration Management

### Problem

Multiple config sources with inconsistent precedence:

```python
# tests/conftest.py:144
test_config = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"

# tests/integration/conftest.py:28
config_file = "config.test.yaml"
if Path("config.yaml").exists():
    config_file = "config.yaml"  # DIFFERENT PRECEDENCE!
elif not Path("config.test.yaml").exists():
    config_file = None
```

### Solution

**Single source of truth**: config.test.yaml

### config.test.yaml Structure

```yaml
# Browser Test Configuration
# Single source of truth for ALL browser tests

backend:
  browser:
    # Chrome/ChromeDriver paths - copied from config.yaml
    chrome_binary_path: /usr/bin/google-chrome  # MUST BE SET
    chromedriver_path: null  # null = use chromedriver-binary package

    # Test-specific browser settings
    headless: true
    window_size: [1280, 720]
    disable_gpu: true
    no_sandbox: true

  storage:
    # Test data directories - isolated from production
    profiles_dir: data/test_profiles
    session_dir: data/test_sessions
    downloads_dir: data/test_downloads
    screenshots_dir: data/test_screenshots

  pool:
    # Smaller pool for tests
    min_instances: 1
    max_instances: 5
    warm_instances: 2
    cleanup_interval: 60

timeouts:
  default: 10
  navigation: 30
  script: 10
  page_load: 30
```

### Update tests/conftest.py

**Before**:
```python
test_config = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"
manager = ChromeManager(config_file=test_config)
```

**After**:
```python
# ALWAYS use config.test.yaml - no fallbacks
test_config = Path("config.test.yaml")
if not test_config.exists():
    raise RuntimeError(
        "config.test.yaml not found. Tests require test-specific configuration. "
        "Copy chrome_binary_path from config.yaml to config.test.yaml"
    )

manager = ChromeManager(config_file="config.test.yaml")
```

### Update tests/integration/conftest.py

**Remove config selection logic entirely**:

```python
# Before: Complex config selection
config_file: str | None = "config.test.yaml"
if Path("config.yaml").exists():
    config_file = "config.yaml"
elif not Path("config.test.yaml").exists():
    config_file = None

# After: Always use config.test.yaml
self.manager = ChromeManager(config_file="config.test.yaml")
```

---

## Phase 3: Fix Cleanup (Remove pkill)

### Problem

Current cleanup violates project rules by using `pkill`:

```python
# tests/conftest.py:352-376
def cleanup_processes() -> None:
    """Kill any remaining browser or server processes."""
    with contextlib.suppress(Exception):
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], ...)
        else:
            subprocess.run(["pkill", "-f", "chrome"], ...)  # VIOLATES CLAUDE.md
            subprocess.run(["pkill", "-f", "chromedriver"], ...)
```

**Project Rules (CLAUDE.md)**:
- "Manage processes only through `scripts/ami-run.sh nodes/scripts/setup_service.py {start|stop|restart} <service>`"
- "NEVER touch `pkill`/`kill*`"

### Solution

**Remove pkill, rely on proper manager.shutdown()**:

```python
def cleanup_test_data() -> None:
    """Clean up accumulated test data directories to prevent resource exhaustion."""
    import shutil
    from pathlib import Path

    data_dir = Path("data")
    if not data_dir.exists():
        return

    # Remove all test_* directories
    with contextlib.suppress(Exception):
        for test_dir in data_dir.glob("test_*"):
            if test_dir.is_dir():
                shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="function", autouse=True)
def cleanup_test_data_fixture() -> Iterator[None]:
    """Clean up test data BEFORE and AFTER each test."""
    # Clean BEFORE test for fresh start
    cleanup_test_data()

    yield

    # Clean AFTER test to prevent accumulation
    cleanup_test_data()
    # DO NOT kill processes - manager.shutdown() handles this


# REMOVE cleanup_processes() function entirely
# REMOVE atexit.register(cleanup_processes)
# REMOVE cleanup_at_exit fixture
```

**If tests leave orphaned processes**: Fix the tests to properly call `manager.shutdown()`, don't kill everything.

---

## Phase 4: Restructure Integration Tests

### Current Structure (Flat)

```
tests/integration/
├── __init__.py
├── conftest.py
├── test_browser_integration.py
├── test_profile_manager_initialization.py
├── test_mcp_tab_session_integration.py
├── test_real_website_session_save.py
├── test_kill_orphaned_flag.py
├── test_profile_conflict.py
├── ... (20+ more files)
```

**Problems**:
- No organization by feature
- Unclear which tests are related
- No shared fixtures per feature
- Serial execution (7-8 minutes)
- Resource accumulation → segfaults

### Target Structure (Feature-Based)

```
tests/integration/
├── __init__.py
├── conftest.py              # Shared fixtures for ALL integration tests
│
├── session/                 # Session save/restore tests
│   ├── __init__.py
│   ├── conftest.py          # Session-specific fixtures
│   ├── test_session_save_restore.py
│   ├── test_session_real_websites.py
│   ├── test_session_mcp_integration.py
│   ├── test_session_https_profile.py
│   └── test_kill_orphaned_flag.py
│
├── profile/                 # Profile management tests
│   ├── __init__.py
│   ├── conftest.py          # Profile-specific fixtures
│   ├── test_profile_manager_initialization.py
│   ├── test_profile_conflict.py
│   └── test_profiles_sessions.py
│
├── navigation/              # Browser navigation & interaction tests
│   ├── __init__.py
│   ├── conftest.py          # Navigation-specific fixtures
│   ├── test_browser_navigation.py
│   ├── test_input_simulation.py
│   ├── test_dynamic_content.py
│   ├── test_screen_space_interactions.py
│   └── test_window_open_tab_url_bug.py
│
├── mcp/                     # MCP server & tool tests
│   ├── __init__.py
│   ├── conftest.py          # MCP-specific fixtures
│   ├── test_chrome_fastmcp_server.py
│   ├── test_mcp_tab_management.py
│   ├── test_mcp_tab_session_integration.py
│   ├── test_mcp_session_save_restore.py
│   ├── test_mcp_client_helpers.py
│   ├── test_run_chrome_runner.py
│   └── test_run_mcp_runner.py
│
├── tools/                   # MCP tool tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_web_search_tool.py
│   └── test_script_validation_integration.py
│
└── pool/                    # Browser pool & instance management tests
    ├── __init__.py
    ├── conftest.py          # Pool-specific fixtures
    ├── test_instance_reuse.py
    └── test_antidetection.py
```

### Migration Plan

**1. Create Directory Structure**:
```bash
cd tests/integration
mkdir -p session profile navigation mcp tools pool
touch session/__init__.py profile/__init__.py navigation/__init__.py mcp/__init__.py tools/__init__.py pool/__init__.py
```

**2. Create Feature-Specific conftest.py Files**:

Each feature gets shared fixtures. Example for `session/conftest.py`:

```python
"""Shared fixtures for session tests."""
import pytest_asyncio
from browser.backend.core.management.manager import ChromeManager

@pytest_asyncio.fixture(scope="module")
async def session_test_manager() -> AsyncIterator[ChromeManager]:
    """Manager configured for session tests."""
    manager = ChromeManager(
        config_file="config.test.yaml",
        config_overrides={
            "backend.storage.session_dir": "data/test_sessions_session_tests",
            "backend.storage.profiles_dir": "data/test_profiles_session_tests",
        }
    )
    await manager.initialize()

    yield manager

    await manager.shutdown()
```

**3. Move Tests to Appropriate Directories**:

| Current File | New Location | Reason |
|-------------|--------------|--------|
| test_real_website_session_save.py | session/ | Session save/restore |
| test_session_https_profile.py | session/ | Session with profile |
| test_mcp_session_save_restore.py | session/ | MCP session |
| test_kill_orphaned_flag.py | session/ | Session restore flag |
| test_profile_manager_initialization.py | profile/ | Profile init |
| test_profile_conflict.py | profile/ | Profile conflicts |
| test_profiles_sessions.py | profile/ | Profile/session interaction |
| test_browser_integration.py | navigation/ | Browser navigation |
| test_screen_space_interactions.py | navigation/ | Mouse/keyboard |
| test_window_open_tab_url_bug.py | navigation/ | Tab management |
| test_chrome_fastmcp_server.py | mcp/ | MCP server |
| test_mcp_tab_management.py | mcp/ | MCP tabs |
| test_mcp_tab_session_integration.py | mcp/ | MCP + session |
| test_mcp_client_helpers.py | mcp/ | MCP helpers |
| test_run_chrome_runner.py | mcp/ | MCP runner |
| test_run_mcp_runner.py | mcp/ | MCP runner |
| test_web_search_tool.py | tools/ | MCP tool |
| test_script_validation_integration.py | tools/ | Script validation |
| test_instance_reuse.py | pool/ | Instance pool |
| test_antidetection.py | pool/ | Antidetect browser |

**4. Update Imports**:

After moving, update any internal imports to reflect new paths.

---

## Phase 5: Enable Parallel Execution

### Problem

All 341 tests run serially → 7-8 minutes, resource accumulation → segfaults

### Solution

Enable pytest-xdist for parallel execution where safe.

### Update pytest.ini

```ini
[pytest]
# Minimum version
minversion = 7.0

# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Asyncio mode
asyncio_mode = auto

# Parallel execution (enabled)
# -n auto = use all CPU cores
# --dist loadfile = tests from same file run together (preserves module fixtures)
addopts =
    -v
    --tb=short
    --strict-markers
    --asyncio-mode=auto
    -n auto
    --dist=loadfile

# Markers for test categorization
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    mcp: marks tests related to MCP server
    browser: marks tests related to browser operations
    pool: marks tests related to browser pool
    session: marks tests related to session management
    profile: marks tests related to profile management
    navigation: marks tests related to navigation
    tools: marks tests related to MCP tools

# Logging
log_cli = false
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Coverage (optional)
# addopts = --cov=browser --cov-report=html --cov-report=term
```

### Serial Tests (if needed)

For tests that MUST run serially (e.g., testing pool state), mark them:

```python
@pytest.mark.serial
def test_pool_state():
    """Test that requires serial execution."""
    pass
```

Then run with: `pytest -m "not serial" -n auto` for parallel, `pytest -m serial` for serial.

---

## Phase 6: Verification & Testing

### Step 1: Run Unit Tests

```bash
cd /home/ami/Projects/AMI-ORCHESTRATOR/browser
scripts/ami-run.sh scripts/run_tests.py tests/unit/ -v
```

**Expected**: 137 tests pass, no failures

### Step 2: Run Integration Tests (by feature)

```bash
# Session tests
scripts/ami-run.sh scripts/run_tests.py tests/integration/session/ -v

# Profile tests
scripts/ami-run.sh scripts/run_tests.py tests/integration/profile/ -v

# Navigation tests
scripts/ami-run.sh scripts/run_tests.py tests/integration/navigation/ -v

# MCP tests
scripts/ami-run.sh scripts/run_tests.py tests/integration/mcp/ -v

# Tools tests
scripts/ami-run.sh scripts/run_tests.py tests/integration/tools/ -v

# Pool tests
scripts/ami-run.sh scripts/run_tests.py tests/integration/pool/ -v
```

**Expected**: All tests pass, no segfaults

### Step 3: Run Full Test Suite

```bash
scripts/ami-run.sh scripts/run_tests.py -v
```

**Expected**:
- ~249 tests pass
- Runtime: 3-5 minutes (with parallelization)
- No Chrome segfaults
- No flaky tests

### Step 4: Run THE CRITICAL TEST 100 times

```bash
for i in {1..100}; do
    echo "Run $i/100"
    scripts/ami-run.sh scripts/run_tests.py tests/integration/mcp/test_mcp_tab_session_integration.py::test_mcp_open_tab_goto_session_save_restore -v || break
done
```

**Expected**: All 100 runs pass

---

## Success Criteria

### Quantitative Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Total tests | 341 | ~249 | 249 |
| Unit tests | 229 | 137 | 137 |
| Integration tests | 114 | 114 | 114 |
| Useless tests deleted | 0 | 92 | 92 |
| Test runtime | 7-8 min | 3-5 min | <5 min |
| Chrome segfaults | Yes | No | 0 |
| Flaky tests | 2+ | 0 | 0 |
| Config sources | 3+ | 1 | 1 |
| Uses pkill | Yes | No | No |

### Qualitative Criteria

- ✅ All tests test REAL code (no mock-only tests)
- ✅ Clear feature-based organization
- ✅ Single config source (config.test.yaml)
- ✅ No pkill usage
- ✅ Proper test isolation (cleanup before + after)
- ✅ Parallel execution enabled
- ✅ THE CRITICAL TEST runs reliably 24/7

---

## Rollback Plan

If restructure causes issues:

```bash
# Restore from git
git checkout HEAD -- tests/
git checkout HEAD -- pytest.ini

# Or restore specific files
git checkout HEAD -- tests/unit/test_profile_manager.py
git checkout HEAD -- tests/unit/test_chrome_manager.py
# ... etc
```

---

## Implementation Timeline

| Phase | Task | Est. Time | Status |
|-------|------|-----------|--------|
| 1 | Delete useless unit tests | 5 min | PENDING |
| 2 | Create config.test.yaml | 10 min | PENDING |
| 2 | Fix conftest.py files | 15 min | PENDING |
| 3 | Remove pkill from cleanup | 10 min | PENDING |
| 4 | Create feature directories | 5 min | PENDING |
| 4 | Create feature conftest.py files | 20 min | PENDING |
| 4 | Move integration tests | 30 min | PENDING |
| 5 | Update pytest.ini | 5 min | PENDING |
| 6 | Run verification tests | 30 min | PENDING |
| **Total** | | **~2 hours** | **0/9 complete** |

---

## Post-Restructure Maintenance

### Adding New Tests

**Unit tests**: Add to `tests/unit/test_<feature>.py`, ensure they test REAL code, not mocks.

**Integration tests**: Add to appropriate feature directory:
- Session tests → `tests/integration/session/`
- Profile tests → `tests/integration/profile/`
- Navigation tests → `tests/integration/navigation/`
- MCP tests → `tests/integration/mcp/`
- Tool tests → `tests/integration/tools/`
- Pool tests → `tests/integration/pool/`

### Code Review Checklist

For new tests, verify:
- ✅ Tests REAL code (not just mocks)
- ✅ In correct feature directory
- ✅ Uses shared fixtures from conftest.py
- ✅ Proper cleanup (uses fixtures, no manual pkill)
- ✅ Can run in parallel (unless marked serial)
- ✅ Passes when run alone AND with full suite

---

## References

- Project Rules: `/home/ami/Projects/AMI-ORCHESTRATOR/CLAUDE.md`
- Browser Rules: `/home/ami/Projects/AMI-ORCHESTRATOR/browser/CLAUDE.md`
- Test Analysis: `/tmp/test_audit_findings.md`
- Restructure Plan: `/tmp/test_restructure_plan.md`
