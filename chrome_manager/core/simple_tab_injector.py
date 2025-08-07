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
        """Check for new tabs continuously."""
        while self.monitoring:
            try:
                current_handles = set(self.driver.window_handles)
                new_handles = current_handles - self.known_handles

                if new_handles:
                    # Save current tab
                    original_handle = self.driver.current_window_handle

                    for handle in new_handles:
                        try:
                            # Switch to new tab IMMEDIATELY
                            self.driver.switch_to.window(handle)
                            logger.debug(f"Detected new tab: {handle}")

                            # First, try CDP injection for future navigation
                            try:
                                self.driver.execute_cdp_cmd(
                                    "Page.addScriptToEvaluateOnNewDocument",
                                    {  # type: ignore[attr-defined]
                                        "source": self.antidetect_script
                                    },
                                )
                                logger.debug(f"CDP injection successful for tab {handle}")
                            except Exception as cdp_err:
                                logger.debug(f"CDP injection failed: {cdp_err}")

                            # Aggressively inject into current document
                            injection_success = False
                            for attempt in range(20):  # Even more attempts
                                try:
                                    # Try to inject immediately, even if document not ready
                                    self.driver.execute_script(self.antidetect_script)

                                    # Small delay to let script execute
                                    time.sleep(0.01)

                                    # Verify injection worked
                                    plugin_count = self.driver.execute_script("return navigator.plugins ? navigator.plugins.length : -1")

                                    if plugin_count > 0:
                                        logger.info(f"Successfully injected into new tab {handle} on attempt {attempt + 1}, plugins: {plugin_count}")
                                        injection_success = True
                                        break
                                    elif plugin_count == 0:
                                        # Plugins exist but empty, script may not have run yet
                                        logger.debug(f"Attempt {attempt + 1}: Plugins exist but empty, retrying...")
                                    else:
                                        # navigator.plugins doesn't exist yet
                                        logger.debug(f"Attempt {attempt + 1}: Document not ready, retrying...")

                                except Exception as e:
                                    # Document probably not ready yet
                                    if attempt < 19:
                                        time.sleep(0.01)  # Wait 10ms and retry
                                    else:
                                        logger.error(f"Failed all injection attempts: {e}")

                            if not injection_success:
                                # Last ditch effort - wait for navigation and inject
                                logger.warning(f"Standard injection failed for tab {handle}, trying after delay...")
                                time.sleep(0.5)
                                try:
                                    self.driver.execute_script(self.antidetect_script)
                                    plugin_count = self.driver.execute_script("return navigator.plugins ? navigator.plugins.length : -1")
                                    if plugin_count > 0:
                                        logger.info(f"Late injection successful for tab {handle}, plugins: {plugin_count}")
                                    else:
                                        logger.error(f"Failed to inject plugins into tab {handle} even after delay")
                                except Exception as e:
                                    logger.error(f"Late injection also failed: {e}")

                        except Exception as e:
                            logger.error(f"Failed to process tab {handle}: {e}")

                    # Switch back
                    try:
                        self.driver.switch_to.window(original_handle)
                    except Exception as e:
                        logger.debug(f"Could not switch back to original tab: {e}")

                    # Update known handles
                    self.known_handles = current_handles

            except Exception as e:
                logger.debug(f"Monitor loop error: {e}")

            time.sleep(0.005)  # Check every 5ms for ultra-fast response
