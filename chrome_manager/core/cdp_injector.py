"""CDP-based injector for new tabs and windows."""

import json
import threading
import time
from pathlib import Path

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver


class CDPInjector:
    """Injects anti-detection into all new tabs via CDP."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.monitoring = False
        self.monitor_thread = None
        self.attached_targets: set[str] = set()
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
        """Start monitoring for new targets."""
        if self.monitoring or not self.antidetect_script:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.debug("CDP monitoring started")

    def stop_monitoring(self):
        """Stop monitoring for new targets."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.debug("CDP monitoring stopped")

    def _monitor_loop(self):
        """Monitor loop that runs in a separate thread."""
        while self.monitoring:
            try:
                # Get all targets
                targets = self.driver.execute_cdp_cmd("Target.getTargets", {})  # type: ignore[attr-defined]

                for target in targets.get("targetInfos", []):
                    target_id = target.get("targetId")
                    target_type = target.get("type")

                    # Only process page targets we haven't seen
                    if target_type == "page" and target_id not in self.attached_targets:
                        self._inject_into_target(target_id)
                        self.attached_targets.add(target_id)

            except Exception as e:
                logger.debug(f"CDP monitor loop error: {e}")

            time.sleep(0.2)  # Check every 200ms

    def _inject_into_target(self, target_id: str):
        """Inject anti-detection into a specific target."""
        try:
            # Attach to the target
            result = self.driver.execute_cdp_cmd("Target.attachToTarget", {"targetId": target_id, "flatten": True})  # type: ignore[attr-defined]

            session_id = result.get("sessionId")
            if not session_id:
                return

            # Send commands to the attached session
            # Enable Page domain on the target
            self._send_to_session(session_id, "Page.enable", {})

            # Add script to evaluate on new document
            self._send_to_session(session_id, "Page.addScriptToEvaluateOnNewDocument", {"source": self.antidetect_script})

            # Also try to inject immediately if page is loaded
            self._send_to_session(session_id, "Runtime.evaluate", {"expression": self.antidetect_script, "silent": True})

            logger.debug(f"Injected anti-detect into target {target_id}")

        except Exception as e:
            logger.debug(f"Failed to inject into target {target_id}: {e}")

    def _send_to_session(self, session_id: str, method: str, params: dict):
        """Send a CDP command to a specific session."""
        try:
            # Use Target.sendMessageToTarget to send to attached session
            message = json.dumps({"id": 1, "method": method, "params": params})

            self.driver.execute_cdp_cmd("Target.sendMessageToTarget", {"message": message, "sessionId": session_id})  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug(f"Failed to send {method} to session: {e}")
