"""Tab management with anti-detection injection for new tabs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from loguru import logger  # noqa: E402
from selenium.webdriver.remote.webdriver import WebDriver  # noqa: E402

from browser.backend.core.browser.properties_manager import PropertiesManager  # noqa: E402
from browser.backend.models.browser_properties import BrowserProperties  # noqa: E402

if TYPE_CHECKING:
    pass


class TabManager:
    """Manages browser tabs and ensures anti-detection is applied to all tabs."""

    def __init__(
        self,
        driver: WebDriver,
        instance_id: str | None = None,
        properties_manager: PropertiesManager | None = None,
    ):
        self.driver = driver
        self.instance_id = instance_id
        self.properties_manager = properties_manager
        self._load_antidetect_script()
        self._injected_tabs: set[str] = set()

    def _load_antidetect_script(self) -> None:
        """Load the anti-detection script content."""
        # Path: backend/core/browser -> web/scripts
        script_path = MODULE_ROOT / "web" / "scripts" / "complete-antidetect.js"
        if script_path.exists():
            with script_path.open("r", encoding="utf-8") as f:
                self.antidetect_script: str | None = f.read()
        else:
            logger.error(f"Anti-detect script not found at {script_path}")
            self.antidetect_script = None

    def ensure_antidetect_on_current_tab(self) -> None:
        """Ensure anti-detection is applied to the current tab."""
        # Cleanup closed tabs automatically to prevent memory leak
        self.cleanup_closed_tabs()
        current_handle: str = str(self.driver.current_window_handle)

        # Inject browser properties if available
        if self.properties_manager and self.instance_id:
            props = self.properties_manager.get_tab_properties(self.instance_id, current_handle)
            props_script = props.to_injection_script()
            try:
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": props_script})
                logger.debug(f"Injected browser properties into tab {current_handle}")
            except Exception as e:
                logger.error(f"Failed to inject browser properties into tab {current_handle}: {e}")

        # Inject anti-detect script
        if not self.antidetect_script:
            return

        # If we haven't injected into this tab yet
        if current_handle not in self._injected_tabs:
            try:
                # Inject via CDP for this specific tab
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {"source": self.antidetect_script},
                )
                self._injected_tabs.add(current_handle)
                logger.debug(f"Injected anti-detect into tab {current_handle}")
            except Exception as e:
                logger.error(f"Failed to inject anti-detect into tab {current_handle}: {e}")

    def open_new_tab(self, url: str | None = None, properties: BrowserProperties | None = None) -> str:
        """Open a new tab with anti-detection and optionally custom properties."""
        # Open new tab
        self.driver.switch_to.new_window("tab")
        current_handle: str = str(self.driver.current_window_handle)

        # Set custom properties for this tab if provided
        if properties and self.properties_manager and self.instance_id:
            self.properties_manager.set_tab_properties(self.instance_id, current_handle, properties)

        # Immediately inject anti-detection and properties
        self.ensure_antidetect_on_current_tab()

        # Navigate if URL provided
        if url:
            self.driver.get(url)

        return current_handle

    def switch_to_tab(self, window_handle: str) -> None:
        """Switch to a tab and ensure anti-detection is applied."""
        # Cleanup before switching
        self.cleanup_closed_tabs()
        self.driver.switch_to.window(window_handle)
        self.ensure_antidetect_on_current_tab()

    def open_link_in_new_tab(self, url: str, properties: BrowserProperties | None = None) -> str:
        """Open a link in a new tab with anti-detection and optionally custom properties."""
        # Open new tab with properties
        return self.open_new_tab(url, properties)

    def set_tab_properties(self, tab_id: str, properties: BrowserProperties | dict[str, Any]) -> None:
        """Set properties for a specific tab."""
        if self.properties_manager and self.instance_id:
            self.properties_manager.set_tab_properties(self.instance_id, tab_id, properties)
            # If this is the current tab, reinject
            if self.driver.current_window_handle == tab_id:
                self.ensure_antidetect_on_current_tab()

    def cleanup_closed_tabs(self) -> None:
        """Remove closed tabs from the injected tabs set to prevent memory leak."""
        try:
            current_handles = set(self.driver.window_handles)
            self._injected_tabs = self._injected_tabs.intersection(current_handles)
        except Exception as e:
            logger.debug(f"Error cleaning up closed tabs: {e}")
