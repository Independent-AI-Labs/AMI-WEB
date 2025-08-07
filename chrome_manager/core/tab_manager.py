"""Tab management with anti-detection injection for new tabs."""

from pathlib import Path

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver


class TabManager:
    """Manages browser tabs and ensures anti-detection is applied to all tabs."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self._load_antidetect_script()
        self._injected_tabs: set[str] = set()

    def _load_antidetect_script(self):
        """Load the anti-detection script content."""
        script_path = Path(__file__).parent.parent / "scripts" / "complete-antidetect.js"
        if script_path.exists():
            with script_path.open("r", encoding="utf-8") as f:
                self.antidetect_script = f.read()
        else:
            logger.error(f"Anti-detect script not found at {script_path}")
            self.antidetect_script = None

    def ensure_antidetect_on_current_tab(self):
        """Ensure anti-detection is applied to the current tab."""
        if not self.antidetect_script:
            return

        current_handle = self.driver.current_window_handle

        # If we haven't injected into this tab yet
        if current_handle not in self._injected_tabs:
            try:
                # Inject via CDP for this specific tab
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": self.antidetect_script})
                self._injected_tabs.add(current_handle)
                logger.debug(f"Injected anti-detect into tab {current_handle}")
            except Exception as e:
                logger.warning(f"Failed to inject anti-detect into tab: {e}")

    def open_new_tab(self, url: str = None):
        """Open a new tab with anti-detection pre-applied."""
        # Open new tab
        self.driver.switch_to.new_window("tab")

        # Immediately inject anti-detection
        self.ensure_antidetect_on_current_tab()

        # Navigate if URL provided
        if url:
            self.driver.get(url)

    def switch_to_tab(self, window_handle: str):
        """Switch to a tab and ensure anti-detection is applied."""
        self.driver.switch_to.window(window_handle)
        self.ensure_antidetect_on_current_tab()

    def open_link_in_new_tab(self, url: str):
        """Open a link in a new tab with anti-detection."""
        # Open new tab properly
        self.open_new_tab(url)

        # Return the new tab handle
        return self.driver.current_window_handle
