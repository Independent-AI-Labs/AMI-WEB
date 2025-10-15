# AMI Browser Module

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checking: Mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](http://mypy-lang.org/)
[![Tests: Pytest](https://img.shields.io/badge/tests-pytest-orange.svg)](https://docs.pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-check%20CI-brightgreen.svg)](#testing)

Production-grade Chromium automation with security-first JavaScript execution, session persistence, and comprehensive MCP tooling for AI agents.

## Overview

The Browser module provides a fully-featured Chrome automation platform built on Selenium with anti-detection capabilities, profile isolation, session management, and a FastMCP server exposing 11 tool families. Every JavaScript execution is validated against configurable forbidden patterns to prevent tab corruption and unsafe operations.

## Key Features

- **Script Validation**: Regex-based pattern matching blocks dangerous JavaScript (e.g., `window.open('url', '_blank')`) before execution
- **Session Persistence**: Save and restore complete browser states including multiple tabs, cookies, and active tab tracking
- **Tab Management**: Open, close, switch, and list tabs via `browser_navigate` tool with anti-detection support
- **Profile Management**: Isolated browser profiles with copy, create, delete, and list operations
- **Anti-Detection**: Stealth mode with fingerprint randomization and webdriver flag removal
- **Tab State Protection**: Improved session save logic prevents tab URL corruption during capture
- **React DevTools**: Trigger handlers, inspect props/state, and navigate fiber trees
- **Chunked Responses**: Stream large text extractions with deterministic byte-offset chunking
- **FastMCP Integration**: 11 tool families exposing all browser capabilities via MCP

## What's New

### Tab Management via browser_navigate

The `browser_navigate` tool now supports comprehensive tab management:
- `open_tab` - Create new tabs with optional URL navigation
- `list_tabs` - List all open tabs with current tab indicator
- `switch_tab` - Switch to specific tab by handle ID
- `close_tab` - Close specific or current tab

All tab operations integrate with anti-detection and are fully tested via E2E integration tests.

### Script Validation System

All JavaScript execution now goes through pattern validation to prevent dangerous operations:

```yaml
# res/forbidden_script_patterns.yaml
patterns:
  - pattern: 'window\.open\s*\([^)]*[''"]_blank[''"]'
    reason: "window.open with '_blank' corrupts tab state. Use TabController.create_tab() instead."
    severity: error
    category: tab_management
```

**Blocked patterns include:**
- `window.open()` with `_blank` or `_self` targets (error)
- `window.close()` (error)
- Direct `window.location` assignment (warning)
- `eval()` and `Function()` constructor (warning)
- History manipulation without tracking (warning)

Configure enforcement in `res/forbidden_script_patterns.yaml`:
```yaml
config:
  enforce: true
  warnings_are_errors: false
```

### Improved Tab Management

Session save now captures tab state correctly even when switching between tabs:

- **Before**: Tab URLs could become "about:blank" after `window.open()`
- **After**: Handle states are captured in a single pass, preventing corruption

## Architecture

```
browser/
├── backend/
│   ├── core/
│   │   ├── browser/          # Instance lifecycle, options, tab management
│   │   ├── management/       # ChromeManager, session/profile managers
│   │   ├── security/         # Anti-detect, tab injection, script validator
│   │   └── storage/          # Storage configuration
│   ├── mcp/chrome/
│   │   ├── chrome_server.py  # FastMCP server with 11 tools
│   │   ├── tools/            # Tool implementations
│   │   │   ├── facade/       # V02 unified facades
│   │   │   ├── browser_tools.py
│   │   │   ├── javascript_tools.py  # Script validation here
│   │   │   ├── navigation_tools.py
│   │   │   ├── input_tools.py
│   │   │   ├── extraction_tools.py
│   │   │   ├── screenshot_tools.py
│   │   │   ├── react_tools.py
│   │   │   └── search_tools.py
│   │   └── utils/            # Response limits, chunking
│   └── facade/context/       # TabController, NavigationController
├── res/
│   ├── forbidden_script_patterns.yaml  # Script validation rules
│   └── notbot.png            # Anti-bot CAPTCHA solver asset
├── scripts/
│   ├── run_chrome.py         # MCP server entry point
│   ├── setup_chrome.py       # Install Chromium/ChromeDriver
│   └── run_tests.py          # Test runner
├── tests/
│   ├── unit/                 # Unit tests including script validation
│   └── integration/          # Full browser automation tests
└── web/scripts/              # Anti-detect JavaScript injection
```

## MCP Tools

The `ChromeFastMCPServer` exposes 11 tool families:

### 1. `browser_session` - Instance Lifecycle & Session Persistence

**Actions:**
- `launch` - Create browser instance (headless, profile, anti_detect, use_pool)
- `terminate` - Shut down instance
- `list` - List all instances
- `get_active` - Get currently active instance
- `save` - Save current session (all tabs, cookies, active tab)
- `restore` - Restore saved session (supports `kill_orphaned` to clear profile locks)
- `list_sessions` - List all saved sessions
- `delete_session` - Delete a session
- `rename_session` - Rename a session

**Example:**
```python
# Launch browser
await browser_session(action="launch", headless=False, profile="default")

# Save session
await browser_session(action="save", session_name="my-work-session")

# Restore session
await browser_session(action="restore", session_id="<uuid>", kill_orphaned=True)
```

### 2. `browser_navigate` - Navigation, History & Tab Management

**Actions:** `goto`, `back`, `forward`, `refresh`, `get_url`, `open_tab`, `close_tab`, `switch_tab`, `list_tabs`

**Navigation Examples:**
```python
# Navigate to URL
await browser_navigate(action="goto", url="https://example.com", wait_for="body", timeout=30)

# History navigation
await browser_navigate(action="back")
await browser_navigate(action="forward")
await browser_navigate(action="refresh")
```

**Tab Management Examples:**
```python
# Open new tab with URL
await browser_navigate(action="open_tab", url="https://reddit.com")

# Open empty tab
await browser_navigate(action="open_tab")

# List all tabs
response = await browser_navigate(action="list_tabs")
# Returns: {"tabs": [{"tab_id": "...", "is_current": true}, ...], "count": 2}

# Switch to specific tab
await browser_navigate(action="switch_tab", tab_id="ABC123...")

# Close specific tab
await browser_navigate(action="close_tab", tab_id="ABC123...")

# Close current tab
await browser_navigate(action="close_tab")
```

### 3. `browser_interact` - Element Interaction

**Actions:** `click`, `type`, `select`, `hover`, `scroll`, `press`, `wait`

**Example:**
```python
await browser_interact(action="click", selector="button.submit", timeout=10)
await browser_interact(action="type", selector="input[name='q']", text="search query", clear=True)
await browser_interact(action="scroll", direction="down", amount=500)
```

### 4. `browser_inspect` - DOM Inspection

**Actions:** `get_html`, `exists`, `get_attribute`

**Example:**
```python
await browser_inspect(action="get_html", selector="div.content", max_depth=5)
await browser_inspect(action="exists", selector="button#login")
await browser_inspect(action="get_attribute", selector="img", attribute="src")
```

### 5. `browser_extract` - Content Extraction

**Actions:** `get_text`, `get_cookies`

**Supports chunking** for large text extractions:
```python
# First chunk
result = await browser_extract(
    action="get_text",
    selector="article",
    use_chunking=True,
    offset=0,
    length=10000
)
# Next chunk
result = await browser_extract(
    action="get_text",
    selector="article",
    use_chunking=True,
    offset=result.next_offset,
    length=10000,
    snapshot_checksum=result.snapshot_checksum
)
```

### 6. `browser_capture` - Screenshots

**Actions:** `screenshot`, `element_screenshot`

**Example:**
```python
await browser_capture(action="screenshot", full_page=True, save_to_disk=True)
await browser_capture(action="element_screenshot", selector="div.chart")
```

### 7. `browser_execute` - JavaScript Execution (Validated)

**Actions:** `execute`, `evaluate`

**All scripts are validated before execution.**

**Example:**
```python
# This will succeed
await browser_execute(action="execute", code="document.querySelector('button').click()")

# This will FAIL with validation error
await browser_execute(action="execute", code="window.open('url', '_blank')")
# Error: Script validation failed: [tab_management] window.open with '_blank' corrupts tab state
```

**Use browser_navigate for tab management:**
```python
# Correct way to create tabs via MCP
await browser_navigate(action="open_tab", url="https://reddit.com")
```

### 8. `web_search` - Web Search

Query the configured search engine (defaults to local SearXNG at `http://127.0.0.1:8888`).

**Example:**
```python
await web_search(query="python typing best practices", max_results=10)
```

### 9. `browser_storage` - Downloads & Screenshots Management

**Actions:**
- `list_downloads`, `clear_downloads`, `wait_for_download`
- `list_screenshots`, `clear_screenshots`
- `set_download_behavior`

**Example:**
```python
await browser_storage(action="set_download_behavior", behavior="allow", download_path="/tmp/downloads")
await browser_storage(action="wait_for_download", filename="report.pdf", timeout=60)
```

### 10. `browser_react` - React DevTools Integration

**Actions:** `trigger_handler`, `get_props`, `get_state`, `find_component`, `get_fiber_tree`

**Example:**
```python
await browser_react(action="trigger_handler", selector="button", handler_name="onClick")
await browser_react(action="get_props", selector="div[data-testid='user-card']")
```

### 11. `browser_profile` - Profile Management

**Actions:** `create`, `delete`, `list`, `copy`

**Example:**
```python
await browser_profile(action="create", profile_name="work", description="Work browsing profile")
await browser_profile(action="copy", source_profile="default", dest_profile="work-backup")
```

## Running the Server

### Setup Chromium

```bash
/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh scripts/setup_chrome.py
```

Respects `AMI_COMPUTE_PROFILE` for driver selection (`cpu`, `nvidia`, `intel`, `amd`).

### Start MCP Server

```bash
# stdio transport
/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh scripts/run_chrome.py

# websocket transport
/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh scripts/run_chrome.py --transport websocket --port 9000
```

## Testing

```bash
# Run all tests
/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh scripts/run_tests.py

# Run specific test
/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh scripts/run_tests.py tests/unit/test_script_validator.py -v

# Run integration tests
/home/ami/Projects/AMI-ORCHESTRATOR/scripts/ami-run.sh scripts/run_tests.py tests/integration/ -v
```

**Test Coverage:**
- `tests/unit/test_script_validator.py` - Script validation pattern matching
- `tests/integration/test_script_validation_integration.py` - End-to-end validation blocking
- `tests/integration/test_window_open_tab_url_bug.py` - Tab state preservation
- `tests/integration/test_multiple_tabs_session_persistence.py` - Multi-tab session save/restore
- `tests/integration/test_session_persistence_e2e.py` - Full session persistence flow
- `tests/integration/test_mcp_tab_management.py` - MCP tab management E2E tests

## Configuration

### `config.yaml`

Generated from platform template on first setup:

```yaml
backend:
  tools:
    web_search:
      url_template: "http://127.0.0.1:8888/search?q={query}&format=json"
      timeout: 30
  storage:
    session_dir: "./data/sessions"
    profiles_dir: "./data/profiles"
    downloads_dir: "./data/downloads"
    screenshots_dir: "./data/screenshots"
  browser:
    headless: true
    binary_location: null  # Auto-detected
    driver_path: null      # Auto-detected
```

### Script Validation Config

Edit `res/forbidden_script_patterns.yaml` to customize forbidden patterns:

```yaml
patterns:
  # Add custom patterns
  - pattern: 'dangerous\.api\('
    reason: "This API is forbidden"
    severity: error
    category: custom

config:
  enforce: true                # Block scripts with errors
  warnings_are_errors: false   # Allow warnings
  log_checks: false            # Log all validation checks
```

## Best Practices

### DO ✅

1. **Use browser_navigate for tab management:**
   ```python
   await browser_navigate(action="open_tab", url="https://example.com")
   await browser_navigate(action="list_tabs")
   await browser_navigate(action="switch_tab", tab_id=tab_id)
   ```

2. **Save sessions with descriptive names:**
   ```python
   await browser_session(action="save", session_name="github-pr-review-session")
   ```

3. **Use chunking for large text:**
   ```python
   result = await browser_extract(action="get_text", use_chunking=True, length=10000)
   ```

4. **Restore sessions with orphan cleanup:**
   ```python
   await browser_session(action="restore", session_id=sid, kill_orphaned=True)
   ```

### DON'T ❌

1. **Never use `window.open()` with targets in execute:**
   ```python
   # WRONG - will be blocked
   await browser_execute(action="execute", code="window.open('url', '_blank')")
   ```

2. **Don't bypass script validation:**
   - Validation exists to prevent tab corruption and data loss
   - Use proper APIs instead of low-level DOM manipulation

3. **Don't assume tab order is stable:**
   - Use tab handles/IDs, not indices
   - Session save captures all tabs but restore may reorder

4. **Don't suppress warnings in production:**
   - Keep `warnings_are_errors: false` but review warnings
   - Warnings indicate risky patterns that may cause issues

## Compliance & Audit

- All browser operations are logged via `loguru`
- Session files stored in `data/sessions/<uuid>/session.json`
- Screenshots saved to `data/screenshots/` with timestamps
- Script validation violations logged with matched patterns

Future integration with `compliance/` module will surface:
- Session artifacts as audit evidence
- Script validation denials
- Profile usage tracking
- Search query logs

## Roadmap

- [ ] Multi-window session support
- [ ] CDP raw command passthrough
- [ ] HAR file export
- [ ] Network request interception
- [ ] Custom certificate injection
- [ ] Playwright backend option

## See Also

- `docs/Architecture-Map.md` - Module relationships
- `compliance/docs/research/COMPLIANCE_BACKEND_SPEC.md` - Compliance integration spec
- `res/forbidden_script_patterns.yaml` - Script validation configuration
- `tests/integration/` - Integration test examples
