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

    def _monitor_loop(self):
        """Check for new tabs every 100ms."""
        while self.monitoring:
            try:
                current_handles = set(self.driver.window_handles)
                new_handles = current_handles - self.known_handles

                if new_handles:
                    # Save current tab
                    original_handle = self.driver.current_window_handle

                    for handle in new_handles:
                        try:
                            # Switch to new tab
                            self.driver.switch_to.window(handle)

                            # First inject via CDP for this specific tab
                            try:
                                self.driver.execute_cdp_cmd(
                                    "Page.addScriptToEvaluateOnNewDocument",
                                    {  # type: ignore[attr-defined]
                                        "source": self.antidetect_script
                                    },
                                )
                            except Exception as cdp_err:
                                logger.debug(f"CDP injection failed: {cdp_err}")

                            # Wait for page to start loading
                            time.sleep(0.05)

                            # Try direct injection multiple times as page loads
                            for attempt in range(5):
                                try:
                                    # Check if document exists
                                    self.driver.execute_script("return document.readyState")
                                    # If we got here, document exists, inject
                                    self.driver.execute_script(self.antidetect_script)
                                    logger.debug(f"Successfully injected into new tab {handle} on attempt {attempt + 1}")
                                    break
                                except Exception:
                                    time.sleep(0.05)  # Wait a bit and retry

                        except Exception as e:
                            logger.debug(f"Failed to inject into tab {handle}: {e}")

                    # Switch back
                    try:
                        self.driver.switch_to.window(original_handle)
                    except Exception as e:
                        logger.debug(f"Could not switch back to original tab: {e}")

                    # Update known handles
                    self.known_handles = current_handles

            except Exception as e:
                logger.debug(f"Monitor loop error: {e}")

            time.sleep(0.02)  # Check every 20ms for faster response
