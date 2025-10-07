"""Browser lifecycle management - launch, terminate, restart."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

from browser.backend.core.browser.tab_manager import TabManager
from browser.backend.core.security.antidetect import (
    ChromeDriverPatcher,
    execute_anti_detection_scripts,
)
from browser.backend.core.security.tab_injector import SimpleTabInjector
from browser.backend.models.browser import BrowserStatus
from browser.backend.models.security import SecurityConfig, SecurityLevel
from browser.backend.utils.config import Config
from browser.backend.utils.exceptions import InstanceError

if TYPE_CHECKING:
    pass

# Timeout constants
DEFAULT_PAGE_LOAD_TIMEOUT = 30  # seconds
DEFAULT_SCRIPT_TIMEOUT = 30  # seconds
DEFAULT_IMPLICIT_WAIT = 5  # seconds
PROCESS_TERMINATION_TIMEOUT = 5  # seconds


class BrowserLifecycle:
    """Manages browser lifecycle - launch, terminate, restart."""

    def __init__(
        self,
        instance_id: str,
        config: Config | None = None,
        security_config: SecurityConfig | None = None,
    ):
        self.instance_id = instance_id
        self.driver: WebDriver | None = None
        self.status = BrowserStatus.IDLE
        self._config = config or Config()
        self._security_config = security_config
        self._service: Service | None = None
        self._launch_options: dict[str, Any] = {}
        self.window_monitor: SimpleTabInjector | None = None
        self.tab_manager: TabManager | None = None

    def set_security_config(self, config: SecurityConfig | None = None) -> None:
        """Set or update security configuration."""
        if config:
            self._security_config = config
        else:
            # Load from config or use default
            security_level = self._config.get("backend.security.level", "standard")
            self._security_config = SecurityConfig.from_level(SecurityLevel(security_level))

    async def launch(self, chrome_options: Options, anti_detect: bool = False) -> WebDriver:
        """Launch the browser with given options."""
        try:
            self.status = BrowserStatus.STARTING

            # Store launch options for restart
            self._launch_options = {
                "options": chrome_options,
                "anti_detect": anti_detect,
            }

            # Launch based on mode
            if anti_detect:
                driver = await self._launch_undetected_mode(chrome_options)
            else:
                driver = await self._launch_standard(chrome_options)

            self.driver = driver
            self.status = BrowserStatus.READY

            # Setup tab manager
            if driver:
                self.tab_manager = TabManager(driver, self.instance_id)
                logger.debug(f"Tab manager initialized for instance {self.instance_id}")

            # Setup tab injection monitor if anti-detect
            if anti_detect and driver:
                self.window_monitor = SimpleTabInjector(driver)
                logger.debug(f"Tab injection monitor setup for instance {self.instance_id}")

            logger.info(f"Browser instance {self.instance_id} launched successfully")
            return driver

        except Exception as e:
            self.status = BrowserStatus.ERROR
            logger.error(f"Failed to launch browser: {e}")
            raise InstanceError(f"Failed to launch browser: {e}") from e

    async def _launch_undetected_mode(self, chrome_options: Options) -> WebDriver:
        """Launch Chrome with anti-detection features."""
        loop = asyncio.get_event_loop()

        # Ensure Chrome and ChromeDriver are installed and configured
        chrome_binary_path, chromedriver_path = self._ensure_chrome_ready()

        # Set Chrome binary location
        if chrome_binary_path and Path(chrome_binary_path).exists():
            chrome_options.binary_location = str(chrome_binary_path)

        # Patch ChromeDriver for anti-detection
        patched_driver_path = chromedriver_path
        logger.info(f"ChromeDriver path: {chromedriver_path}")

        if chromedriver_path and Path(chromedriver_path).exists():
            patcher = ChromeDriverPatcher(chromedriver_path)
            if not patcher.is_patched():
                logger.info("Patching ChromeDriver for anti-detection...")
                if patcher.patch():
                    patched_driver_path = str(patcher.get_patched_path())
                    logger.info(f"Using patched ChromeDriver: {patched_driver_path}")
                else:
                    logger.error("Failed to patch ChromeDriver")
            else:
                patched_driver_path = str(patcher.get_patched_path())
                logger.info(f"Using already patched ChromeDriver: {patched_driver_path}")
        # Create service and driver (explicit path required; do not rely on PATH)
        if not patched_driver_path:
            raise InstanceError("ChromeDriver path is not set after patching")
        self._service = Service(executable_path=patched_driver_path)
        try:
            driver = await loop.run_in_executor(
                None,
                lambda: webdriver.Chrome(service=self._service, options=chrome_options),
            )
        except WebDriverException as e:
            logger.error(f"Chrome launch failed: {e}")
            raise

        # Set timeouts
        driver.set_page_load_timeout(DEFAULT_PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)

        # Inject anti-detection script

        execute_anti_detection_scripts(driver)

        return driver

    async def _launch_standard(self, chrome_options: Options) -> WebDriver:
        """Launch Chrome in standard mode."""
        loop = asyncio.get_event_loop()

        # Ensure Chrome and ChromeDriver are installed and configured
        chrome_binary_path, chromedriver_path = self._ensure_chrome_ready()

        # Set chrome binary
        if chrome_binary_path and Path(chrome_binary_path).exists():
            chrome_options.binary_location = str(chrome_binary_path)

        # Create service and driver (explicit path required; do not rely on PATH)
        if not chromedriver_path:
            raise InstanceError("ChromeDriver path is not set")
        self._service = Service(executable_path=chromedriver_path)
        try:
            driver = await loop.run_in_executor(
                None,
                lambda: webdriver.Chrome(service=self._service, options=chrome_options),
            )
        except WebDriverException as e:
            logger.error(f"Chrome launch failed: {e}")
            raise

        # Set timeouts
        driver.set_page_load_timeout(DEFAULT_PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)

        return driver

    def _ensure_chrome_ready(self) -> tuple[str, str]:
        """Ensure Chrome and ChromeDriver are available and return their paths.

        Paths must be configured explicitly in browser/config.yaml. This helper verifies
        they exist and refuses to launch when binaries are missing so operators can take
        corrective action (for example by running browser/scripts/setup_chrome.py).
        """
        # Load configured paths
        chrome_binary_path = self._config.get("backend.browser.chrome_binary_path")
        chromedriver_path = self._config.get("backend.browser.chromedriver_path")

        # Validate Chrome binary
        if not chrome_binary_path or not Path(str(chrome_binary_path)).exists():
            raise InstanceError(
                f"Chrome binary not found: {chrome_binary_path}. " "Configure 'backend.browser.chrome_binary_path' and run browser/scripts/setup_chrome.py"
            )

        # Validate ChromeDriver
        if not chromedriver_path or not Path(str(chromedriver_path)).exists():
            raise InstanceError(
                f"ChromeDriver not found: {chromedriver_path}. " "Configure 'backend.browser.chromedriver_path' and run browser/scripts/setup_chrome.py"
            )

        return str(chrome_binary_path), str(chromedriver_path)

    async def terminate(self, force: bool = False) -> None:
        """Terminate the browser instance."""
        if not self.driver:
            return

        self.status = BrowserStatus.CLOSING

        try:
            # Stop monitoring if active
            if self.window_monitor:
                self.window_monitor.stop_monitoring()
                self.window_monitor = None

            # Try graceful quit first
            if not force:
                try:
                    self.driver.quit()
                    logger.debug(f"Browser instance {self.instance_id} terminated gracefully")
                except Exception as e:
                    logger.warning(f"Graceful quit failed: {e}, forcing termination")
                    force = True

            # ALWAYS stop the ChromeDriver service to terminate the process
            if self._service:
                try:
                    self._service.stop()
                    logger.debug(f"ChromeDriver service stopped for instance {self.instance_id}")
                except Exception as e:
                    logger.error(f"Failed to stop ChromeDriver service: {e}")

        except Exception as e:
            logger.error(f"Error during termination: {e}")
        finally:
            self.driver = None
            self._service = None
            self.status = BrowserStatus.CLOSED
            logger.info(f"Browser instance {self.instance_id} terminated")

    async def restart(self) -> WebDriver | None:
        """Restart the browser with the same options."""
        if not self._launch_options:
            logger.error("No launch options stored for restart")
            return None

        await self.terminate()
        return await self.launch(self._launch_options["options"], self._launch_options["anti_detect"])

    def is_alive(self) -> bool:
        """Check if browser is still alive."""
        if not self.driver:
            return False

        try:
            # Try to get current URL as a health check
            _ = self.driver.current_url
            return True
        except WebDriverException as e:
            logger.debug(f"Browser health check failed: {e}")
            return False
