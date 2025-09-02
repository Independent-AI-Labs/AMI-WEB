"""Network monitoring and control via Chrome DevTools Protocol."""

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from browser.backend.facade.base import BaseController
from browser.backend.models.browser import NetworkEntry
from browser.backend.utils.exceptions import ChromeManagerError
from loguru import logger

if TYPE_CHECKING:
    from browser.backend.core.browser.instance import BrowserInstance


class NetworkController(BaseController):
    """Controller for network monitoring and interception."""

    def __init__(self, instance: "BrowserInstance") -> None:
        super().__init__(instance)
        self.request_handlers: list[Callable[..., Any]] = []
        self.response_handlers: list[Callable[..., Any]] = []
        self._monitoring_enabled = False

    async def enable_monitoring(self) -> None:
        """Enable network monitoring."""
        if self._monitoring_enabled:
            logger.debug("Network monitoring already enabled")
            return

        try:
            await self._execute_cdp("Network.enable")
            self._monitoring_enabled = True
            logger.info("Network monitoring enabled")
        except Exception as e:
            logger.error(f"Failed to enable network monitoring: {e}")
            raise ChromeManagerError(f"Failed to enable network monitoring: {e}") from e

    async def disable_monitoring(self) -> None:
        """Disable network monitoring."""
        if not self._monitoring_enabled:
            logger.debug("Network monitoring already disabled")
            return

        try:
            await self._execute_cdp("Network.disable")
            self._monitoring_enabled = False
            logger.info("Network monitoring disabled")
        except Exception as e:
            logger.error(f"Failed to disable network monitoring: {e}")
            raise ChromeManagerError(f"Failed to disable network monitoring: {e}") from e

    async def get_network_logs(self) -> list[NetworkEntry]:
        """Get captured network activity.

        Returns:
            List of network entries
        """
        try:
            if not self._monitoring_enabled:
                await self.enable_monitoring()

            if not self.driver:
                raise ChromeManagerError("Browser not initialized")
            logs = self.driver.get_log("performance")  # type: ignore[attr-defined]
            entries = []

            for log in logs:
                try:
                    message = json.loads(log["message"])
                    method = message.get("message", {}).get("method")

                    if method == "Network.responseReceived":
                        response = message["message"]["params"]["response"]
                        entries.append(
                            NetworkEntry(  # type: ignore[call-arg]
                                url=response.get("url"),
                                method=response.get("requestMethod", "GET"),
                                status=response.get("status"),
                                type=response.get("mimeType"),
                                size=response.get("encodedDataLength"),
                                headers=response.get("headers", {}),
                            ),
                        )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse log entry: {e}")
                    continue

            return entries

        except Exception as e:
            logger.error(f"Failed to get network logs: {e}")
            return []

    async def clear_cache(self) -> None:
        """Clear browser cache."""
        await self._execute_cdp("Network.clearBrowserCache")
        logger.info("Browser cache cleared")

    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        await self._execute_cdp("Network.clearBrowserCookies")
        logger.info("Browser cookies cleared")

    async def set_cache_disabled(self, disabled: bool = True) -> None:
        """Enable or disable cache.

        Args:
            disabled: If True, disable cache
        """
        await self._execute_cdp("Network.setCacheDisabled", {"cacheDisabled": disabled})
        logger.info(f"Cache {'disabled' if disabled else 'enabled'}")

    async def set_user_agent(self, user_agent: str) -> None:
        """Set custom user agent.

        Args:
            user_agent: User agent string
        """
        await self._execute_cdp("Network.setUserAgentOverride", {"userAgent": user_agent})
        logger.info(f"Set user agent: {user_agent[:50]}...")

    async def set_extra_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests.

        Args:
            headers: Dictionary of headers to add
        """
        await self._execute_cdp("Network.setExtraHTTPHeaders", {"headers": headers})
        logger.info(f"Set {len(headers)} extra headers")

    async def block_urls(self, patterns: list[str]) -> None:
        """Block URLs matching patterns.

        Args:
            patterns: List of URL patterns to block
        """
        await self.enable_monitoring()
        await self._execute_cdp("Network.setBlockedURLs", {"urls": patterns})
        logger.info(f"Blocking {len(patterns)} URL patterns")

    async def unblock_all_urls(self) -> None:
        """Remove all URL blocks."""
        await self._execute_cdp("Network.setBlockedURLs", {"urls": []})
        logger.info("Unblocked all URLs")

    async def throttle_network(self, download_kbps: int = 1024, upload_kbps: int = 512, latency_ms: int = 100) -> None:
        """Enable network throttling.

        Args:
            download_kbps: Download speed in KB/s
            upload_kbps: Upload speed in KB/s
            latency_ms: Additional latency in milliseconds
        """
        await self._execute_cdp(
            "Network.emulateNetworkConditions",
            {"offline": False, "downloadThroughput": download_kbps * 1024, "uploadThroughput": upload_kbps * 1024, "latency": latency_ms},
        )
        logger.info(f"Network throttled: {download_kbps}KB/s down, {upload_kbps}KB/s up, {latency_ms}ms latency")

    async def go_offline(self) -> None:
        """Simulate offline mode."""
        await self._execute_cdp("Network.emulateNetworkConditions", {"offline": True, "downloadThroughput": 0, "uploadThroughput": 0, "latency": 0})
        logger.info("Network set to offline mode")

    async def go_online(self) -> None:
        """Restore online mode."""
        await self._execute_cdp("Network.emulateNetworkConditions", {"offline": False, "downloadThroughput": -1, "uploadThroughput": -1, "latency": 0})
        logger.info("Network restored to online mode")

    async def _execute_cdp(self, command: str, params: dict[str, Any] | None = None) -> Any:
        """Execute CDP command.

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
                return self.driver.execute_cdp_cmd(command, params or {})
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.driver.execute_cdp_cmd(command, params or {}) if self.driver else None)
        except Exception as e:
            logger.error(f"CDP command failed: {command}: {e}")
            raise ChromeManagerError(f"Failed to execute CDP command {command}: {e}") from e
