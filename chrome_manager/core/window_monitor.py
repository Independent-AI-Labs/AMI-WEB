"""Monitor for new windows and inject anti-detection immediately."""

import threading
import time
from pathlib import Path

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver


class WindowMonitor:
    """Monitors for new browser windows and injects anti-detection."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.known_windows = set(driver.window_handles)
        self.monitoring = False
        self.monitor_thread = None
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
        """Start monitoring for new windows."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.debug("Window monitoring started")

    def stop_monitoring(self):
        """Stop monitoring for new windows."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.debug("Window monitoring stopped")

    def _monitor_loop(self):
        """Monitor loop that runs in a separate thread."""
        while self.monitoring:
            try:
                current_windows = set(self.driver.window_handles)
                new_windows = current_windows - self.known_windows

                if new_windows:
                    for window in new_windows:
                        self._inject_into_window(window)

                    self.known_windows = current_windows

            except Exception as e:
                logger.debug(f"Monitor loop error: {e}")

            time.sleep(0.1)  # Check every 100ms

    def _inject_into_window(self, window_handle: str):
        """Inject anti-detection into a specific window."""
        if not self.antidetect_script:
            return

        try:
            # Save current window
            original_window = self.driver.current_window_handle

            # Switch to new window
            self.driver.switch_to.window(window_handle)

            # Inject immediately via CDP for this window
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": self.antidetect_script})  # type: ignore[attr-defined]

            # Also try direct injection
            try:
                self.driver.execute_script(self.antidetect_script)
            except Exception as e:
                logger.debug(f"Direct injection failed (expected if page not ready): {e}")

            logger.debug(f"Injected anti-detect into new window {window_handle}")

            # Switch back
            self.driver.switch_to.window(original_window)

        except Exception as e:
            logger.debug(f"Failed to inject into window {window_handle}: {e}")
