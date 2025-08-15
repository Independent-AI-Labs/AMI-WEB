# CODE EXCEPTIONS - BROWSER MODULE

This file documents legitimate code patterns that might appear problematic but are actually necessary for the module's functionality.

## 1. Legitimate Polling Patterns

### Download Monitoring
**Location:** `backend/core/storage/storage.py:70`

**Justification:**
Chrome/Selenium doesn't provide download completion events. We must poll the filesystem to detect when downloads finish (checking for `.crdownload` extension disappearance).

### Pattern:
```python
while time.time() - start_time < timeout:
    if file_path.exists() and not str(file_path).endswith(".crdownload"):
        return file_path
    time.sleep(DOWNLOAD_CHECK_INTERVAL)
```

## 2. Configurable Delays for User Experience

### Scroll Delays
**Location:** 
- `backend/facade/navigation/scroller.py:48,93`

**Justification:**
These delays use configurable values from `FacadeConfig` to wait for smooth scrolling animations to complete. This ensures subsequent operations don't execute before the scroll finishes.

### Input Delays
**Location:**
- `backend/facade/input/keyboard.py:50` - Typing delays
- `backend/facade/input/mouse.py:44,97,375` - Click delays
- `backend/facade/input/touch.py:377` - Touch delays

**Justification:**
All these delays use configurable parameters passed by the user to simulate human-like interaction patterns. They're not hardcoded polling but user-controlled timing.

## 3. Import Order Requirements

### Path Setup Required
**Location:**
- `backend/mcp/chrome/run_stdio.py:11-19`
- `backend/mcp/chrome/run_websocket.py:12-20`
- `backend/mcp/chrome/server.py:14-19`

**Justification:**
These scripts must modify `sys.path` BEFORE importing local modules to ensure correct module resolution.

### Pattern:
```python
import sys
sys.path.insert(0, project_root)  # Must come first
from backend.chrome import ChromeManager  # Now safe to import
```

## 4. Type Ignores for CDP Commands

### Selenium CDP Limitations
**Location:** Multiple files using CDP commands

**Justification:**
Selenium's Chrome DevTools Protocol (CDP) commands don't have proper type stubs. The `execute_cdp_cmd` method returns `Any`, requiring type ignores for proper type checking.

### Pattern:
```python
result = driver.execute_cdp_cmd("Page.captureScreenshot", params)  # type: ignore[no-untyped-call]
```

## 5. Screenshot Stitching Delays

### Rendering Waits
**Location:** `backend/facade/media/screenshot.py:126,134`

**Justification:**
Brief delays between screenshots ensure the page has rendered properly after scrolling. This is necessary for accurate full-page screenshot stitching.

## 6. Utility Retry Functions

### Wait and Retry Utilities
**Location:** `backend/utils/timing.py:56-61`

**Justification:**
The `wait_for()` function is a general-purpose utility for retry logic with exponential backoff. It's used for testing and waiting for conditions that don't have native event support.

## Summary

These patterns are intentional design decisions necessary for browser automation functionality. They should NOT be "fixed" as they would break core features like download monitoring, human-like interaction simulation, and screenshot capture.