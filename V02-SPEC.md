# Browser MCP V02 Facade Specification

**Version:** 2.0
**Date:** 2025-10-03
**Status:** Implementation Ready

---

## Executive Summary

The V02 facade simplifies the Browser MCP tool surface from **29 granular tools** to **9 action-based tools**. This reduces cognitive load for LLM agents, improves tool selection accuracy, and provides a cleaner API surface while maintaining full feature parity.

### Key Changes

- **Tool Count:** 29 → 9 (69% reduction)
- **Action-Based:** Unified interfaces with action dispatch
- **Breaking Change:** V01 tools are retired (no migration layer)
- **Feature Complete:** 100% feature parity with V01 + new storage management

---

## V02 Tools Overview

| Tool | Purpose | Actions | V01 Tools Replaced |
|------|---------|---------|-------------------|
| `browser_session` | Instance lifecycle management | launch, terminate, list, get_active | 4 tools |
| `browser_navigate` | Page navigation and history | goto, back, forward, refresh, get_url | 5 tools |
| `browser_interact` | Element interaction and waiting | click, type, select, hover, scroll, press, wait | 7 tools |
| `browser_inspect` | DOM structure inspection | get_html, exists, get_attribute | 3 tools |
| `browser_extract` | Content extraction | get_text, get_cookies | 3 tools (including chunked variant) |
| `browser_capture` | Visual capture (with disk save) | screenshot, element_screenshot | 2 tools |
| `browser_execute` | JavaScript execution | execute, evaluate | 4 tools (including chunked variants) |
| `browser_storage` | Download/screenshot management | list_downloads, clear_downloads, wait_for_download, list_screenshots, clear_screenshots, set_download_behavior | NEW |
| `web_search` | Web search | (unchanged) | 1 tool |

**Total:** 9 tools covering 29+ operations

---

## Detailed Tool Specifications

### 1. browser_session

**Description:** Manage browser instance lifecycle (launch, terminate, list).

**Parameters:**

```python
action: Literal["launch", "terminate", "list", "get_active"]  # Required
instance_id: str | None = None  # Required for "terminate"
headless: bool = True
profile: str | None = None
anti_detect: bool = False
use_pool: bool = True
```

**Actions:**

- **launch:** Create new browser instance
  - Returns: `instance_id` in response
  - Parameters: `headless`, `profile`, `anti_detect`, `use_pool`

- **terminate:** Shutdown browser instance
  - Requires: `instance_id`
  - Returns: `data.status = "terminated"`

- **list:** List all active instances
  - Returns: `data.instances` (array of instance info)

- **get_active:** Get currently active instance
  - Returns: `instance_id` of active instance

**Response Fields:**
- `success`: bool
- `instance_id`: str | None
- `data`: dict (action-specific)

**V01 Mapping:**
- `browser_launch` → `browser_session(action="launch")`
- `browser_terminate` → `browser_session(action="terminate")`
- `browser_list` → `browser_session(action="list")`
- `browser_get_active` → `browser_session(action="get_active")`

---

### 2. browser_navigate

**Description:** Navigate pages and manage browser history.

**Parameters:**

```python
action: Literal["goto", "back", "forward", "refresh", "get_url"]  # Required
url: str | None = None  # Required for "goto"
wait_for: str | None = None  # CSS selector to wait for after navigation
timeout: float = 30
```

**Actions:**

- **goto:** Navigate to URL
  - Requires: `url`
  - Optional: `wait_for` (CSS selector), `timeout`
  - Returns: `url` in response

- **back:** Navigate back in history
  - Returns: `data.status = "navigated_back"`

- **forward:** Navigate forward in history
  - Returns: `data.status = "navigated_forward"`

- **refresh:** Reload current page
  - Returns: `data.status = "refreshed"`

- **get_url:** Get current page URL
  - Returns: `url` in response

**Response Fields:**
- `success`: bool
- `url`: str | None
- `data`: dict

**V01 Mapping:**
- `browser_navigate` → `browser_navigate(action="goto")`
- `browser_back` → `browser_navigate(action="back")`
- `browser_forward` → `browser_navigate(action="forward")`
- `browser_refresh` → `browser_navigate(action="refresh")`
- `browser_get_url` → `browser_navigate(action="get_url")`

---

### 3. browser_interact

**Description:** Interact with page elements (click, type, select, etc.).

**Parameters:**

```python
action: Literal["click", "type", "select", "hover", "scroll", "press", "wait"]  # Required
selector: str | None = None  # Required for most actions except scroll, press

# Type action parameters
text: str | None = None  # Required for "type"
clear: bool = False  # For "type"
delay: float = 0  # For "type" (typing delay in seconds)

# Click action parameters
button: str = "left"  # For "click" (left/right/middle)
click_count: int = 1  # For "click"

# Select action parameters (one required)
value: str | None = None  # For "select" (by value)
index: int | None = None  # For "select" (by index)
label: str | None = None  # For "select" (by label text)

# Scroll action parameters
direction: str = "down"  # For "scroll" (up/down/left/right)
amount: int = 100  # For "scroll" (pixels)

# Press action parameters
key: str | None = None  # Required for "press"
modifiers: list[str] | None = None  # For "press" (ctrl, alt, shift, meta)

# Wait action parameters
state: str = "visible"  # For "wait" (visible/hidden/present)
timeout: float = 30  # For "wait"
```

**Actions:**

- **click:** Click element
  - Requires: `selector`
  - Optional: `button`, `click_count`

- **type:** Type text into element
  - Requires: `selector`, `text`
  - Optional: `clear`, `delay`

- **select:** Select dropdown option
  - Requires: `selector` + one of (`value` | `index` | `label`)

- **hover:** Hover over element
  - Requires: `selector`

- **scroll:** Scroll page or element
  - Optional: `direction`, `amount`

- **press:** Press keyboard key
  - Requires: `key`
  - Optional: `modifiers`

- **wait:** Wait for element state
  - Requires: `selector`
  - Optional: `state`, `timeout`

**Response Fields:**
- `success`: bool
- `data.status`: str (e.g., "clicked", "typed", "selected")

**V01 Mapping:**
- `browser_click` → `browser_interact(action="click")`
- `browser_type` → `browser_interact(action="type")`
- `browser_select` → `browser_interact(action="select")`
- `browser_hover` → `browser_interact(action="hover")`
- `browser_scroll` → `browser_interact(action="scroll")`
- `browser_press` → `browser_interact(action="press")`
- `browser_wait_for` → `browser_interact(action="wait")`

---

### 4. browser_inspect

**Description:** Inspect DOM structure and element properties.

**Parameters:**

```python
action: Literal["get_html", "exists", "get_attribute"]  # Required
selector: str | None = None  # Element selector (null = full page for get_html)

# get_html action parameters
max_depth: int | None = None  # Maximum DOM depth to traverse
collapse_depth: int | None = None  # Depth at which to collapse to summaries
ellipsize_text_after: int = 128  # Truncate text content after N chars

# get_attribute action parameters
attribute: str | None = None  # Required for "get_attribute"
```

**Actions:**

- **get_html:** Get HTML structure with depth limiting
  - Optional: `selector` (null = full page)
  - Optional: `max_depth`, `collapse_depth`, `ellipsize_text_after`
  - Returns: `text` (HTML string), `truncated`, `returned_bytes`, `total_bytes_estimate`

- **exists:** Check if element exists
  - Requires: `selector`
  - Returns: `data.exists` (boolean)

- **get_attribute:** Get element attribute value
  - Requires: `selector`, `attribute`
  - Returns: `data.value` (attribute value)

**Response Fields:**
- `success`: bool
- `text`: str | None (for get_html)
- `data`: dict (action-specific)
- `truncated`: bool
- `returned_bytes`: int | None
- `total_bytes_estimate`: int | None

**V01 Mapping:**
- `browser_get_html` → `browser_inspect(action="get_html")`
- `browser_exists` → `browser_inspect(action="exists")`
- `browser_get_attribute` → `browser_inspect(action="get_attribute")`

---

### 5. browser_extract

**Description:** Extract text content with element tags and auto-ellipsization, or get cookies.

**Parameters:**

```python
action: Literal["get_text", "get_cookies"]  # Required
selector: str | None = None  # Required for "get_text" (null = document.body)

# Chunking support for large text
use_chunking: bool = False
offset: int = 0
length: int | None = None
snapshot_checksum: str | None = None

# Text extraction parameters (get_text action only)
ellipsize_text_after: int = 128  # Truncate each element's text after N chars
include_tag_names: bool = True   # Prefix text with element tag (e.g., "div#id: text")
skip_hidden: bool = True         # Skip hidden/invisible elements
max_depth: int | None = None     # Maximum DOM depth to traverse
```

**Actions:**

- **get_text:** Extract text content with element tags
  - Requires: `selector`
  - Optional: Chunking parameters for large content
  - Optional: `ellipsize_text_after`, `include_tag_names`, `skip_hidden`, `max_depth`
  - Text format: Each visible element on a new line with tag prefix (if `include_tag_names=True`)
  - Example output:
    ```
    h1#title: Welcome to Our Site
    p.intro: This is the introduction text that describes...
    div.content: Main content goes here with automatic...
    ```
  - Returns: `text`, `truncated`, `returned_bytes`, `total_bytes_estimate`
  - Chunked returns: Also `chunk_start`, `chunk_end`, `next_offset`, `remaining_bytes`, `snapshot_checksum`

- **get_cookies:** Get all browser cookies
  - Returns: `cookies` (array of cookie objects)

**Response Fields:**
- `success`: bool
- `text`: str | None
- `cookies`: list[dict] | None
- `truncated`: bool
- `returned_bytes`: int | None
- `total_bytes_estimate`: int | None
- Chunking fields (when `use_chunking=True`):
  - `chunk_start`: int
  - `chunk_end`: int
  - `next_offset`: int | None
  - `remaining_bytes`: int
  - `snapshot_checksum`: str

**V01 Mapping:**
- `browser_get_text` → `browser_extract(action="get_text")`
- `browser_get_text_chunk` → `browser_extract(action="get_text", use_chunking=True)`
- `browser_get_cookies` → `browser_extract(action="get_cookies")`

---

### 6. browser_capture

**Description:** Capture screenshots of page or elements (saves to disk by default).

**Parameters:**

```python
action: Literal["screenshot", "element_screenshot"]  # Required
selector: str | None = None  # Required for "element_screenshot"
full_page: bool = False  # For "screenshot"
save_to_disk: bool = True  # Save to disk (default) or return base64
```

**Actions:**

- **screenshot:** Capture full page or viewport
  - Optional: `full_page`
  - Optional: `save_to_disk` (default: True) - saves to configured screenshot directory
  - Returns: `data.filepath` (when `save_to_disk=True`) OR `screenshot` (base64 PNG when False)

- **element_screenshot:** Capture specific element
  - Requires: `selector`
  - Optional: `save_to_disk` (default: True) - saves to configured screenshot directory
  - Returns: `data.filepath` (when `save_to_disk=True`) OR `screenshot` (base64 PNG when False)

**Response Fields:**
- `success`: bool
- When `save_to_disk=True` (default):
  - `data.filepath`: str (full path to saved file)
  - `data.filename`: str (filename only)
  - `data.format`: "png"
  - `data.saved`: true
- When `save_to_disk=False`:
  - `screenshot`: str (base64 encoded PNG)
  - `data.format`: "base64"

**V01 Mapping:**
- `browser_screenshot` → `browser_capture(action="screenshot")`
- `browser_element_screenshot` → `browser_capture(action="element_screenshot")`

---

### 7. browser_execute

**Description:** Execute JavaScript code or evaluate expressions.

**Parameters:**

```python
action: Literal["execute", "evaluate"]  # Required
code: str  # Required: JavaScript code (execute) or expression (evaluate)
args: list[Any] | None = None  # Arguments for execute action

# Chunking support for large results
use_chunking: bool = False
offset: int = 0
length: int | None = None
snapshot_checksum: str | None = None
```

**Actions:**

- **execute:** Execute JavaScript code
  - Requires: `code`
  - Optional: `args` (script arguments)
  - Optional: Chunking parameters for large string results
  - Returns: `result` (execution result), optionally with chunking metadata

- **evaluate:** Evaluate JavaScript expression
  - Requires: `code` (expression)
  - Optional: Chunking parameters for large string results
  - Returns: `result` (expression value), optionally with chunking metadata

**Response Fields:**
- `success`: bool
- `result`: Any
- `truncated`: bool
- `returned_bytes`: int | None (for string results)
- `total_bytes_estimate`: int | None
- Chunking fields (when `use_chunking=True` and result is string):
  - `chunk_start`: int
  - `chunk_end`: int
  - `next_offset`: int | None
  - `remaining_bytes`: int
  - `snapshot_checksum`: str

**V01 Mapping:**
- `browser_execute` → `browser_execute(action="execute")`
- `browser_execute_chunk` → `browser_execute(action="execute", use_chunking=True)`
- `browser_evaluate` → `browser_execute(action="evaluate")`
- `browser_evaluate_chunk` → `browser_execute(action="evaluate", use_chunking=True)`

---

### 8. browser_storage

**Description:** Manage downloads and screenshots storage (NEW in V02).

**Parameters:**

```python
action: Literal[
    "list_downloads",
    "clear_downloads",
    "wait_for_download",
    "list_screenshots",
    "clear_screenshots",
    "set_download_behavior"
]  # Required
filename: str | None = None  # For "wait_for_download"
timeout: int = 30  # For "wait_for_download"
behavior: str = "allow"  # For "set_download_behavior" (allow, deny, allowAndName, default)
download_path: str | None = None  # For "set_download_behavior"
```

**Actions:**

- **list_downloads:** List all downloaded files
  - Returns: `data.downloads` (list of file metadata), `data.count`

- **clear_downloads:** Delete all downloaded files
  - Returns: `data.cleared` (number of files deleted)

- **wait_for_download:** Wait for a download to complete
  - Optional: `filename` (specific file to wait for)
  - Optional: `timeout` (seconds)
  - Returns: `data.filepath`, `data.filename`, `data.found`

- **list_screenshots:** List all saved screenshots
  - Returns: `data.screenshots` (list of file metadata), `data.count`

- **clear_screenshots:** Delete all saved screenshots
  - Returns: `data.cleared` (number of files deleted)

- **set_download_behavior:** Configure download behavior via CDP
  - Requires: `behavior` ("allow", "deny", "allowAndName", "default")
  - Optional: `download_path` (custom download directory)
  - Returns: `data.behavior`, `data.path`

**Response Fields:**
- `success`: bool
- Action-specific fields in `data`:
  - Downloads/Screenshots list: `{name, path, size, modified}`
  - Cleared count: `{cleared: int}`
  - Wait result: `{filepath, filename, found}`
  - Download behavior: `{behavior, path}`

**V01 Mapping:**
- NEW tool, no V01 equivalent

---

### 9. web_search

**Description:** Run web search using configured engine (unchanged from V01).

**Parameters:**

```python
query: str  # Required
max_results: int = 10
search_engine_url: str | None = None
timeout: float | None = None
```

**Response Fields:**
- `success`: bool
- `result.results`: list[SearchResult]
  - `rank`: int
  - `title`: str
  - `url`: str
  - `snippet`: str | None
- `text`: str (formatted summary)
- `data.provider`: str
- `data.query`: str
- `data.request_url`: str

**V01 Mapping:**
- `web_search` → `web_search` (unchanged)

---

## Response Format

All tools return a unified `BrowserResponse` object:

```python
class BrowserResponse:
    success: bool                          # Operation success status
    error: str | None = None               # Error message if failed
    data: dict[str, Any] | None = None     # Action-specific data

    # Instance management
    instance_id: str | None = None

    # Navigation
    url: str | None = None

    # Content extraction
    text: str | None = None
    cookies: list[dict] | None = None

    # JavaScript execution
    result: Any = None

    # Visual capture
    screenshot: str | None = None  # Base64 encoded

    # Response size metadata
    truncated: bool = False
    returned_bytes: int | None = None
    total_bytes_estimate: int | None = None

    # Chunking metadata
    chunk_start: int | None = None
    chunk_end: int | None = None
    next_offset: int | None = None
    remaining_bytes: int | None = None
    snapshot_checksum: str | None = None
```

---

## Migration from V01 to V02

### Breaking Changes

1. **Tool names changed** - All granular tool names replaced with 8 action-based tools
2. **Action parameter required** - All tools (except `web_search`) require `action` parameter
3. **Parameter consolidation** - Some parameters renamed or restructured
4. **No migration layer** - V01 tools completely removed

### Migration Examples

#### Example 1: Launching and navigating

**V01:**
```python
# Launch browser
await session.call_tool("browser_launch", {"headless": True})

# Navigate
await session.call_tool("browser_navigate", {"url": "https://example.com"})
```

**V02:**
```python
# Launch browser
await session.call_tool("browser_session", {
    "action": "launch",
    "headless": True
})

# Navigate
await session.call_tool("browser_navigate", {
    "action": "goto",
    "url": "https://example.com"
})
```

#### Example 2: Interacting with elements

**V01:**
```python
# Click button
await session.call_tool("browser_click", {"selector": "#submit"})

# Type text
await session.call_tool("browser_type", {
    "selector": "#username",
    "text": "admin",
    "clear": True
})
```

**V02:**
```python
# Click button
await session.call_tool("browser_interact", {
    "action": "click",
    "selector": "#submit"
})

# Type text
await session.call_tool("browser_interact", {
    "action": "type",
    "selector": "#username",
    "text": "admin",
    "clear": True
})
```

#### Example 3: Extracting content

**V01:**
```python
# Get text
await session.call_tool("browser_get_text", {"selector": ".content"})

# Get HTML
await session.call_tool("browser_get_html", {
    "selector": "#main",
    "max_depth": 5
})
```

**V02:**
```python
# Get text
await session.call_tool("browser_extract", {
    "action": "get_text",
    "selector": ".content"
})

# Get HTML
await session.call_tool("browser_inspect", {
    "action": "get_html",
    "selector": "#main",
    "max_depth": 5
})
```

#### Example 4: Chunked content extraction

**V01:**
```python
# First chunk
result = await session.call_tool("browser_get_text_chunk", {
    "selector": "body",
    "offset": 0
})

# Next chunk
if result.next_offset:
    result = await session.call_tool("browser_get_text_chunk", {
        "selector": "body",
        "offset": result.next_offset,
        "snapshot_checksum": result.snapshot_checksum
    })
```

**V02:**
```python
# First chunk
result = await session.call_tool("browser_extract", {
    "action": "get_text",
    "selector": "body",
    "use_chunking": True,
    "offset": 0
})

# Next chunk
if result.next_offset:
    result = await session.call_tool("browser_extract", {
        "action": "get_text",
        "selector": "body",
        "use_chunking": True,
        "offset": result.next_offset,
        "snapshot_checksum": result.snapshot_checksum
    })
```

---

## Complete V01 → V02 Mapping Table

| V01 Tool | V02 Tool | V02 Action | Notes |
|----------|----------|------------|-------|
| `browser_launch` | `browser_session` | `launch` | - |
| `browser_terminate` | `browser_session` | `terminate` | - |
| `browser_list` | `browser_session` | `list` | - |
| `browser_get_active` | `browser_session` | `get_active` | - |
| `browser_navigate` | `browser_navigate` | `goto` | - |
| `browser_back` | `browser_navigate` | `back` | - |
| `browser_forward` | `browser_navigate` | `forward` | - |
| `browser_refresh` | `browser_navigate` | `refresh` | - |
| `browser_get_url` | `browser_navigate` | `get_url` | - |
| `browser_click` | `browser_interact` | `click` | - |
| `browser_type` | `browser_interact` | `type` | - |
| `browser_select` | `browser_interact` | `select` | - |
| `browser_hover` | `browser_interact` | `hover` | - |
| `browser_scroll` | `browser_interact` | `scroll` | - |
| `browser_press` | `browser_interact` | `press` | - |
| `browser_wait_for` | `browser_interact` | `wait` | - |
| `browser_get_html` | `browser_inspect` | `get_html` | - |
| `browser_exists` | `browser_inspect` | `exists` | - |
| `browser_get_attribute` | `browser_inspect` | `get_attribute` | - |
| `browser_get_text` | `browser_extract` | `get_text` | - |
| `browser_get_text_chunk` | `browser_extract` | `get_text` | Set `use_chunking=True` |
| `browser_get_cookies` | `browser_extract` | `get_cookies` | - |
| `browser_screenshot` | `browser_capture` | `screenshot` | - |
| `browser_element_screenshot` | `browser_capture` | `element_screenshot` | - |
| `browser_execute` | `browser_execute` | `execute` | - |
| `browser_execute_chunk` | `browser_execute` | `execute` | Set `use_chunking=True` |
| `browser_evaluate` | `browser_execute` | `evaluate` | - |
| `browser_evaluate_chunk` | `browser_execute` | `evaluate` | Set `use_chunking=True` |
| `web_search` | `web_search` | (N/A) | Unchanged |

---

## Implementation Notes

### File Structure

```
browser/backend/mcp/chrome/
├── chrome_server.py              # Updated: Register 8 V02 tools
├── response.py                    # Unchanged: BrowserResponse model
└── tools/
    ├── facade/                    # NEW: V02 simplified facade
    │   ├── __init__.py
    │   ├── session.py            # browser_session
    │   ├── navigation.py         # browser_navigate
    │   ├── interaction.py        # browser_interact
    │   ├── inspection.py         # browser_inspect
    │   ├── extraction.py         # browser_extract
    │   ├── capture.py            # browser_capture
    │   └── execution.py          # browser_execute
    ├── browser_tools.py          # DELETED (integrated into facade)
    ├── navigation_tools.py       # DELETED (integrated into facade)
    ├── input_tools.py            # DELETED (integrated into facade)
    ├── extraction_tools.py       # KEPT (called by facade)
    ├── javascript_tools.py       # KEPT (called by facade)
    ├── screenshot_tools.py       # KEPT (called by facade)
    └── search_tools.py           # KEPT (unchanged)
```

### Implementation Strategy

1. **Create facade tools** in `backend/mcp/chrome/tools/facade/`
2. **Facade tools dispatch** to existing implementation functions
3. **Update chrome_server.py** to register only 8 V02 tools
4. **Delete V01-specific tool modules** (browser_tools, navigation_tools, input_tools)
5. **Keep core implementations** (extraction_tools, javascript_tools, screenshot_tools helpers)
6. **Update all tests** to use V02 tool names and action parameters

### Validation Requirements

- Action parameter must be valid for each tool
- Required parameters must be present for each action
- Clear error messages for invalid action/parameter combinations
- Response format must remain consistent with BrowserResponse model

---

## Benefits of V02 Facade

1. **Reduced Cognitive Load** - 72% fewer tools (8 vs 29)
2. **Better Tool Selection** - LLMs make fewer tool selection errors
3. **Logical Grouping** - Related operations grouped by category
4. **Cleaner API** - Action-based interface is more intuitive
5. **Extensible** - Easy to add new actions to existing tools
6. **Consistent Interface** - Similar parameter patterns across tools
7. **Context Efficient** - Fewer tools in context window = more room for conversation

---

## Configuration

V02 facade uses the same configuration as V01:

```yaml
mcp:
  tool_limits:
    global_max_bytes: 256000
    defaults:
      response_bytes: 64000

    browser_get_text:
      response_bytes: 64000
      chunk_bytes: 16000

    browser_execute:
      response_bytes: 32000
      chunk_bytes: 12000

    browser_evaluate:
      response_bytes: 32000
      chunk_bytes: 12000

    browser_get_html:
      response_bytes: 128000
      chunk_bytes: 32000
      ellipsize_text_after: 128

    chunks:
      default_chunk_size_bytes: 16000
      max_chunk_bytes: 128000
```

Configuration paths remain unchanged; facade tools internally map to the same limits as V01 tools.

---

## End of Specification
