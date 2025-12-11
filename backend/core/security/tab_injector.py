"""Tab injector using CDP events - NO POLLING."""

from base.scripts.env.paths import setup_imports


ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from loguru import logger  # noqa: E402
from selenium.webdriver.remote.webdriver import WebDriver  # noqa: E402


class SimpleTabInjector:
    """Injects anti-detection script into tabs using CDP events."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.antidetect_script: str | None = None
        self._injected_tabs: set[str] = set()
        self._load_script()
        self._setup_cdp_injection()

    def _load_script(self) -> None:
        """Load the anti-detection script."""
        # Path: backend/core/security -> web/scripts
        script_path = MODULE_ROOT / "web" / "scripts" / "complete-antidetect.js"
        if script_path.exists():
            with script_path.open("r", encoding="utf-8") as f:
                self.antidetect_script = f.read()
                logger.info(f"Loaded anti-detect script from {script_path}")
        else:
            logger.error(f"Anti-detect script not found at {script_path}")

    def _setup_cdp_injection(self) -> None:
        """Setup CDP to inject script on all new documents automatically."""
        if not self.antidetect_script:
            logger.error("Cannot setup CDP injection - no script loaded")
            return

        try:
            # Enable Page domain
            self.driver.execute_cdp_cmd("Page.enable", {})

            # This injects the script into EVERY new document/frame automatically
            # No polling needed - CDP handles it for us!
            result = self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": self.antidetect_script,
                    "worldName": "",  # Main world
                    "runImmediately": True,  # Also inject into existing pages
                },
            )

            script_id = result.get("identifier", "unknown")
            logger.info(f"CDP injection setup complete with script ID: {script_id}")
            logger.info("Script will be injected into ALL new tabs/documents automatically - NO POLLING")

        except Exception as e:
            logger.error(f"Failed to setup CDP injection: {e}")

    def inject_into_current_tab(self) -> bool:
        """Manually inject into current tab if needed."""
        if not self.antidetect_script:
            return False

        try:
            current_handle = self.driver.current_window_handle

            # Check if already injected
            if current_handle in self._injected_tabs:
                logger.debug(f"Tab {current_handle} already injected")
                return True

            # Inject directly via execute_script for immediate effect
            self.driver.execute_script(self.antidetect_script)

            # Verify injection worked
            plugin_count = self.driver.execute_script("return navigator.plugins ? navigator.plugins.length : -1")

            if plugin_count > 0:
                self._injected_tabs.add(current_handle)
                logger.info(f"Successfully injected into tab {current_handle}, plugins: {plugin_count}")
                return True
            logger.warning(f"Injection may have failed for tab {current_handle}, plugins: {plugin_count}")
            return False

        except Exception as e:
            logger.error(f"Failed to inject into current tab: {e}")
            return False

    def cleanup_closed_tabs(self) -> None:
        """Remove closed tabs from tracking."""
        try:
            current_handles = set(self.driver.window_handles)
            self._injected_tabs = self._injected_tabs.intersection(current_handles)
        except Exception as e:
            logger.debug(f"Error cleaning up closed tabs: {e}")

    # These methods do nothing now since we use CDP events
    def start_monitoring(self) -> None:
        """No-op - CDP handles everything."""
        logger.debug("start_monitoring called but not needed - using CDP events")

    def stop_monitoring(self) -> None:
        """No-op - CDP handles everything."""
        logger.debug("stop_monitoring called but not needed - using CDP events")
