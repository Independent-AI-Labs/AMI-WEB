"""React-specific tools for Chrome MCP server."""

from typing import Any

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse


async def browser_react_trigger_handler_tool(
    manager: ChromeManager,
    selector: str,
    handler_name: str,
    event_data: dict[str, Any] | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Trigger React event handler on an element.

    Args:
        manager: Chrome manager instance
        selector: CSS selector for target element
        handler_name: Handler name (e.g., "onClick", "onDoubleClick", "onChange")
        event_data: Optional event data to pass to the handler
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with execution result
    """
    logger.debug(
        f"Triggering React handler: {handler_name} on {selector}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    # JavaScript to find and trigger React handler
    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) {
        return { success: false, error: 'Element not found' };
    }

    // Find React fiber
    const reactKey = Object.keys(element).find(key => key.startsWith('__reactFiber'));
    if (!reactKey) {
        return { success: false, error: 'React fiber not found - element may not be a React component' };
    }

    const fiber = element[reactKey];
    let currentFiber = fiber;
    let handler = null;

    // Traverse fiber tree to find handler
    while (currentFiber) {
        if (currentFiber.memoizedProps && currentFiber.memoizedProps[arguments[1]]) {
            handler = currentFiber.memoizedProps[arguments[1]];
            break;
        }
        currentFiber = currentFiber.return;
    }

    if (!handler) {
        return { success: false, error: 'Handler not found: ' + arguments[1] };
    }

    // Create synthetic event if event data provided
    const eventData = arguments[2];
    if (eventData) {
        handler(eventData);
    } else {
        handler();
    }

    return { success: true, message: 'Handler triggered successfully' };
    """

    result = instance.driver.execute_script(script, selector, handler_name, event_data)

    if isinstance(result, dict):
        if result.get("success"):
            return BrowserResponse(
                success=True, result=result.get("message", "Handler triggered")
            )
        return BrowserResponse(
            success=False, error=result.get("error", "Unknown error")
        )

    return BrowserResponse(success=True, result="Handler triggered")


async def browser_react_get_props_tool(
    manager: ChromeManager,
    selector: str,
    max_depth: int = 10,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Get React component props.

    Args:
        manager: Chrome manager instance
        selector: CSS selector for target element
        max_depth: Maximum fiber tree depth to traverse
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with component props
    """
    logger.debug(f"Getting React props for: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) {
        return { success: false, error: 'Element not found' };
    }

    const reactKey = Object.keys(element).find(key => key.startsWith('__reactFiber'));
    if (!reactKey) {
        return { success: false, error: 'React fiber not found' };
    }

    const fiber = element[reactKey];
    let currentFiber = fiber;
    const maxDepth = arguments[1];
    let depth = 0;

    while (currentFiber && depth < maxDepth) {
        if (currentFiber.memoizedProps) {
            // Filter out internal React props and functions for cleaner output
            const props = {};
            for (const key in currentFiber.memoizedProps) {
                if (!key.startsWith('__') && typeof currentFiber.memoizedProps[key] !== 'function') {
                    props[key] = currentFiber.memoizedProps[key];
                }
            }
            if (Object.keys(props).length > 0) {
                return { success: true, props: props };
            }
        }
        currentFiber = currentFiber.return;
        depth++;
    }

    return { success: false, error: 'No props found' };
    """

    result = instance.driver.execute_script(script, selector, max_depth)

    if isinstance(result, dict):
        if result.get("success"):
            return BrowserResponse(success=True, result=result.get("props", {}))
        return BrowserResponse(
            success=False, error=result.get("error", "Unknown error")
        )

    return BrowserResponse(success=True, result=result)


async def browser_react_get_state_tool(
    manager: ChromeManager,
    selector: str,
    max_depth: int = 10,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Get React component state.

    Args:
        manager: Chrome manager instance
        selector: CSS selector for target element
        max_depth: Maximum fiber tree depth to traverse
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with component state
    """
    logger.debug(f"Getting React state for: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) {
        return { success: false, error: 'Element not found' };
    }

    const reactKey = Object.keys(element).find(key => key.startsWith('__reactFiber'));
    if (!reactKey) {
        return { success: false, error: 'React fiber not found' };
    }

    const fiber = element[reactKey];
    let currentFiber = fiber;
    const maxDepth = arguments[1];
    let depth = 0;

    while (currentFiber && depth < maxDepth) {
        if (currentFiber.memoizedState) {
            return { success: true, state: currentFiber.memoizedState };
        }
        currentFiber = currentFiber.return;
        depth++;
    }

    return { success: false, error: 'No state found - component may be stateless' };
    """

    result = instance.driver.execute_script(script, selector, max_depth)

    if isinstance(result, dict):
        if result.get("success"):
            return BrowserResponse(success=True, result=result.get("state"))
        return BrowserResponse(
            success=False, error=result.get("error", "Unknown error")
        )

    return BrowserResponse(success=True, result=result)


async def browser_react_find_component_tool(
    manager: ChromeManager, component_name: str, instance_id: str | None = None
) -> BrowserResponse:
    """Find React component by type or displayName.

    Args:
        manager: Chrome manager instance
        component_name: Component name to search for
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with component information
    """
    logger.debug(
        f"Finding React component: {component_name}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    script = """
    const componentName = arguments[0];
    const allElements = document.querySelectorAll('*');
    const found = [];

    for (const element of allElements) {
        const reactKey = Object.keys(element).find(key => key.startsWith('__reactFiber'));
        if (!reactKey) continue;

        const fiber = element[reactKey];
        let currentFiber = fiber;

        while (currentFiber) {
            const type = currentFiber.type;
            if (type) {
                const name = type.displayName || type.name || '';
                if (name === componentName) {
                    // Generate a unique selector for this element
                    let selector = element.tagName.toLowerCase();
                    if (element.id) {
                        selector = '#' + element.id;
                    } else if (element.className) {
                        const classes = element.className.split(' ').filter(c => c).join('.');
                        if (classes) selector += '.' + classes;
                    }
                    found.push({
                        selector: selector,
                        componentName: name,
                        props: currentFiber.memoizedProps ? Object.keys(currentFiber.memoizedProps).filter(k => !k.startsWith('__')) : []
                    });
                    break;
                }
            }
            currentFiber = currentFiber.return;
        }
    }

    if (found.length === 0) {
        return { success: false, error: 'Component not found: ' + componentName };
    }

    return { success: true, components: found };
    """

    result = instance.driver.execute_script(script, component_name)

    if isinstance(result, dict):
        if result.get("success"):
            return BrowserResponse(success=True, result=result.get("components", []))
        return BrowserResponse(
            success=False, error=result.get("error", "Unknown error")
        )

    return BrowserResponse(success=True, result=result)


async def browser_react_get_fiber_tree_tool(
    manager: ChromeManager,
    selector: str,
    max_depth: int = 5,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Get React fiber tree structure.

    Args:
        manager: Chrome manager instance
        selector: CSS selector for target element
        max_depth: Maximum tree depth to traverse
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with fiber tree structure
    """
    logger.debug(f"Getting React fiber tree for: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) {
        return { success: false, error: 'Element not found' };
    }

    const reactKey = Object.keys(element).find(key => key.startsWith('__reactFiber'));
    if (!reactKey) {
        return { success: false, error: 'React fiber not found' };
    }

    const maxDepth = arguments[1];

    function getFiberInfo(fiber, depth = 0) {
        if (!fiber || depth >= maxDepth) return null;

        const type = fiber.type;
        const typeName = type ? (type.displayName || type.name || type) : 'Unknown';

        return {
            type: String(typeName),
            props: fiber.memoizedProps ? Object.keys(fiber.memoizedProps).filter(k => !k.startsWith('__')) : [],
            hasState: !!fiber.memoizedState,
            parent: fiber.return ? getFiberInfo(fiber.return, depth + 1) : null
        };
    }

    const tree = getFiberInfo(element[reactKey]);
    return { success: true, tree: tree };
    """

    result = instance.driver.execute_script(script, selector, max_depth)

    if isinstance(result, dict):
        if result.get("success"):
            return BrowserResponse(success=True, result=result.get("tree"))
        return BrowserResponse(
            success=False, error=result.get("error", "Unknown error")
        )

    return BrowserResponse(success=True, result=result)
