"""Tab management with anti-detection injection for new tabs."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver

if TYPE_CHECKING:
    from ..models.browser_properties import BrowserProperties
    from .properties_manager import PropertiesManager


class TabManager:
    """Manages browser tabs and ensures anti-detection is applied to all tabs."""

    def __init__(self, driver: WebDriver, instance_id: str | None = None, properties_manager: "PropertiesManager | None" = None):
        self.driver = driver
        self.instance_id = instance_id
        self.properties_manager = properties_manager
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
        current_handle = self.driver.current_window_handle

        # Inject browser properties if available
        if self.properties_manager and self.instance_id:
            props = self.properties_manager.get_tab_properties(self.instance_id, current_handle)
            props_script = props.to_injection_script()
            try:
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": props_script})
                logger.debug(f"Injected browser properties into tab {current_handle}")
            except Exception as e:
                logger.warning(f"Failed to inject browser properties into tab: {e}")

        # Inject anti-detect script
        if not self.antidetect_script:
            return

        # If we haven't injected into this tab yet
        if current_handle not in self._injected_tabs:
            try:
                # Inject via CDP for this specific tab
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": self.antidetect_script})
                self._injected_tabs.add(current_handle)
                logger.debug(f"Injected anti-detect into tab {current_handle}")
            except Exception as e:
                logger.warning(f"Failed to inject anti-detect into tab: {e}")

    def open_new_tab(self, url: str = None, properties: "BrowserProperties | None" = None):
        """Open a new tab with anti-detection and optionally custom properties."""
        # Open new tab
        self.driver.switch_to.new_window("tab")
        current_handle = self.driver.current_window_handle

        # Set custom properties for this tab if provided
        if properties and self.properties_manager and self.instance_id:
            self.properties_manager.set_tab_properties(self.instance_id, current_handle, properties)

        # Immediately inject anti-detection and properties
        self.ensure_antidetect_on_current_tab()

        # Navigate if URL provided
        if url:
            self.driver.get(url)

        return current_handle

    def switch_to_tab(self, window_handle: str):
        """Switch to a tab and ensure anti-detection is applied."""
        self.driver.switch_to.window(window_handle)
        self.ensure_antidetect_on_current_tab()

    def open_link_in_new_tab(self, url: str, properties: "BrowserProperties | None" = None):
        """Open a link in a new tab with anti-detection and optionally custom properties."""
        # Open new tab with properties
        return self.open_new_tab(url, properties)

    def set_tab_properties(self, tab_id: str, properties: "BrowserProperties | dict[str, Any]"):
        """Set properties for a specific tab."""
        if self.properties_manager and self.instance_id:
            self.properties_manager.set_tab_properties(self.instance_id, tab_id, properties)
            # If this is the current tab, reinject
            if self.driver.current_window_handle == tab_id:
                self.ensure_antidetect_on_current_tab()

    def cleanup_closed_tabs(self):
        """Remove closed tabs from the injected tabs set to prevent memory leak."""
        try:
            current_handles = set(self.driver.window_handles)
            self._injected_tabs = self._injected_tabs.intersection(current_handles)
        except Exception as e:
            logger.debug(f"Error cleaning up closed tabs: {e}")
