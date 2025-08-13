# AMI-WEB Extended Documentation

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Installation & Setup](#installation--setup)
3. [Core Components](#core-components)
4. [Facade Layer Reference](#facade-layer-reference)
5. [MCP Tools Reference](#mcp-tools-reference)
6. [Configuration](#configuration)
7. [Anti-Detection System](#anti-detection-system)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [API Examples](#api-examples)

## System Architecture

AMI-WEB follows a layered architecture with clear separation of concerns:

```
External Layer (Clients)
    ↓
MCP Protocol Layer (stdio/WebSocket)
    ↓
Management Layer (ChromeManager)
    ↓
Core Layer (BrowserInstance)
    ↓
Facade Layer (Controllers)
    ↓
Browser (Chrome + CDP)
```

### Component Organization

```
backend/
├── core/                    # Core browser functionality
│   ├── browser/            # Browser instance management
│   │   ├── instance.py     # Main BrowserInstance class
│   │   ├── lifecycle.py    # Launch, terminate, restart logic
│   │   ├── options.py      # Chrome options builder
│   │   ├── properties_manager.py  # Browser fingerprint management
│   │   └── tab_manager.py  # Tab lifecycle management
│   ├── management/         # High-level orchestration
│   │   ├── manager.py      # ChromeManager - main entry point
│   │   ├── pool.py         # Browser pool for pre-warmed instances
│   │   ├── profile_manager.py  # Chrome profile management
│   │   └── session_manager.py  # Session save/restore
│   ├── monitoring/         # Real-time monitoring
│   │   └── monitor.py      # Console logs, performance metrics
│   ├── security/           # Anti-detection features
│   │   ├── antidetect.py   # ChromeDriver patching & scripts
│   │   └── tab_injector.py # Tab-level script injection
│   └── storage/            # Data persistence
│       └── storage.py      # Downloads, cookies, local storage
├── facade/                 # High-level controller interfaces
│   ├── base.py            # BaseController abstract class
│   ├── input/             # User input simulation
│   │   ├── mouse.py       # Click, hover, drag operations
│   │   ├── keyboard.py    # Type, press key operations
│   │   ├── touch.py       # Touch gestures for mobile
│   │   └── forms.py       # Form filling utilities
│   ├── navigation/        # Page navigation & content
│   │   ├── navigator.py   # URL navigation, history
│   │   ├── extractor.py   # Content extraction (HTML, text, links)
│   │   ├── waiter.py      # Wait for elements/conditions
│   │   ├── scroller.py    # Scroll operations
│   │   └── storage.py     # LocalStorage/SessionStorage
│   ├── media/             # Media capture
│   │   ├── screenshot.py  # Screenshot capture
│   │   └── video.py       # Video recording (placeholder)
│   ├── devtools/          # Chrome DevTools integration
│   │   ├── network.py     # Network monitoring
│   │   ├── performance.py # Performance metrics
│   │   └── devtools.py    # Console logs access
│   └── context/           # Browser context management
│       ├── tabs.py        # Tab management
│       └── frames.py      # iFrame handling
├── mcp/                   # Model Context Protocol implementation
│   ├── base/              # Generic MCP server framework
│   │   ├── mcp_server.py  # Base MCP server class
│   │   ├── protocol.py    # MCP protocol implementation
│   │   ├── transport.py   # stdio/WebSocket transports
│   │   ├── auth.py        # Authentication (placeholder)
│   │   └── rate_limit.py  # Rate limiting (placeholder)
│   └── browser/           # Browser-specific MCP
│       ├── server.py      # BrowserMCPServer implementation
│       ├── run_stdio.py   # stdio transport runner
│       ├── run_websocket.py  # WebSocket transport runner
│       └── tools/         # MCP tool definitions
│           ├── definitions.py  # Tool schemas
│           ├── executor.py     # Tool execution logic
│           └── registry.py     # Tool registration
├── models/                # Data models (Pydantic)
│   ├── browser.py         # Browser-related models
│   ├── browser_properties.py  # Fingerprint properties
│   ├── security.py        # Security configurations
│   ├── media.py           # Screenshot/video models
│   └── mcp.py             # MCP protocol models
├── services/              # Business services
│   └── property_injection.py  # Property injection service
└── utils/                 # Utilities
    ├── config.py          # Configuration management
    ├── exceptions.py      # Custom exceptions
    ├── javascript.py      # JS script utilities
    ├── paths.py           # Path utilities
    ├── selectors.py       # CSS selector utilities
    ├── timing.py          # Timing constants
    └── threading.py       # Thread-safe operations
```

## Installation & Setup

### Prerequisites

- Python 3.12 recommended (3.10+ supported)
- Windows 10/11, macOS 11+, or Ubuntu 20.04+
- 4GB RAM minimum (8GB recommended)
- Chrome and ChromeDriver included in repository

### Installation Steps

```bash
# Clone repository
git clone https://github.com/Independent-AI-Labs/AMI-WEB.git
cd AMI-WEB

# Install uv for fast dependency management (REQUIRED)
pip install uv

# The start script will automatically:
# 1. Create virtual environment at .venv/
# 2. Install all dependencies from requirements.txt
# 3. Start the appropriate server

# Start MCP server (auto-setup included)
python scripts/start_mcp_server.py              # stdio mode (Claude Desktop)
python scripts/start_mcp_server.py websocket    # WebSocket mode
python scripts/start_mcp_server.py websocket --host 0.0.0.0 --port 8080  # Custom

# Manual setup (if needed)
uv venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
uv pip install -r requirements.txt
uv pip install -r requirements-test.txt  # For development

# Configure (optional - has defaults)
cp config.sample.yaml config.yaml
# Edit config.yaml as needed
```

## Core Components

### ChromeManager

Central orchestrator managing all browser operations.

```python
from backend.core.management.manager import ChromeManager
from backend.models.security import SecurityConfig, SecurityLevel

# Initialize
manager = ChromeManager(config_file="config.yaml")
await manager.initialize()

# Get or create instance with all options
instance = await manager.get_or_create_instance(
    headless=True,                    # Run in headless mode
    profile="my_profile",             # Use named profile (auto-created)
    anti_detect=True,                  # Enable anti-detection (default: True)
    use_pool=True,                     # Use pre-warmed pool (default: True)
    security_config=SecurityConfig.from_level(SecurityLevel.STANDARD),
    download_dir="./downloads",       # Custom download directory
    extensions=["path/to/extension"], # Chrome extensions to load
)

# Core instance management
await manager.get_instance(instance_id)          # Get existing instance
await manager.terminate_instance(instance_id)    # Fully terminate
await manager.return_to_pool(instance_id)        # Return for reuse
await manager.list_instances()                   # List all active

# Session management
session_id = await manager.save_session(instance_id, "shopping_session")
restored = await manager.restore_session(session_id)

# Browser properties (fingerprinting)
from backend.models.browser_properties import BrowserPropertiesPreset

await manager.set_browser_properties(
    instance_id=instance.id,
    preset="stealth"  # Or "minimal", "moderate", "aggressive"
)
props = await manager.get_browser_properties(instance_id)

# Pool statistics
stats = await manager.get_pool_stats()
# {'total_instances': 5, 'available': 2, 'in_use': 3, ...}

# Batch execution
tasks = [
    {"type": "navigate", "params": {"url": "https://example.com"}},
    {"type": "screenshot", "params": {}},
    {"type": "execute_script", "params": {"script": "return document.title"}}
]
results = await manager.execute_batch(tasks, max_concurrent=5)

# Cleanup
await manager.shutdown()
```

### ProfileManager

Manages Chrome profiles with complete isolation.

```python
from backend.core.management.profile_manager import ProfileManager

profile_manager = ProfileManager(base_dir="./data/browser_profiles")

# Methods available:
profile_dir = profile_manager.create_profile(name, description)
profile_dir = profile_manager.get_profile_dir(name)
success = profile_manager.delete_profile(name)
profiles = profile_manager.list_profiles()
new_dir = profile_manager.copy_profile(source, dest)
```

### SessionManager

Saves and restores browser sessions.

```python
from backend.core.management.session_manager import SessionManager

session_manager = SessionManager(session_dir="./data/sessions")
await session_manager.initialize()

# Methods available:
session_id = await session_manager.save_session(instance, name)
instance = await session_manager.restore_session(session_id)
sessions = await session_manager.list_sessions()
success = session_manager.delete_session(session_id)
await session_manager.shutdown()
```

### BrowserPool

Manages pre-warmed browser instances for instant availability.

```python
# Configured via ChromeManager
pool_stats = await manager.get_pool_stats()
# Returns: {
#   "total_instances": 5,
#   "available": 2,
#   "in_use": 3,
#   "warm_target": 2,
#   "health_checks_run": 150
# }
```

## Facade Layer Reference

### Navigation Components

#### Navigator
```python
from backend.facade.navigation.navigator import Navigator

nav = Navigator(browser_instance)
result = await nav.navigate(url, wait_for="domcontentloaded", timeout=30)
await nav.back()
await nav.forward()
await nav.refresh()
current_url = await nav.get_current_url()
title = await nav.get_title()
```

#### ContentExtractor
```python
from backend.facade.navigation.extractor import ContentExtractor

extractor = ContentExtractor(browser_instance)
html = await extractor.get_page_content()
element_html = await extractor.get_element_html(selector)
element_text = await extractor.get_element_text(selector)
result = await extractor.execute_script(script, *args)
limited_html = await extractor.get_html_with_depth_limit(max_depth=3)
text = await extractor.extract_text(preserve_structure=True)
links = await extractor.extract_links(absolute=True)
forms = await extractor.extract_forms()
```

#### Waiter
```python
from backend.facade.navigation.waiter import Waiter

waiter = Waiter(browser_instance)
found = await waiter.wait_for_element(selector, timeout=10)
found = await waiter.wait_for_element_visible(selector, timeout=10)
gone = await waiter.wait_for_element_hidden(selector, timeout=10)
```

#### Scroller
```python
from backend.facade.navigation.scroller import Scroller

scroller = Scroller(browser_instance)
await scroller.scroll_to_element(selector, smooth=True)
await scroller.scroll_to_position(x=0, y=500, smooth=True)
await scroller.scroll_by(x=0, y=200, smooth=False)
await scroller.scroll_to_top(smooth=True)
await scroller.scroll_to_bottom(smooth=True)
position = await scroller.get_scroll_position()
```

#### StorageController
```python
from backend.facade.navigation.storage import StorageController

storage = StorageController(browser_instance)
value = await storage.get_local_storage(key)
await storage.set_local_storage(key, value)
await storage.clear_local_storage()
value = await storage.get_session_storage(key)
await storage.set_session_storage(key, value)
await storage.clear_session_storage()
```

### Input Components

#### MouseController
```python
from backend.facade.input.mouse import MouseController

mouse = MouseController(browser_instance)
await mouse.click(selector, button="left", click_count=1)
await mouse.click_at_coordinates(x, y, button="left", click_count=1)
await mouse.double_click(selector)
await mouse.right_click(selector)
await mouse.hover(selector)
await mouse.drag_and_drop(source_selector, target_selector)
await mouse.drag_from_to(start_x, start_y, end_x, end_y, duration=1.0)
```

#### KeyboardController
```python
from backend.facade.input.keyboard import KeyboardController

keyboard = KeyboardController(browser_instance)
await keyboard.type_text(selector, text, clear=True, delay=0.1)
await keyboard.press_key(key)  # e.g., "Enter", "Tab", "Escape"
await keyboard.send_keys(selector, keys)  # e.g., ["ctrl+a", "delete"]
await keyboard.clear_field(selector)
```

#### TouchController
```python
from backend.facade.input.touch import TouchController

touch = TouchController(browser_instance)
await touch.tap(selector)
await touch.double_tap(selector)
await touch.long_press(selector, duration=1.0)
await touch.swipe(start_x, start_y, end_x, end_y, duration=0.5)
await touch.pinch_zoom(selector, scale=2.0)
```

#### FormsController
```python
from backend.facade.input.forms import FormsController

forms = FormsController(browser_instance)
await forms.fill_form(form_data)  # Dict of field_name: value
await forms.submit_form(form_selector)
await forms.select_option(select_selector, value)
await forms.check_checkbox(checkbox_selector)
await forms.uncheck_checkbox(checkbox_selector)
await forms.select_radio(radio_selector)
form_data = await forms.get_form_data(form_selector)
```

### Media Components

#### ScreenshotController
```python
from backend.facade.media.screenshot import ScreenshotController

screenshot = ScreenshotController(browser_instance)
png_bytes = await screenshot.capture_viewport()
png_bytes = await screenshot.capture_full_page()
png_bytes = await screenshot.capture_element(selector)
base64_str = await screenshot.capture_as_base64()
file_path = await screenshot.save_screenshot(filename="screenshot.png")
```

### DevTools Components

#### NetworkMonitor
```python
from backend.facade.devtools.network import NetworkMonitor

network = NetworkMonitor(browser_instance)
await network.start_monitoring()
requests = await network.get_requests()
responses = await network.get_responses()
await network.clear_data()
await network.stop_monitoring()
```

#### PerformanceMonitor
```python
from backend.facade.devtools.performance import PerformanceMonitor

perf = PerformanceMonitor(browser_instance)
metrics = await perf.get_metrics()
# Returns: navigation_start, dom_content_loaded, load_complete, first_paint, etc.
timing = await perf.get_timing()
memory = await perf.get_memory_info()
```

### Context Components

#### TabManager
```python
from backend.facade.context.tabs import TabManager

tabs = TabManager(browser_instance)
tab_list = await tabs.get_tabs()
await tabs.switch_to_tab(tab_id)
new_tab = await tabs.open_new_tab(url)
await tabs.close_tab(tab_id)
current = await tabs.get_current_tab()
```

## MCP Tools Reference

AMI-WEB provides the following MCP tools:

### Browser Lifecycle
- `browser_launch` - Launch new browser instance
- `browser_terminate` - Terminate browser instance
- `browser_list` - List all active instances
- `browser_get_active` - Get currently active instance

### Navigation
- `browser_navigate` - Navigate to URL
- `browser_back` - Go back in history
- `browser_forward` - Go forward in history
- `browser_refresh` - Refresh current page
- `browser_get_url` - Get current URL

### Input
- `browser_click` - Click on element
- `browser_type` - Type text into field
- `browser_select` - Select dropdown option
- `browser_scroll` - Scroll the page
- `browser_execute_script` - Execute JavaScript

### Content
- `browser_get_text` - Extract page text
- `browser_get_html` - Get HTML content
- `browser_extract_forms` - Extract all forms
- `browser_extract_links` - Extract all links

### Media
- `browser_screenshot` - Take screenshot

### Tabs
- `browser_get_tabs` - List open tabs
- `browser_switch_tab` - Switch to specific tab

### Storage
- `browser_get_cookies` - Get cookies
- `browser_set_cookies` - Set cookies
- `browser_clear_cookies` - Clear cookies

### Monitoring
- `browser_get_console_logs` - Get console logs
- `browser_get_network_logs` - Get network logs

### Profiles
- `profile_create` - Create new profile
- `profile_list` - List all profiles
- `profile_delete` - Delete profile

### Sessions
- `session_save` - Save current session
- `session_load` - Load saved session
- `session_list` - List saved sessions

## Configuration

### config.yaml Structure

```yaml
backend:
  browser:
    chrome_binary_path: "./chromium-win/chrome.exe"
    chromedriver_path: "./chromedriver.exe"
    default_headless: true
    default_window_size: [1920, 1080]
    
  pool:
    min_instances: 1
    max_instances: 10
    warm_instances: 2
    instance_ttl: 3600
    health_check_interval: 30
    
  storage:
    session_dir: "./data/sessions"
    profiles_dir: "./data/browser_profiles"
    download_dir: "./data/downloads"
    
  security:
    level: "standard"  # strict/standard/relaxed/permissive
    
  browser_properties:
    preset: "stealth"  # Fingerprint preset
    overrides:
      user_agent: "Mozilla/5.0..."
      webgl_vendor: "Google Inc. (Intel)"
      webgl_renderer: "ANGLE..."
```

## Anti-Detection System

### CDP Script Injection

AMI-WEB uses Chrome DevTools Protocol for automatic script injection:

```python
# Automatically injected on all new documents
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": antidetect_script,
    "runImmediately": True
})
```

### Fingerprint Management

Control all browser parameters:
- WebDriver property removal
- Plugin array simulation
- WebGL vendor/renderer spoofing
- Canvas noise injection
- Audio context modification
- Chrome runtime simulation
- Permissions API override

### ChromeDriver Patching

Binary-level modifications to remove automation indicators.

## Testing

### Test Structure

```
tests/
├── unit/                  # Unit tests
│   ├── test_chrome_manager.py
│   ├── test_mcp_auth.py
│   └── test_mcp_rate_limit.py
├── integration/          # Integration tests
│   ├── test_browser_integration.py
│   ├── test_browser_properties.py
│   ├── test_profiles_sessions.py
│   ├── test_screen_space_interactions.py
│   ├── test_mcp_server.py
│   └── test_antidetection.py
└── fixtures/            # Test data
    └── html/           # Test HTML pages
```

### Running Tests

```bash
# Using test runner script (auto-handles virtual env)
python scripts/run_tests.py                    # All tests
python scripts/run_tests.py tests/unit/        # Unit tests only
python scripts/run_tests.py -k test_browser    # Pattern matching
python scripts/run_tests.py -x                 # Stop on first failure
python scripts/run_tests.py --cov=backend      # With coverage

# Specific test files
python scripts/run_tests.py tests/integration/test_antidetection.py -v
python scripts/run_tests.py tests/integration/test_browser_properties.py
python scripts/run_tests.py tests/integration/test_profiles_sessions.py

# Direct pytest (must activate venv first)
.venv\Scripts\activate  # Windows
python -m pytest tests/ -v --tb=short
python -m pytest tests/unit/test_chrome_manager.py::test_basic_operations -xvs
```

## Troubleshooting

### Common Issues

#### Browser Won't Launch
- Check Chrome/ChromeDriver paths in config.yaml
- Verify Chrome and ChromeDriver versions match
- Ensure sufficient memory available

#### MCP Connection Failed
- Verify server is running: `python scripts/start_mcp_server.py`
- Check port availability (default 8765)
- Review logs in data/logs/

#### Profile Not Found
- Profiles are created automatically on first use
- Check profiles_dir in config.yaml
- Verify write permissions

#### Session Restore Failed
- Sessions require matching profile
- Check session_dir in config.yaml
- Ensure cookies haven't expired

### Debug Mode

Enable detailed logging:

```python
from loguru import logger
logger.add(sys.stderr, level="DEBUG")
```

### Health Monitoring

```python
# Check instance health
health = await instance.health_check()
# Returns: memory_usage, cpu_usage, tab_count, status

# Pool statistics
stats = await manager.get_pool_stats()
```

## API Examples

### Complete Automation Example

```python
import asyncio
from backend.core.management.manager import ChromeManager
from backend.facade.navigation.navigator import Navigator
from backend.facade.input.mouse import MouseController
from backend.facade.input.keyboard import KeyboardController
from backend.facade.media.screenshot import ScreenshotController

async def automate_form_submission():
    # Initialize manager
    manager = ChromeManager()
    await manager.initialize()
    
    # Get browser instance with anti-detection
    instance = await manager.get_or_create_instance(
        headless=False,
        anti_detect=True,
        profile="automation_profile"
    )
    
    # Initialize controllers
    nav = Navigator(instance)
    mouse = MouseController(instance)
    keyboard = KeyboardController(instance)
    screenshot = ScreenshotController(instance)
    
    # Navigate to page
    await nav.navigate("https://example.com/form")
    
    # Fill form
    await keyboard.type_text("#username", "john.doe", clear=True)
    await keyboard.type_text("#email", "john@example.com", clear=True)
    
    # Click checkbox
    await mouse.click("#agree-terms")
    
    # Take screenshot before submission
    await screenshot.save_screenshot("before_submit.png")
    
    # Submit form
    await mouse.click("#submit-button")
    
    # Wait for success
    from backend.facade.navigation.waiter import Waiter
    waiter = Waiter(instance)
    await waiter.wait_for_element(".success-message", timeout=10)
    
    # Save session for later
    session_id = await manager.save_session(instance.id, "form_completed")
    print(f"Session saved: {session_id}")
    
    # Cleanup
    await manager.terminate_instance(instance.id)
    await manager.shutdown()

# Run the automation
asyncio.run(automate_form_submission())
```

### MCP Server Usage

```python
# For Claude Desktop integration
# Add to claude_desktop_config.json:
{
  "mcpServers": {
    "ami-web": {
      "command": "python",
      "args": ["C:/path/to/AMI-WEB/scripts/start_mcp_server.py", "stdio"]
    }
  }
}

# For programmatic WebSocket usage:
import asyncio
import websockets
import json

async def use_mcp_server():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Launch browser
        await websocket.send(json.dumps({
            "method": "tools/call",
            "params": {
                "name": "browser_launch",
                "arguments": {
                    "headless": False,
                    "anti_detect": True
                }
            }
        }))
        response = await websocket.recv()
        print(f"Browser launched: {response}")
        
        # Navigate to URL
        await websocket.send(json.dumps({
            "method": "tools/call",
            "params": {
                "name": "browser_navigate",
                "arguments": {"url": "https://example.com"}
            }
        }))
        response = await websocket.recv()
        print(f"Navigation result: {response}")
```

## Support

- [GitHub Issues](https://github.com/Independent-AI-Labs/AMI-WEB/issues)
- [Documentation](https://github.com/Independent-AI-Labs/AMI-WEB/docs)
- [Contributing Guide](../CONTRIBUTING.md)

---

*AMI-WEB - Enterprise Browser Automation with Complete Control*