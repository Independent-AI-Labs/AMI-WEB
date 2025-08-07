"""Helper functions for browser automation with anti-detection."""

from pathlib import Path

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver


def inject_antidetect_on_tab_switch(driver: WebDriver) -> None:
    """
    Manually inject anti-detection scripts when switching tabs.
    Call this after switching to a new tab/window.
    """
    scripts_dir = Path(__file__).parent.parent / "scripts"
    script_path = scripts_dir / "complete-antidetect.js"

    if not script_path.exists():
        logger.error(f"Complete anti-detect script not found at {script_path}")
        return

    try:
        with script_path.open("r", encoding="utf-8") as f:
            script_content = f.read()

        # Inject directly into current context
        driver.execute_script(script_content)
        logger.debug("Anti-detection script injected on tab switch")
    except Exception as e:
        logger.warning(f"Failed to inject anti-detection on tab switch: {e}")


def open_new_tab_with_antidetect(driver: WebDriver, url: str = None) -> None:
    """
    Open a new tab and ensure anti-detection is applied.

    Args:
        driver: Selenium WebDriver instance
        url: Optional URL to navigate to
    """
    # Open new tab
    driver.switch_to.new_window("tab")

    # Inject anti-detection immediately
    inject_antidetect_on_tab_switch(driver)

    # Navigate if URL provided
    if url:
        driver.get(url)
        # Re-inject after navigation to be sure
        inject_antidetect_on_tab_switch(driver)
