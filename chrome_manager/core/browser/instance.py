"""Refactored BrowserInstance using composition pattern."""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver

from ...models.browser import BrowserStatus, ChromeOptions, ConsoleEntry, InstanceInfo, PerformanceMetrics, TabInfo
from ...models.browser_properties import BrowserProperties
from ...models.security import SecurityConfig
from ...utils.config import Config
from ...utils.exceptions import InstanceError
from ..monitoring.monitor import BrowserMonitor
from ..storage.storage import BrowserStorage
from .lifecycle import BrowserLifecycle
from .options import BrowserOptionsBuilder

if TYPE_CHECKING:
    from ..management.profile_manager import ProfileManager
    from .properties_manager import PropertiesManager


class BrowserInstance:
    """Refactored browser instance using composition for better separation of concerns."""

    def __init__(
        self,
        instance_id: str | None = None,
        config: Config | None = None,
        properties_manager: "PropertiesManager | None" = None,
        profile_manager: "ProfileManager | None" = None,
    ):
        # Core properties
        self.id = instance_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self._config = config or Config()
        self._properties_manager = properties_manager
        self._profile_manager = profile_manager

        # Composed components
        self._lifecycle = BrowserLifecycle(self.id, self._config)
        self._monitor = BrowserMonitor(self.id)
        self._storage = BrowserStorage(self.id)
        self._options_builder = BrowserOptionsBuilder(self._config, self._profile_manager)

        # State tracking
        self._profile_name: str | None = None
        self._anti_detect: bool = False
        self.process: psutil.Process | None = None

    # === Lifecycle Management (delegates to BrowserLifecycle) ===

    @property
    def driver(self) -> WebDriver | None:
        """Get the WebDriver instance."""
        return self._lifecycle.driver

    @property
    def status(self) -> BrowserStatus:
        """Get browser status."""
        return self._lifecycle.status

    @property
    def last_activity(self) -> datetime:
        """Get last activity timestamp."""
        return self._monitor.last_activity

    def update_activity(self):
        """Update last activity timestamp."""
        self._monitor.update_activity()

    async def launch(
        self,
        headless: bool = True,
        profile: str | None = None,
        extensions: list[str] | None = None,
        options: ChromeOptions | None = None,
        anti_detect: bool = False,
        browser_properties: BrowserProperties | None = None,
        download_dir: str | None = None,
        security_config: SecurityConfig | None = None,
    ) -> WebDriver:
        """Launch the browser with specified configuration."""
        try:
            # Store configuration
            self._profile_name = profile
            self._anti_detect = anti_detect

            # Set security config
            self._lifecycle.set_security_config(security_config)

            # Set up download directory
            if download_dir:
                self._storage.set_download_directory(Path(download_dir))
            elif profile and self._profile_manager:
                profile_dir = self._profile_manager.get_profile_dir(profile)
                self._storage.set_download_directory(profile_dir / "Downloads")
            else:
                default_dir = Path(self._config.get("chrome_manager.storage.download_dir", "./downloads"))
                self._storage.set_download_directory(default_dir)

            # Build Chrome options
            chrome_options = self._options_builder.build(
                headless=headless,
                profile=profile,
                extensions=extensions,
                options=options,
                anti_detect=anti_detect,
                browser_properties=browser_properties,
                download_dir=self._storage.get_download_directory(),
                security_config=security_config,
            )

            # Launch browser
            driver = await self._lifecycle.launch(chrome_options, anti_detect)

            # Setup monitoring
            await self._monitor.setup_logging(driver)

            # Track process
            try:
                if hasattr(driver, "service") and driver.service and hasattr(driver.service, "process"):  # type: ignore[attr-defined]
                    self.process = psutil.Process(driver.service.process.pid)  # type: ignore[attr-defined]
            except Exception as e:
                logger.debug(f"Could not track process: {e}")

            # Inject browser properties if provided
            if browser_properties and self._properties_manager:
                self._properties_manager.inject_properties(driver, browser_properties)

            logger.info(f"Browser instance {self.id} launched successfully")
            return driver

        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            raise InstanceError(f"Failed to launch browser: {e}") from e

    async def terminate(self, force: bool = False) -> None:
        """Terminate the browser instance."""
        await self._lifecycle.terminate(force)
        self.process = None
        self._monitor.clear_logs()
        logger.info(f"Browser instance {self.id} terminated")

    async def restart(self) -> WebDriver | None:
        """Restart the browser with the same configuration."""
        driver = await self._lifecycle.restart()
        if driver:
            await self._monitor.setup_logging(driver)
        return driver

    # === Monitoring (delegates to BrowserMonitor) ===

    async def get_console_logs(self) -> list[ConsoleEntry]:
        """Get console logs from the browser."""
        return await self._monitor.get_console_logs(self.driver)

    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics."""
        return await self._monitor.get_performance_metrics(self.driver)

    async def get_tabs(self) -> list[TabInfo]:
        """Get information about all open tabs."""
        return await self._monitor.get_tabs(self.driver)

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check."""
        return await self._monitor.health_check(self.driver)

    # === Storage Management (delegates to BrowserStorage) ===

    def get_download_directory(self) -> Path | None:
        """Get the download directory path."""
        return self._storage.get_download_directory()

    def list_downloads(self) -> list[dict[str, Any]]:
        """List all downloads."""
        return self._storage.list_downloads()

    def wait_for_download(self, filename: str | None = None, timeout: int = 30) -> Path | None:
        """Wait for a download to complete."""
        return self._storage.wait_for_download(filename, timeout)

    def clear_downloads(self) -> int:
        """Clear all downloads."""
        return self._storage.clear_downloads()

    def save_cookies(self) -> list[dict]:
        """Save cookies from the current session."""
        if not self.driver:
            raise InstanceError("Browser not initialized")
        return self._storage.save_cookies(self.driver)

    def load_cookies(self, cookies: list[dict] | None = None, navigate_to_domain: bool = True) -> int:
        """Load cookies into the browser."""
        if not self.driver:
            raise InstanceError("Browser not initialized")
        return self._storage.load_cookies(self.driver, cookies, navigate_to_domain)

    # === Security Configuration ===

    def get_security_config(self) -> SecurityConfig | None:
        """Get the current security configuration."""
        return self._lifecycle._security_config

    # === Information ===

    def get_info(self) -> InstanceInfo:
        """Get instance information."""
        tabs = []
        if self.driver:
            from contextlib import suppress

            with suppress(Exception):
                tabs = asyncio.run(self.get_tabs())

        return InstanceInfo(
            id=self.id,
            status=self.status,
            created_at=self.created_at,
            last_activity=self.last_activity,
            profile=self._profile_name,
            headless=self._is_headless(),
            active_tabs=len(tabs),
        )

    def _is_headless(self) -> bool:
        """Check if browser is running in headless mode."""
        if not self.driver:
            return False

        try:
            # Check if headless by looking at Chrome options
            capabilities = self.driver.capabilities
            chrome_options = capabilities.get("goog:chromeOptions", {})
            args = chrome_options.get("args", [])
            return any("headless" in arg for arg in args)
        except Exception:
            return False


# For backward compatibility during migration
