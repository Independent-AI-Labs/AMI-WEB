"""Input tools for Chrome MCP server."""

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.input.forms import FormsController
from browser.backend.facade.input.keyboard import KeyboardController
from browser.backend.facade.input.mouse import MouseController
from browser.backend.facade.navigation.scroller import Scroller
from browser.backend.mcp.chrome.response import BrowserResponse


async def browser_click_tool(
    manager: ChromeManager,
    selector: str,
    button: str = "left",
    click_count: int = 1,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Click on an element."""
    logger.debug(
        f"Clicking element: {selector} with button={button}, count={click_count}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    mouse = MouseController(instance)
    await mouse.click(selector)

    return BrowserResponse(success=True, data={"status": "clicked"})


async def browser_type_tool(
    manager: ChromeManager,
    selector: str,
    text: str,
    clear: bool = False,
    delay: float = 0,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Type text into an element."""
    logger.debug(f"Typing into element: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    keyboard = KeyboardController(instance)

    await keyboard.type_text(selector, text, clear=clear, delay=int(delay))

    return BrowserResponse(success=True, data={"status": "typed"})


async def browser_select_tool(
    manager: ChromeManager,
    selector: str,
    value: str | None = None,
    index: int | None = None,
    label: str | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Select an option from a dropdown."""
    logger.debug(f"Selecting from dropdown: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    forms = FormsController(instance)

    if value:
        await forms.select_option(selector, value=value)
    elif index is not None:
        await forms.select_option(selector, index=index)
    elif label:
        await forms.select_option(selector, text=label)
    else:
        return BrowserResponse(
            success=False, error="Must provide value, index, or label"
        )

    return BrowserResponse(success=True, data={"status": "selected"})


async def browser_hover_tool(
    manager: ChromeManager, selector: str, instance_id: str | None = None
) -> BrowserResponse:
    """Hover over an element."""
    logger.debug(f"Hovering over element: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    mouse = MouseController(instance)
    await mouse.hover(selector)

    return BrowserResponse(success=True, data={"status": "hovered"})


async def browser_scroll_tool(
    manager: ChromeManager,
    direction: str = "down",
    amount: int = 100,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Scroll page or element."""
    logger.debug(f"Scrolling {direction} by {amount}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    scroller = Scroller(instance)

    if direction == "down":
        await scroller.scroll_by(y=amount)
    elif direction == "up":
        await scroller.scroll_by(y=-amount)
    else:
        return BrowserResponse(success=False, error=f"Invalid direction: {direction}")

    return BrowserResponse(success=True, data={"status": "scrolled"})


async def browser_press_tool(
    manager: ChromeManager,
    key: str,
    modifiers: list[str | None] | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Press keyboard keys."""
    logger.debug(
        f"Pressing key: {key} with modifiers: {modifiers}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    keyboard = KeyboardController(instance)

    # Send the key press
    await keyboard.press_key(key)

    return BrowserResponse(success=True, data={"status": "key_pressed"})
