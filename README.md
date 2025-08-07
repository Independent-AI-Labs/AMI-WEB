# AMI-WEB Chrome Manager 🚀

A powerful, enterprise-grade Chrome browser automation framework with Model Context Protocol (MCP) server support, built for scalability, reliability, and ease of use.

## 🌟 Features

### Core Capabilities
- **🎯 Browser Instance Management**: Efficient pooling and lifecycle management of Chrome instances
- **🔄 MCP Server Integration**: Full Model Context Protocol support with WebSocket communication
- **📸 Advanced Screenshot Capture**: Full page, viewport, and element-specific screenshots
- **🎮 Input Automation**: Click, type, scroll, and complex interaction chains
- **🍪 Cookie Management**: Full cookie CRUD operations with domain filtering
- **📑 Tab Management**: Multi-tab navigation and window handling
- **💾 Storage Access**: Local Storage and Session Storage read/write capabilities
- **📊 Performance Monitoring**: Console logs, network logs, and performance metrics
- **🔍 Content Extraction**: Smart text, link, form, and table extraction
- **🎭 Browser Profiles**: Support for custom Chrome profiles and extensions
- **⚡ Async/Await Support**: Fully asynchronous architecture for high performance

### Advanced Features
- **Chrome DevTools Protocol (CDP)** integration for advanced debugging
- **Network throttling** and device emulation
- **Geolocation spoofing** and timezone override
- **URL blocking** and request interception
- **Headless and headful** browser modes
- **Automatic retry** mechanisms with exponential backoff
- **Resource pooling** for efficient instance reuse
- **Thread-safe** operations for concurrent automation

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Usage Examples](#-usage-examples)
- [MCP Server](#-mcp-server)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- Google Chrome browser installed
- ChromeDriver (automatically managed)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/ami-web.git
cd ami-web

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Unix/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Install via pip (when published)

```bash
pip install ami-web-chrome-manager
```

## 🚀 Quick Start

### Basic Usage

The Chrome Manager provides a simple API for browser automation with async/await support.

### Using the MCP Server

The MCP Server exposes browser automation capabilities via WebSocket for AI agents and other clients.

## 🏗 Architecture

### Component Overview

```
AMI-WEB Chrome Manager
├── Core Layer
│   ├── ChromeManager     # Main orchestrator
│   ├── BrowserInstance   # Individual browser instance
│   ├── InstancePool      # Resource pooling
│   └── DriverFactory     # ChromeDriver management
├── Facade Layer
│   ├── NavigationController  # Page navigation
│   ├── InputController       # User interactions
│   ├── ScreenshotController  # Screenshot capture
│   ├── DevToolsController    # CDP integration
│   └── MediaController       # Media handling
├── MCP Server
│   ├── WebSocket Handler     # Client connections
│   ├── Tool Registry         # Available tools
│   └── Request Processor     # Command execution
└── Utilities
    ├── HTMLParser            # Content extraction
    ├── ExceptionHandler      # Error management
    └── Logger               # Logging system
```

### Design Patterns

- **Facade Pattern**: Simplified interfaces for complex browser operations
- **Factory Pattern**: Dynamic browser instance creation
- **Object Pool Pattern**: Efficient resource reuse
- **Observer Pattern**: Event-driven architecture for MCP
- **Strategy Pattern**: Pluggable screenshot and extraction strategies

## 💡 Usage Examples

### Web Scraping

Extract structured data from websites efficiently using headless mode and smart waiting strategies.

### Form Automation

Automate form filling and submission with built-in input controls and validation waiting.

### Multi-Tab Operations

Handle multiple browser tabs simultaneously for comparison shopping, data aggregation, or parallel processing.

### Performance Monitoring

Monitor page performance metrics, console logs, and network activity for debugging and optimization.

## 🔌 MCP Server

### Available MCP Tools

The MCP server exposes the following tools via WebSocket:

#### Browser Lifecycle
- `browser_launch` - Launch a new browser instance
- `browser_close` - Close a browser instance
- `browser_list` - List all active instances

#### Navigation
- `browser_navigate` - Navigate to a URL
- `browser_back` - Go back in history
- `browser_forward` - Go forward in history
- `browser_refresh` - Refresh the current page

#### Interaction
- `browser_click` - Click an element
- `browser_type` - Type text into an element
- `browser_scroll` - Scroll the page
- `browser_wait_for_element` - Wait for element to appear

#### Content Extraction
- `browser_screenshot` - Capture screenshots
- `browser_get_html` - Get raw HTML source of page or element
- `browser_extract_text` - Extract page text
- `browser_extract_links` - Extract all links
- `browser_execute_script` - Execute JavaScript

#### Data Management
- `browser_get_cookies` - Get browser cookies
- `browser_set_cookies` - Set browser cookies
- `browser_get_local_storage` - Read local storage
- `browser_set_local_storage` - Write to local storage
- `browser_remove_local_storage` - Delete storage item
- `browser_clear_local_storage` - Clear all storage
- `browser_get_session_storage` - Read session storage
- `browser_set_session_storage` - Write session storage

#### Monitoring
- `browser_get_console_logs` - Get console logs
- `browser_get_network_logs` - Get network activity
- `browser_get_tabs` - List browser tabs
- `browser_switch_tab` - Switch active tab

### WebSocket Client Example

Connect to the MCP server using WebSocket clients in JavaScript/Node.js, Python, or any language with WebSocket support. The server sends capabilities on connection and processes tool requests with JSON messaging.

## 📚 API Reference

### ChromeManager

Main orchestrator for browser instance lifecycle management with pooling support.

### BrowserInstance

Individual browser instance with navigation, screenshot, script execution, and content extraction capabilities.

### NavigationController

Handles page navigation, scrolling, waiting, and storage operations.

### InputController

Manages user input simulation including clicks, typing, and drag-and-drop operations.

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chrome_manager --cov-report=html

# Run specific test file
pytest tests/integration/test_mcp_server.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── test_manager.py
│   ├── test_instance.py
│   └── test_pool.py
├── integration/          # Integration tests
│   ├── test_mcp_server.py
│   ├── test_mcp_logs_storage.py
│   ├── test_browser_integration.py
│   └── test_screen_space_interactions.py
└── fixtures/            # Test fixtures and utilities
    ├── test_pages/      # HTML test files
    └── threaded_server.py
```

### Writing Tests

Tests use pytest with async support and follow the standard test structure with setup, execution, and teardown phases.

## ⚙️ Configuration

### Environment Variables

```bash
# Chrome binary path (optional)
CHROME_BINARY_PATH=/path/to/chrome

# ChromeDriver path (optional)
CHROMEDRIVER_PATH=/path/to/chromedriver

# Default headless mode
DEFAULT_HEADLESS=true

# Pool configuration
POOL_MIN_INSTANCES=1
POOL_MAX_INSTANCES=10
POOL_WARM_INSTANCES=2

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8765
MCP_MAX_CONNECTIONS=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=chrome_manager.log
```

### Configuration File

Create `config.yaml`:

```yaml
chrome:
  binary_path: null  # Auto-detect
  driver_path: null  # Auto-download
  default_options:
    - "--no-sandbox"
    - "--disable-dev-shm-usage"
    - "--disable-blink-features=AutomationControlled"

pool:
  min_instances: 1
  max_instances: 10
  warm_instances: 2
  instance_timeout: 3600  # seconds
  cleanup_interval: 300  # seconds

mcp:
  server_host: "localhost"
  server_port: 8765
  max_connections: 10
  ping_interval: 30
  ping_timeout: 10

logging:
  level: "INFO"
  format: "{time} | {level} | {message}"
  rotation: "10 MB"
```

## 🔧 Troubleshooting

### Common Issues

#### Chrome fails to start
- Specify Chrome binary path explicitly in configuration

#### ChromeDriver version mismatch
- Update ChromeDriver to match installed Chrome version

#### Timeout errors
- Increase timeout values for slow-loading pages

#### Memory leaks with long-running instances
- Enable automatic cleanup with periodic instance recycling

### Debug Mode

Enable detailed logging by setting LOG_LEVEL environment variable to DEBUG or configuring loguru.

### Performance Tips

1. **Use headless mode** for better performance
2. **Reuse instances** via the pool instead of creating new ones
3. **Disable images** for faster page loads
4. **Use specific waits** instead of fixed delays
5. **Batch operations** when possible