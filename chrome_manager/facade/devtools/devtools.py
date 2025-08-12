"""Chrome DevTools Protocol operations and network monitoring."""

import asyncio
import json
from typing import Any

from loguru import logger

from ...core.browser.instance import BrowserInstance
from ...models.browser import ConsoleEntry, NetworkEntry
from ...utils.exceptions import ChromeManagerError
from ..base import BaseController
from .config import get_device_config, list_available_devices


class DevToolsController(BaseController):
    """Controller for Chrome DevTools Protocol operations."""

    def __init__(self, instance: BrowserInstance):
        super().__init__(instance)
        self.instance = instance
        self.driver = instance.driver

    async def execute_cdp_command(self, command: str, params: dict | None = None) -> Any:
        """Execute a Chrome DevTools Protocol command.

        Args:
            command: CDP command name
            params: Command parameters

        Returns:
            Command result
        """
        if not self.driver:
            raise ChromeManagerError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                return self.driver.execute_cdp_cmd(command, params or {})  # type: ignore[attr-defined]
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.driver.execute_cdp_cmd, command, params or {})  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f"CDP command failed: {command}: {e}")
            raise ChromeManagerError(f"Failed to execute CDP command {command}: {e}") from e

    async def get_performance_metrics(self) -> Any:
        """Get browser performance metrics.

        Returns:
            Performance metrics (PerformanceMetrics object or dict)
        """
        return await self.instance.get_performance_metrics()

    async def get_network_logs(self) -> list[NetworkEntry]:
        """Get network activity logs.

        Returns:
            List of network entries
        """
        try:
            logs = self.driver.get_log("performance")
            entries = []

            for log in logs:
                try:
                    message = json.loads(log["message"])
                    if message.get("message", {}).get("method") == "Network.responseReceived":
                        response = message["message"]["params"]["response"]
                        entries.append(
                            NetworkEntry(  # type: ignore[call-arg]
                                url=response.get("url"),
                                method=response.get("requestMethod", "GET"),
                                status=response.get("status"),
                                type=response.get("mimeType"),
                                size=response.get("encodedDataLength"),
                                headers=response.get("headers", {}),
                            )
                        )
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse performance log entry: {e}")
                    logger.debug(f"Problematic log entry: {log}")
                except KeyError as e:
                    logger.warning(f"Missing expected key in log entry: {e}")
                    logger.debug(f"Log entry structure: {log}")
                except Exception as e:
                    logger.error(f"Unexpected error parsing log entry: {e}")
                    logger.debug(f"Log entry: {log}")

            return entries

        except Exception as e:
            logger.error(f"Failed to get network logs: {e}")
            return []

    async def get_console_logs(self) -> list[ConsoleEntry]:
        """Get browser console logs.

        Returns:
            List of console entries
        """
        return await self.instance.get_console_logs()

    async def enable_network_throttling(self, download_throughput: int = 1024 * 1024, upload_throughput: int = 1024 * 512, latency: int = 100) -> None:
        """Enable network throttling.

        Args:
            download_throughput: Download speed in bytes/second
            upload_throughput: Upload speed in bytes/second
            latency: Additional latency in milliseconds
        """
        await self.execute_cdp_command(
            "Network.emulateNetworkConditions",
            {"offline": False, "downloadThroughput": download_throughput, "uploadThroughput": upload_throughput, "latency": latency},
        )
        logger.info(f"Enabled network throttling: {download_throughput / 1024}KB/s down, " f"{upload_throughput / 1024}KB/s up, {latency}ms latency")

    async def disable_network_throttling(self) -> None:
        """Disable network throttling."""
        await self.execute_cdp_command("Network.emulateNetworkConditions", {"offline": False, "downloadThroughput": -1, "uploadThroughput": -1, "latency": 0})
        logger.info("Disabled network throttling")

    async def emulate_device(self, device_name: str) -> None:
        """Emulate a specific device.

        Args:
            device_name: Name of device to emulate

        Raises:
            ChromeManagerError: If device is unknown
        """
        device_config = get_device_config(device_name)
        if not device_config:
            available = list_available_devices()
            raise ChromeManagerError(f"Unknown device: {device_name}. Available devices: {', '.join(available)}")

        # Convert dataclass to dict for CDP
        device_params = {
            "width": device_config.width,
            "height": device_config.height,
            "deviceScaleFactor": device_config.deviceScaleFactor,
            "mobile": device_config.mobile,
        }

        await self.execute_cdp_command("Emulation.setDeviceMetricsOverride", device_params)
        await self.execute_cdp_command("Emulation.setUserAgentOverride", {"userAgent": device_config.userAgent})

        logger.info(f"Emulating device: {device_name}")

    async def clear_device_emulation(self) -> None:
        """Clear device emulation and return to normal mode."""
        await self.execute_cdp_command("Emulation.clearDeviceMetricsOverride")
        await self.execute_cdp_command("Emulation.clearUserAgentOverride")
        logger.info("Cleared device emulation")

    async def block_urls(self, patterns: list[str]) -> None:
        """Block URLs matching patterns.

        Args:
            patterns: List of URL patterns to block
        """
        await self.execute_cdp_command("Network.enable")
        await self.execute_cdp_command("Network.setBlockedURLs", {"urls": patterns})
        logger.info(f"Blocking URLs matching patterns: {patterns}")

    async def unblock_all_urls(self) -> None:
        """Remove all URL blocks."""
        await self.execute_cdp_command("Network.setBlockedURLs", {"urls": []})
        logger.info("Unblocked all URLs")

    async def set_geolocation(self, latitude: float, longitude: float, accuracy: int = 100) -> None:
        """Set browser geolocation.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            accuracy: Location accuracy in meters
        """
        await self.execute_cdp_command("Emulation.setGeolocationOverride", {"latitude": latitude, "longitude": longitude, "accuracy": accuracy})
        logger.info(f"Set geolocation to ({latitude}, {longitude}) with {accuracy}m accuracy")

    async def clear_geolocation(self) -> None:
        """Clear geolocation override."""
        await self.execute_cdp_command("Emulation.clearGeolocationOverride")
        logger.info("Cleared geolocation override")

    async def set_timezone(self, timezone_id: str) -> None:
        """Set browser timezone.

        Args:
            timezone_id: Timezone identifier (e.g., 'America/New_York')
        """
        await self.execute_cdp_command("Emulation.setTimezoneOverride", {"timezoneId": timezone_id})
        logger.info(f"Set timezone to {timezone_id}")

    async def set_locale(self, locale: str) -> None:
        """Set browser locale.

        Args:
            locale: Locale identifier (e.g., 'en-US')
        """
        await self.execute_cdp_command("Emulation.setLocaleOverride", {"locale": locale})
        logger.info(f"Set locale to {locale}")

    async def enable_request_interception(self) -> None:
        """Enable request interception for modification."""
        await self.execute_cdp_command("Fetch.enable")
        logger.info("Enabled request interception")

    async def disable_request_interception(self) -> None:
        """Disable request interception."""
        await self.execute_cdp_command("Fetch.disable")
        logger.info("Disabled request interception")

    def evaluate_performance_tree(self, metrics: dict, max_depth: int = 3) -> dict:
        """Recursively evaluate performance metrics tree.

        Args:
            metrics: Performance metrics dictionary
            max_depth: Maximum recursion depth

        Returns:
            Evaluated metrics tree
        """
        return self._evaluate_tree_recursive(metrics, 0, max_depth)

    def _evaluate_tree_recursive(self, obj: Any, current_depth: int, max_depth: int) -> Any:
        """Recursive helper for tree evaluation.

        Args:
            obj: Object to evaluate
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Evaluated object
        """
        if current_depth >= max_depth:
            return str(obj) if not isinstance(obj, str | int | float | bool | type(None)) else obj

        if isinstance(obj, dict):
            return {k: self._evaluate_tree_recursive(v, current_depth + 1, max_depth) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._evaluate_tree_recursive(item, current_depth + 1, max_depth) for item in obj]
        return obj
