import asyncio
import json
from datetime import datetime
from typing import Any

from loguru import logger

from ..core.instance import BrowserInstance
from ..models.browser import ConsoleEntry, NetworkEntry, PerformanceMetrics
from ..utils.exceptions import ChromeManagerError


class DevToolsController:
    def __init__(self, instance: BrowserInstance):
        self.instance = instance
        self.driver = instance.driver

    async def execute_cdp_command(self, command: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.driver:
            raise ChromeManagerError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.driver.execute_cdp_cmd, command, params)  # type: ignore[attr-defined]
            logger.debug(f"Executed CDP command: {command}")
            return result

        except Exception as e:
            logger.error(f"CDP command failed: {command}: {e}")
            raise ChromeManagerError(f"Failed to execute CDP command {command}: {e}") from e

    async def get_performance_metrics(self) -> PerformanceMetrics:
        return await self.instance.get_performance_metrics()

    async def get_network_logs(self) -> list[NetworkEntry]:
        try:
            await self.execute_cdp_command("Network.getAllCookies", {})

            performance_logs = self.driver.get_log("performance")  # type: ignore[attr-defined]

            entries = []
            for log_entry in performance_logs:
                try:
                    message = json.loads(log_entry["message"])

                    if message.get("message", {}).get("method") == "Network.responseReceived":
                        response = message["message"]["params"]["response"]
                        entries.append(
                            NetworkEntry(
                                timestamp=datetime.fromtimestamp(log_entry["timestamp"] / 1000),
                                method=response.get("requestMethod", "GET"),
                                url=response["url"],
                                status_code=response["status"],
                                response_time=None,
                                size=response.get("encodedDataLength"),
                                headers=response.get("headers", {}),
                            )
                        )
                except Exception:
                    logger.debug("Failed to parse performance log entry")
                    continue

            return entries

        except Exception as e:
            logger.warning(f"Failed to get network logs: {e}")
            return []

    async def get_console_logs(self) -> list[ConsoleEntry]:
        return await self.instance.get_console_logs()

    async def enable_network_throttling(self, download_throughput: int = 1024 * 1024, upload_throughput: int = 1024 * 512, latency: int = 100) -> None:
        await self.execute_cdp_command(
            "Network.emulateNetworkConditions",
            {"offline": False, "downloadThroughput": download_throughput, "uploadThroughput": upload_throughput, "latency": latency},
        )
        logger.info(f"Enabled network throttling: {download_throughput / 1024}KB/s down, {upload_throughput / 1024}KB/s up, {latency}ms latency")

    async def disable_network_throttling(self) -> None:
        await self.execute_cdp_command("Network.emulateNetworkConditions", {"offline": False, "downloadThroughput": -1, "uploadThroughput": -1, "latency": 0})
        logger.info("Disabled network throttling")

    async def emulate_device(self, device_name: str) -> None:
        devices = {
            "iPhone 12": {
                "width": 390,
                "height": 844,
                "deviceScaleFactor": 3,
                "mobile": True,
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            },
            "iPad": {
                "width": 768,
                "height": 1024,
                "deviceScaleFactor": 2,
                "mobile": True,
                "userAgent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            },
            "Pixel 5": {
                "width": 393,
                "height": 851,
                "deviceScaleFactor": 2.625,
                "mobile": True,
                "userAgent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36",
            },
        }

        device = devices.get(device_name)
        if not device:
            raise ChromeManagerError(f"Unknown device: {device_name}")

        await self.execute_cdp_command("Emulation.setDeviceMetricsOverride", device)

        await self.execute_cdp_command("Emulation.setUserAgentOverride", {"userAgent": device["userAgent"]})

        logger.info(f"Emulating device: {device_name}")

    async def clear_device_emulation(self) -> None:
        await self.execute_cdp_command("Emulation.clearDeviceMetricsOverride", {})
        logger.info("Cleared device emulation")

    async def get_page_resources(self) -> list[dict[str, Any]]:
        result = await self.execute_cdp_command("Page.getResourceTree", {})

        resources = []

        def extract_resources(frame):
            for resource in frame.get("resources", []):
                resources.append(
                    {
                        "url": resource["url"],
                        "type": resource["type"],
                        "mimeType": resource.get("mimeType"),
                        "failed": resource.get("failed", False),
                        "canceled": resource.get("canceled", False),
                    }
                )

            for child in frame.get("childFrames", []):
                extract_resources(child)

        extract_resources(result["frameTree"]["frame"])
        return resources

    async def block_urls(self, patterns: list[str]) -> None:
        await self.execute_cdp_command("Network.setBlockedURLs", {"urls": patterns})
        logger.info(f"Blocked URL patterns: {patterns}")

    async def clear_blocked_urls(self) -> None:
        await self.execute_cdp_command("Network.setBlockedURLs", {"urls": []})
        logger.info("Cleared blocked URLs")

    async def set_geolocation(self, latitude: float, longitude: float, accuracy: float = 100) -> None:
        await self.execute_cdp_command("Emulation.setGeolocationOverride", {"latitude": latitude, "longitude": longitude, "accuracy": accuracy})
        logger.info(f"Set geolocation: {latitude}, {longitude}")

    async def clear_geolocation(self) -> None:
        await self.execute_cdp_command("Emulation.clearGeolocationOverride", {})
        logger.info("Cleared geolocation override")

    async def set_timezone(self, timezone_id: str) -> None:
        await self.execute_cdp_command("Emulation.setTimezoneOverride", {"timezoneId": timezone_id})
        logger.info(f"Set timezone: {timezone_id}")

    async def get_cookies(self) -> list[dict[str, Any]]:
        result = await self.execute_cdp_command("Network.getAllCookies", {})
        return result.get("cookies", [])
