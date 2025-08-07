# Chrome Manager Integration Tests

Comprehensive integration test suite for the Chrome Manager system, including browser automation, MCP server, and pool management.

## Test Structure

```
tests/
├── fixtures/           # Test fixtures and utilities
│   ├── html/          # Test HTML pages
│   │   ├── login_form.html      # Login form with validation
│   │   ├── captcha_form.html    # Various CAPTCHA types
│   │   └── dynamic_content.html # Dynamic/AJAX content
│   └── test_server.py # HTTP server for serving test pages
├── integration/       # Integration tests
│   ├── test_browser_integration.py  # Browser operations
│   └── test_mcp_server.py          # MCP server tests
└── conftest.py       # Pytest configuration
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all integration tests
python run_integration_tests.py

# Run with coverage
python run_integration_tests.py --coverage
```

### Test Categories

Tests are organized with markers for selective execution:

```bash
# Run only MCP server tests
python run_integration_tests.py -m mcp

# Run only browser tests
python run_integration_tests.py -m browser

# Run all tests except slow ones
python run_integration_tests.py -m "not slow"

# Run specific test
python run_integration_tests.py -k test_navigate_to_page
```

### Advanced Options

```bash
# Verbose output
python run_integration_tests.py -v

# Stop on first failure
python run_integration_tests.py -x

# Use existing test server (don't start new one)
python run_integration_tests.py --no-server
```

## Test Coverage Areas

### 1. Browser Navigation (`test_browser_integration.py`)
- **Page Navigation**: Loading pages, waiting for elements
- **Script Execution**: Injecting and executing JavaScript
- **Content Retrieval**: Getting HTML, element content
- **Performance**: Page load times, metrics

### 2. Input Simulation
- **Form Interaction**: Filling forms, clicking buttons
- **Text Input**: Typing, clearing fields
- **Checkbox/Radio**: Toggle states
- **Complex Interactions**: Drag & drop, hover

### 3. Screenshot & Media
- **Viewport Capture**: Current view screenshots
- **Element Capture**: Specific element screenshots
- **Full Page**: Scrolling full page capture
- **Video Recording**: Session recording (if enabled)

### 4. Dynamic Content
- **AJAX Loading**: Waiting for dynamic content
- **Modal Dialogs**: Interaction with popups
- **Infinite Scroll**: Pagination handling
- **Live Updates**: Real-time content changes

### 5. CAPTCHA Handling
- **Text CAPTCHA**: OCR and solving
- **Math CAPTCHA**: Calculation solving
- **Checkbox**: "I'm not a robot"
- **Puzzle**: Slide/drag puzzles

### 6. MCP Server (`test_mcp_server.py`)
- **Connection**: WebSocket connection, capabilities
- **Browser Control**: Launch, navigate, close
- **Input Operations**: Click, type via MCP
- **Script Execution**: Remote JavaScript execution
- **Cookie Management**: Get/set cookies
- **Tab Management**: Multiple tabs, switching
- **Error Handling**: Invalid requests, timeouts
- **Concurrency**: Multiple clients, parallel operations

### 7. Browser Pool
- **Instance Management**: Create, terminate instances
- **Warm Instances**: Pre-warmed browser pool
- **Parallel Operations**: Multiple browsers simultaneously
- **Resource Management**: Memory, CPU limits

## Test HTML Pages

### login_form.html
- Username/password fields
- Remember me checkbox
- Client-side validation
- Form submission tracking
- Success/error states

### captcha_form.html
- Text CAPTCHA with refresh
- Math problems
- Checkbox verification
- Puzzle sliding
- Audio alternative

### dynamic_content.html
- AJAX content loading
- Modal dialogs
- Tab switching
- Infinite scroll
- Live data updates
- Notifications

## Writing New Tests

### Basic Test Structure

```python
import pytest
from chrome_manager.core.instance import BrowserInstance

@pytest.mark.asyncio
async def test_my_feature(browser_instance, test_server):
    """Test description."""
    nav = NavigationController(browser_instance)
    
    # Navigate to test page
    await nav.navigate(f"{test_server}/test_page.html")
    
    # Perform actions
    result = await nav.execute_script("return document.title")
    
    # Assert results
    assert "Expected Title" in result
```

### Using Fixtures

```python
@pytest.fixture
async def my_fixture():
    """Setup fixture."""
    # Setup
    resource = await create_resource()
    yield resource
    # Teardown
    await cleanup_resource(resource)
```

### Adding Test Markers

```python
@pytest.mark.slow
@pytest.mark.browser
async def test_slow_operation():
    """This test is marked as slow and browser-related."""
    pass
```

## Debugging Tests

### Enable Debug Logging

```python
from loguru import logger

async def test_with_logging():
    logger.debug("Debug information")
    logger.info("Test progress")
    logger.error("Error occurred")
```

### Save Screenshots on Failure

```python
async def test_with_screenshot(browser_instance):
    try:
        # Test code
        assert False
    except AssertionError:
        screenshot = await ScreenshotController(browser_instance).capture_viewport()
        with open("failure.png", "wb") as f:
            f.write(screenshot)
        raise
```

### Interactive Debugging

```python
import pdb

async def test_with_breakpoint():
    # Set breakpoint
    pdb.set_trace()
    # Or use Python 3.7+
    breakpoint()
```

## Performance Testing

### Measure Operation Time

```python
import time

async def test_performance():
    start = time.time()
    # Operation to measure
    await perform_operation()
    duration = time.time() - start
    assert duration < 2.0, f"Operation took {duration}s"
```

### Load Testing

```python
async def test_concurrent_load():
    """Test system under load."""
    tasks = []
    for i in range(10):
        task = asyncio.create_task(perform_operation(i))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    assert all(r.success for r in results)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: python run_integration_tests.py --coverage
```

### Docker Testing

```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt -r requirements-test.txt
CMD ["python", "run_integration_tests.py"]
```

## Troubleshooting

### Common Issues

1. **ChromeDriver version mismatch**
   - Ensure ChromeDriver matches Chrome version
   - Update: `python -m webdriver_manager.chrome`

2. **Port already in use**
   - Test server default port: 8888
   - MCP server default port: 8766
   - Change in conftest.py or use --no-server

3. **Timeout errors**
   - Increase timeout in pytest.ini
   - Use explicit waits in tests

4. **Headless mode issues**
   - Some features work differently in headless
   - Test with `headless=False` for debugging

## Contributing

1. Write tests for new features
2. Ensure all tests pass
3. Maintain >70% code coverage
4. Follow existing test patterns
5. Document complex test scenarios