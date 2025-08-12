"""Simple tab injector that actually works."""

import threading
import time
from pathlib import Path

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver


class SimpleTabInjector:
    """Monitors for new tabs and injects anti-detection script."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.monitoring = False
        self.monitor_thread = None
        self.known_handles = set(driver.window_handles)
        self._load_script()

    def _load_script(self):
        """Load the anti-detection script."""
        script_path = Path(__file__).parent.parent / "scripts" / "complete-antidetect.js"
        if script_path.exists():
            with script_path.open("r", encoding="utf-8") as f:
                self.antidetect_script = f.read()
        else:
            logger.error(f"Anti-detect script not found at {script_path}")
            self.antidetect_script = None

    def start_monitoring(self):
        """Start monitoring for new tabs."""
        if self.monitoring or not self.antidetect_script:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.debug("Simple tab monitoring started")

    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.debug("Simple tab monitoring stopped")

    def _inject_via_cdp(self, handle: str) -> bool:
        """Inject script via CDP for future navigation."""
        try:
            # Enable Page domain for this specific tab context
            self.driver.execute_cdp_cmd("Page.enable", {})  # type: ignore[attr-defined]
            # Enable Runtime domain as well
            self.driver.execute_cdp_cmd("Runtime.enable", {})  # type: ignore[attr-defined]

            # Try to inject immediately into current context
            try:
                self.driver.execute_cdp_cmd(  # type: ignore[attr-defined]
                    "Runtime.evaluate",
                    {"expression": self.antidetect_script, "silent": True, "returnByValue": False, "awaitPromise": False},
                )
                logger.debug("Injected via Runtime.evaluate")
            except Exception:
                logger.debug("Runtime.evaluate failed, will retry with script injection")

            # Add script to evaluate on EVERY new document in this tab
            result = self.driver.execute_cdp_cmd(  # type: ignore[attr-defined]
                "Page.addScriptToEvaluateOnNewDocument",
                {  # type: ignore[attr-defined]
                    "source": self.antidetect_script,
                    "worldName": "",  # Main world
                    "runImmediately": True,  # Run on existing contexts too!
                },
            )
            identifier = result.get("identifier", "unknown")
            logger.info(f"CDP injection successful for tab {handle} with ID: {identifier}")
            return True
        except Exception as cdp_err:
            logger.error(f"CDP injection failed - webdriver will be detected: {cdp_err}")
            return False

    def _inject_via_script(self, handle: str) -> bool:
        """Inject script directly into document."""
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                # Try to inject immediately, even if document not ready
                self.driver.execute_script(self.antidetect_script)
                # Script execution is synchronous, no delay needed

                # Verify injection worked
                plugin_count = self.driver.execute_script("return navigator.plugins ? navigator.plugins.length : -1")

                if plugin_count > 0:
                    logger.info(f"Successfully injected into new tab {handle} on attempt {attempt + 1}, plugins: {plugin_count}")
                    return True
                if plugin_count == 0:
                    logger.debug(f"Attempt {attempt + 1}: Plugins exist but empty, retrying...")
                else:
                    logger.debug(f"Attempt {attempt + 1}: Document not ready, retrying...")

            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(0.05)  # Wait 50ms and retry
                else:
                    logger.error(f"Failed all injection attempts: {e}")
        return False

    def _inject_late(self, handle: str) -> bool:
        """Last ditch effort to inject after delay."""
        logger.warning(f"Standard injection failed for tab {handle}, trying after delay...")
        time.sleep(0.2)
        try:
            self.driver.execute_script(self.antidetect_script)
            plugin_count = self.driver.execute_script("return navigator.plugins ? navigator.plugins.length : -1")
            if plugin_count > 0:
                logger.info(f"Late injection successful for tab {handle}, plugins: {plugin_count}")
                return True
            logger.error(f"Failed to inject plugins into tab {handle} even after delay")
            return False
        except Exception as e:
            logger.error(f"Late injection also failed: {e}")
            return False

    def _process_new_tab(self, handle: str) -> None:
        """Process a single new tab."""
        try:
            # Switch to new tab IMMEDIATELY
            self.driver.switch_to.window(handle)
            logger.debug(f"Detected new tab: {handle}")

            # Try CDP injection first
            self._inject_via_cdp(handle)

            # Then try script injection
            if not self._inject_via_script(handle):
                # Last ditch effort
                self._inject_late(handle)

        except Exception as e:
            logger.error(f"Failed to process tab {handle}: {e}")

    def _monitor_loop(self):
        """Check for new tabs continuously."""
        while self.monitoring:
            try:
                current_handles = set(self.driver.window_handles)
                new_handles = current_handles - self.known_handles

                if new_handles:
                    for handle in new_handles:
                        self._process_new_tab(handle)

                    logger.debug("Injection complete, staying on current tab")
                    self.known_handles = current_handles

            except Exception as e:
                logger.debug(f"Monitor loop error: {e}")

            time.sleep(0.1)  # Check every 100ms - balance between responsiveness and CPU usage
