"""Screenshot tools for Chrome MCP server."""

import base64
from datetime import datetime
from pathlib import Path

from loguru import logger
from selenium.webdriver.common.by import By

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.media.screenshot import ScreenshotController
from browser.backend.mcp.chrome.response import BrowserResponse


async def browser_screenshot_tool(
    manager: ChromeManager,
    full_page: bool = False,
    save_to_disk: bool = True,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Take a screenshot of the page."""
    logger.debug(
        f"Taking screenshot: full_page={full_page}, save_to_disk={save_to_disk}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    screenshot_controller = ScreenshotController(instance)

    if save_to_disk:
        # Save to configured screenshot directory
        screenshot_dir = Path(
            manager.config.get("backend.storage.screenshot_dir", "./data/screenshots")
        )
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"screenshot_{timestamp}.png"
        filepath = screenshot_dir / filename

        # Save screenshot
        saved_path = await screenshot_controller.save_screenshot(
            str(filepath), full_page=full_page
        )

        return BrowserResponse(
            success=True,
            data={
                "filepath": saved_path,
                "filename": filename,
                "format": "png",
                "saved": True,
            },
        )

    # Return base64 encoded
    if full_page:
        screenshot_bytes = await screenshot_controller.capture_full_page()
    else:
        screenshot_bytes = await screenshot_controller.capture_viewport()

    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    return BrowserResponse(
        success=True, screenshot=screenshot_base64, data={"format": "base64"}
    )


async def browser_element_screenshot_tool(
    manager: ChromeManager,
    selector: str,
    save_to_disk: bool = True,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Take a screenshot of an element."""
    logger.debug(
        f"Taking element screenshot: {selector}, save_to_disk={save_to_disk}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    screenshot_controller = ScreenshotController(instance)

    if save_to_disk:
        # Save to configured screenshot directory
        screenshot_dir = Path(
            manager.config.get("backend.storage.screenshot_dir", "./data/screenshots")
        )
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        # Sanitize selector for filename
        safe_selector = (
            selector.replace(" ", "_")
            .replace(".", "")
            .replace("#", "")
            .replace(">", "")[:50]
        )
        filename = f"element_{safe_selector}_{timestamp}.png"
        filepath = screenshot_dir / filename

        # Save screenshot
        saved_path = await screenshot_controller.save_screenshot(
            str(filepath), selector=selector
        )

        return BrowserResponse(
            success=True,
            data={
                "filepath": saved_path,
                "filename": filename,
                "format": "png",
                "saved": True,
            },
        )

    # Return base64 encoded
    element = instance.driver.find_element(By.CSS_SELECTOR, selector)
    screenshot_bytes = element.screenshot_as_png
    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    return BrowserResponse(
        success=True, screenshot=screenshot_base64, data={"format": "base64"}
    )
