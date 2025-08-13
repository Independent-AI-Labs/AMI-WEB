"""Browser monitoring - console, network, performance."""

import json
from datetime import datetime
from typing import Any

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver

from ...models.browser import ConsoleEntry, NetworkEntry, PerformanceMetrics, TabInfo


class BrowserMonitor:
    """Monitors browser console, network, and performance."""

    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self._console_logs: list[ConsoleEntry] = []
        self._network_logs: list[NetworkEntry] = []
        self.last_activity = datetime.now()

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    async def setup_logging(self, driver: WebDriver):
        """Setup CDP logging for console and network."""
        try:
            # Enable console and network logging via CDP
            driver.execute_cdp_cmd("Console.enable", {})  # type: ignore[attr-defined]
            driver.execute_cdp_cmd("Network.enable", {})  # type: ignore[attr-defined]
            driver.execute_cdp_cmd("Performance.enable", {})  # type: ignore[attr-defined]
            logger.debug(f"Logging enabled for instance {self.instance_id}")
        except Exception as e:
            logger.warning(f"Failed to setup logging: {e}")

    async def get_console_logs(self, driver: WebDriver) -> list[ConsoleEntry]:
        """Get console logs from the browser."""
        if not driver:
            return self._console_logs

        try:
            logs = driver.get_log("browser")  # type: ignore[attr-defined]
            for log in logs:
                entry = ConsoleEntry(
                    level=log.get("level", "INFO"), message=log.get("message", ""), timestamp=log.get("timestamp", 0), source=log.get("source", "console")
                )
                self._console_logs.append(entry)
        except Exception as e:
            logger.debug(f"Failed to get console logs: {e}")

        return self._console_logs

    async def get_network_logs(self, driver: WebDriver) -> list[NetworkEntry]:
        """Get network logs from the browser."""
        if not driver:
            return self._network_logs

        try:
            logs = driver.get_log("performance")  # type: ignore[attr-defined]
            for log in logs:
                message = json.loads(log["message"])
                if message.get("message", {}).get("method", "").startswith("Network."):
                    # Extract URL from params if available
                    params = message["message"].get("params", {})
                    url = params.get("request", {}).get("url", "") if "request" in params else ""
                    entry = NetworkEntry(timestamp=datetime.fromtimestamp(log.get("timestamp", 0) / 1000), method=message["message"]["method"], url=url)
                    self._network_logs.append(entry)
        except Exception as e:
            logger.debug(f"Failed to get network logs: {e}")

        return self._network_logs

    async def get_performance_metrics(self, driver: WebDriver) -> PerformanceMetrics:
        """Get performance metrics from the browser."""
        if not driver:
            return PerformanceMetrics(timestamp=datetime.now(), dom_content_loaded=0, load_complete=0)

        try:
            # Get navigation timing
            nav_timing = driver.execute_script(
                """
                var timing = window.performance.timing;
                return {
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart,
                    firstPaint: 0,
                    firstContentfulPaint: 0
                };
            """
            )

            # Get paint timing
            paint_timing = driver.execute_script(
                """
                var entries = window.performance.getEntriesByType('paint');
                var result = {};
                entries.forEach(function(entry) {
                    if (entry.name === 'first-paint') {
                        result.firstPaint = entry.startTime;
                    } else if (entry.name === 'first-contentful-paint') {
                        result.firstContentfulPaint = entry.startTime;
                    }
                });
                return result;
            """
            )

            # Memory usage tracking removed - not currently used

            return PerformanceMetrics(
                timestamp=datetime.now(),
                dom_content_loaded=nav_timing.get("domContentLoaded", 0),
                load_complete=nav_timing.get("loadComplete", 0),
                first_paint=paint_timing.get("firstPaint", nav_timing.get("firstPaint", 0)),
                first_contentful_paint=paint_timing.get("firstContentfulPaint", nav_timing.get("firstContentfulPaint", 0)),
            )
        except Exception as e:
            logger.warning(f"Failed to get performance metrics: {e}")
            return PerformanceMetrics(timestamp=datetime.now(), dom_content_loaded=0, load_complete=0)

    async def get_tabs(self, driver: WebDriver) -> list[TabInfo]:
        """Get information about all open tabs."""
        if not driver:
            return []

        tabs = []
        current_handle = driver.current_window_handle

        try:
            for idx, handle in enumerate(driver.window_handles):
                driver.switch_to.window(handle)
                tabs.append(TabInfo(id=handle, title=driver.title, url=driver.current_url, active=handle == current_handle, index=idx, window_handle=handle))

            # Switch back to original tab
            driver.switch_to.window(current_handle)
        except Exception as e:
            logger.warning(f"Failed to get tab info: {e}")

        return tabs

    async def health_check(self, driver: WebDriver) -> dict[str, Any]:
        """Perform a health check on the browser."""
        health = {"alive": False, "responsive": False, "tabs_count": 0, "memory_usage": 0, "last_activity": self.last_activity.isoformat()}

        if not driver:
            return health

        try:
            # Check if driver is alive
            _ = driver.current_url
            health["alive"] = True

            # Check if responsive
            driver.execute_script("return document.readyState")
            health["responsive"] = True

            # Count tabs
            health["tabs_count"] = len(driver.window_handles)

            # Get memory usage (not available in current metrics)
            health["memory_usage"] = 0

        except Exception as e:
            logger.debug(f"Health check failed: {e}")

        return health

    def clear_logs(self):
        """Clear all stored logs."""
        self._console_logs.clear()
        self._network_logs.clear()
        logger.debug(f"Cleared logs for instance {self.instance_id}")
