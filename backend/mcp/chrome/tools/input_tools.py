"""Input tools for Chrome MCP server."""

from typing import Any

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.input.forms import FormsController
from browser.backend.facade.input.keyboard import KeyboardController
from browser.backend.facade.input.mouse import MouseController
from browser.backend.facade.navigation.scroller import Scroller
from loguru import logger


async def browser_click_tool(manager: ChromeManager, selector: str, button: str = "left", click_count: int = 1) -> dict[str, Any]:
    """Click on an element."""
    logger.debug(f"Clicking element: {selector} with button={button}, count={click_count}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    mouse = MouseController(instance)
    await mouse.click(selector)

    return {"success": True, "status": "clicked"}


async def browser_type_tool(manager: ChromeManager, selector: str, text: str, clear: bool = False, delay: float = 0) -> dict[str, Any]:
    """Type text into an element."""
    logger.debug(f"Typing into element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    keyboard = KeyboardController(instance)

    if clear:
        # Clear the field first if requested
        await keyboard.clear(selector)

    await keyboard.type_text(selector, text, delay=delay)

    return {"success": True, "status": "typed"}


async def browser_select_tool(
    manager: ChromeManager, selector: str, value: str | None = None, index: int | None = None, label: str | None = None
) -> dict[str, Any]:
    """Select an option from a dropdown."""
    logger.debug(f"Selecting from dropdown: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    forms = FormsController(instance)

    if value:
        await forms.select_by_value(selector, value)
    elif index is not None:
        await forms.select_by_index(selector, index)
    elif label:
        await forms.select_by_text(selector, label)
    else:
        return {"success": False, "error": "Must provide value, index, or label"}

    return {"success": True, "status": "selected"}


async def browser_hover_tool(manager: ChromeManager, selector: str) -> dict[str, Any]:
    """Hover over an element."""
    logger.debug(f"Hovering over element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    mouse = MouseController(instance)
    await mouse.hover(selector)

    return {"success": True, "status": "hovered"}


async def browser_scroll_tool(manager: ChromeManager, direction: str = "down", amount: int = 100, selector: str | None = None) -> dict[str, Any]:
    """Scroll page or element."""
    logger.debug(f"Scrolling {direction} by {amount}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    scroller = Scroller(instance)

    if direction == "down":
        await scroller.scroll_down(amount=amount, element=selector)
    elif direction == "up":
        await scroller.scroll_up(amount=amount, element=selector)
    else:
        return {"success": False, "error": f"Invalid direction: {direction}"}

    return {"success": True, "status": "scrolled"}


async def browser_press_tool(manager: ChromeManager, key: str, modifiers: list[str] | None = None) -> dict[str, Any]:
    """Press keyboard keys."""
    logger.debug(f"Pressing key: {key} with modifiers: {modifiers}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    keyboard = KeyboardController(instance)

    # Send the key press
    await keyboard.press_key(key, modifiers=modifiers or [])

    return {"success": True, "status": "key_pressed"}
