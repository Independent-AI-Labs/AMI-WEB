# CRITICAL BROWSER MODULE AUDIT - FORBIDDEN FALLBACKS & DANGEROUS BEHAVIOR

**Date**: 2025-10-06
**Auditor**: Claude Code
**Scope**: `/home/ami/Projects/AMI-ORCHESTRATOR/browser/backend`

---

## 🚨 SEVERITY LEVELS

- **CRITICAL**: Data loss, silent failures, security issues
- **HIGH**: Breaks instance affinity, violates explicit failure requirement
- **MEDIUM**: Code quality, inconsistency
- **LOW**: Documentation, minor issues

---

## 🔴 CRITICAL ISSUES

### 1. Session Restore Silent Tab Clobbering [CRITICAL]
**Location**: `backend/core/management/session_manager.py:352-356`

**Problem**:
- `restore_session()` calls `manager.get_or_create_instance()` which can return EXISTING instance
- If instance already has tabs, they are SILENTLY OVERWRITTEN without warning
- USER DATA LOSS - all active tabs destroyed

**Current Code**:
```python
instance = await manager.get_or_create_instance(
    profile=profile_name,
    headless=use_headless,
    kill_orphaned=kill_orphaned,
)
# Lines 360-378 then REPLACE all tabs in this instance
```

**Impact**: User opens tabs [A, B, C], then restores session. Instance is reused, tabs are silently replaced with restored tabs. Original work LOST.

**Fix Required**:
1. Add `force_reset: bool = False` parameter to `restore_session()`
2. Check if instance has existing tabs before clobbering
3. Raise error if tabs exist and `force_reset=False`
4. Add warning log if `force_reset=True`
5. Update facade tool to accept `force_reset` parameter

---

### 2. Session Restore Missing Instance Context [CRITICAL]
**Location**: `backend/mcp/chrome/tools/facade/session.py:87-101`

**Problem**:
- `_restore_session()` creates new instance but NEVER calls `manager.set_current_instance(instance.id)`
- Subsequent tool calls don't know which instance to use
- Tools fall back to wrong instance or auto-create new ones
- THIS IS ROOT CAUSE OF TEST FAILURE (1 tab restored instead of 2)

**Current Code**:
```python
instance = await manager.session_manager.restore_session(...)
return BrowserResponse(
    success=True,
    data={"instance_id": instance.id, ...}
)
```

**Missing Line After Line 93**:
```python
manager.set_current_instance(instance.id)
```

**Impact**: Breaks instance affinity completely after session restore. All subsequent operations may use wrong instance.

---

### 3. Silent Exception Suppression in Cleanup [CRITICAL]
**Location**: `backend/core/management/manager.py:311-319`

**Problem**:
- Uses `with suppress(Exception):` to hide ALL errors during instance termination
- Masks critical failures like locked files, zombie processes, resource leaks
- No logging of what was suppressed

**Current Code**:
```python
if pool_managed:
    with suppress(Exception):  # Line 311 - HIDES EVERYTHING
        await self.pool.retire_invalid_browser(instance_id)
    return

instance = self._standalone_instances.pop(instance_id, None)
if not instance:
    return
with suppress(Exception):  # Line 318 - HIDES EVERYTHING
    await instance.terminate(force=True)
```

**Impact**: Resource leaks, zombie Chrome processes, locked profiles silently ignored.

**Fix Required**: Log exceptions before suppressing, or use specific exception types only.

---

## 🟠 HIGH SEVERITY - FORBIDDEN FALLBACKS

### 4. `get_current_instance()` Forbidden Fallback [HIGH]
**Location**: `backend/core/management/manager.py:123-142`

**Problem**: Falls back to `list_instances()[0]` if no current instance set.

**FORBIDDEN CODE** (Lines 131-139):
```python
async def get_current_instance(self) -> BrowserInstance | None:
    """Get the current instance, or fallback to first available."""  # ← FORBIDDEN
    if self._current_instance_id:
        instance = await self.get_instance(self._current_instance_id)
        if instance:
            return instance
        self._current_instance_id = None

    # FORBIDDEN FALLBACK - REMOVE LINES 131-139
    instances = await self.list_instances()
    if instances:
        return await self.get_instance(instances[0].id)
    return None
```

**Fix Required**: Remove lines 136-139. Return `None` explicitly, no fallback.

**Corrected**:
```python
async def get_current_instance(self) -> BrowserInstance | None:
    """Get the current instance."""
    if self._current_instance_id:
        instance = await self.get_instance(self._current_instance_id)
        if instance:
            return instance
        self._current_instance_id = None
    return None  # NO FALLBACK
```

---

### 5. `browser_get_active_tool()` Forbidden Fallback [HIGH]
**Location**: `backend/mcp/chrome/tools/browser_tools.py:62-70`

**Problem**: Uses `instances[0]` instead of current instance context.

**FORBIDDEN CODE**:
```python
async def browser_get_active_tool(manager: ChromeManager) -> BrowserResponse:
    """Get the currently active browser instance."""
    logger.debug("Getting active browser instance")

    # For now, return the first instance if available  ← FORBIDDEN COMMENT
    instances = await manager.list_instances()  # ← FORBIDDEN
    active_id = instances[0].id if instances else None  # ← FORBIDDEN FALLBACK

    return BrowserResponse(success=True, instance_id=active_id)
```

**Fix Required**:
```python
async def browser_get_active_tool(manager: ChromeManager) -> BrowserResponse:
    """Get the currently active browser instance."""
    instance = await manager.get_current_instance()
    if not instance:
        return BrowserResponse(success=False, error="No active instance")
    return BrowserResponse(success=True, instance_id=instance.id)
```

---

### 6. `_acquire_healthy_instance()` Triple Fallback Chain [HIGH]
**Location**: `backend/mcp/chrome/tools/navigation_tools.py:40-68`

**Problem**: Three fallbacks in a row, ending with AUTO-CREATE.

**FORBIDDEN CODE**:
```python
async def _acquire_healthy_instance(manager: ChromeManager, instance_id: str | None = None):
    # Fallback 1: Try specific instance
    if instance_id:
        instance = await manager.get_instance(instance_id)
        if instance:
            return True, instance

    # FORBIDDEN FALLBACK 2: Try current instance
    instance = await manager.get_current_instance()
    if instance:
        return True, instance

    # FORBIDDEN FALLBACK 3: AUTO-CREATE NEW INSTANCE
    instance = await manager.get_or_create_instance(headless=default_headless, use_pool=True)
    manager.set_current_instance(instance.id)
    return False, instance
```

**Fix Required**:
```python
async def _acquire_healthy_instance(manager: ChromeManager, instance_id: str | None = None):
    if instance_id:
        instance = await manager.get_instance(instance_id)
        if not instance:
            raise RuntimeError(f"Instance {instance_id} not found")
        return instance

    instance = await manager.get_current_instance()
    if not instance:
        raise RuntimeError("No current instance - launch browser first")
    return instance
```

**NO FALLBACKS. FAIL EXPLICITLY.**

---

### 7. `browser_storage_tool()` Uses `instances[0]` [HIGH]
**Location**: `backend/mcp/chrome/tools/facade/storage.py:44-54`

**Problem**: Uses `list_instances()[0]` instead of current instance.

**FORBIDDEN CODE**:
```python
instances = await manager.list_instances()  # Line 44
if not instances and action not in {"list_screenshots", "clear_screenshots"}:
    return BrowserResponse(success=False, error="No browser instance available")

# Get instance for actions that need it
instance = None
if action in {"list_downloads", "clear_downloads", "wait_for_download", "set_download_behavior"}:
    instance_info = instances[0]  # Line 51 - FORBIDDEN
    instance = await manager.get_instance(instance_info.id)
```

**Fix Required**: Add `instance_id` parameter, use `manager.get_instance_or_current(instance_id)`.

---

## 🟡 MEDIUM SEVERITY

### 8. Session Manager Fallback Comments [MEDIUM]
**Location**: `backend/core/management/session_manager.py`

**Problem**: Multiple "fallback" comments suggest fallback logic (lines 103, 109, 220, 246, 252).

**Details**:
- Line 103: `"""Get tab data for the active tab, with fallback to first real tab."""`
- Line 109: `# Fallback: use first non-chrome tab, or first tab`
- Line 220: `last_real_tab = None  # Fallback: last real page we saw`

**Assessment**: These are INTERNAL session save/restore fallbacks for determining active tab, NOT instance selection fallbacks. **ACCEPTABLE** - this is about tab selection within a single instance, not instance selection.

---

### 9. Navigation Extractor "For Now" Comment [MEDIUM]
**Location**: `backend/facade/navigation/extractor.py:267`

**Code**: `# For now, just return the HTML as-is`

**Assessment**: Temporary implementation note. Not a fallback. Low priority.

---

## 📊 SUMMARY STATISTICS

**Total Issues Found**: 9
**Critical**: 3 (data loss, silent failures)
**High**: 4 (forbidden fallbacks)
**Medium**: 2 (code quality)

---

## ✅ REQUIRED FIXES

### Must Fix Immediately:
1. ✅ Add `manager.set_current_instance(instance.id)` after session restore (Issue #2)
2. ✅ Remove fallback from `get_current_instance()` (Issue #4)
3. ✅ Fix `browser_get_active_tool()` to use current instance (Issue #5)
4. ✅ Remove triple fallback chain from `_acquire_healthy_instance()` (Issue #6)
5. ✅ Fix `browser_storage_tool()` to use instance context (Issue #7)

### Must Fix Before Production:
6. ⚠️ Add `force_reset` flag to session restore (Issue #1)
7. ⚠️ Replace `suppress(Exception)` with logged cleanup (Issue #3)

---

## 🔍 ADDITIONAL FINDINGS

### Silent Exception Patterns Found:
- `backend/facade/media/video.py:85` - `suppress(asyncio.CancelledError)` - **ACCEPTABLE** (graceful shutdown)
- `backend/core/browser/instance.py:162,170,178,267` - `suppress(psutil.*)` - **ACCEPTABLE** (process cleanup)

### No Implicit OR Operators Found:
- Searched for `|| None`, `|| []`, `|| {}`, `|| ""` patterns
- **CLEAN** - No Python implicit fallbacks via OR operators

---

## 📝 NOTES

**Explicit Failure Philosophy**:
- NO fallbacks allowed
- NO silent auto-creation
- NO `instances[0]` access
- Fail fast with clear error messages
- User must explicitly launch browser before operations

**Instance Context Tracking**:
- `manager.set_current_instance(id)` after launch/restore
- `manager.get_current_instance()` returns current or None
- `manager.get_instance_or_current(id)` for tools with optional instance_id
- NO fallbacks to `list_instances()[0]`

---

**END OF AUDIT**
