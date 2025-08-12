"""Browser lifecycle management - launch, terminate, restart."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

from ...models.browser import BrowserStatus
from ...models.security import SecurityConfig, SecurityLevel
from ...utils.config import Config
from ...utils.exceptions import InstanceError

if TYPE_CHECKING:
    from ..security.tab_injector import SimpleTabInjector

# Timeout constants
DEFAULT_PAGE_LOAD_TIMEOUT = 30  # seconds
DEFAULT_SCRIPT_TIMEOUT = 30  # seconds
DEFAULT_IMPLICIT_WAIT = 5  # seconds
PROCESS_TERMINATION_TIMEOUT = 5  # seconds


class BrowserLifecycle:
    """Manages browser lifecycle - launch, terminate, restart."""

    def __init__(self, instance_id: str, config: Config | None = None, security_config: SecurityConfig | None = None):
        self.instance_id = instance_id
        self.driver: WebDriver | None = None
        self.status = BrowserStatus.IDLE
        self._config = config or Config()
        self._security_config = security_config
        self._service: Service | None = None
        self._launch_options: dict[str, Any] = {}
        self.window_monitor: "SimpleTabInjector | None" = None

    def set_security_config(self, config: SecurityConfig | None = None):
        """Set or update security configuration."""
        if config:
            self._security_config = config
        else:
            # Load from config or use default
            security_level = self._config.get("chrome_manager.security.level", "standard")
            self._security_config = SecurityConfig.from_level(SecurityLevel(security_level))

    async def launch(self, chrome_options: Options, anti_detect: bool = False) -> WebDriver:
        """Launch the browser with given options."""
        try:
            self.status = BrowserStatus.STARTING

            # Store launch options for restart
            self._launch_options = {"options": chrome_options, "anti_detect": anti_detect}

            # Launch based on mode
            if anti_detect:
                driver = await self._launch_undetected_mode(chrome_options)
            else:
                driver = await self._launch_standard(chrome_options)

            self.driver = driver
            self.status = BrowserStatus.READY

            # Setup tab injection monitor if anti-detect
            if anti_detect and driver:
                from ..security.tab_injector import SimpleTabInjector

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

        # Get Chrome and ChromeDriver paths
        chrome_binary_path = self._config.get("chrome_manager.browser.chrome_binary_path", "./chromium-win/chrome.exe")
        chromedriver_path = self._config.get("chrome_manager.browser.chromedriver_path", "./chromedriver.exe")

        # Set Chrome binary location
        if chrome_binary_path and Path(chrome_binary_path).exists():
            chrome_options.binary_location = str(chrome_binary_path)

        # Patch ChromeDriver for anti-detection
        patched_driver_path = chromedriver_path
        logger.info(f"ChromeDriver path from config: {chromedriver_path}")

        if chromedriver_path and Path(chromedriver_path).exists():
            from ..security.antidetect import ChromeDriverPatcher

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
        else:
            logger.warning(f"ChromeDriver not found at {chromedriver_path}, using default")

        # Create service and driver
        self._service = Service(executable_path=patched_driver_path) if patched_driver_path else Service()
        driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(service=self._service, options=chrome_options))

        # Set timeouts
        driver.set_page_load_timeout(DEFAULT_PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)

        # Inject anti-detection script
        from ..security.antidetect import execute_anti_detection_scripts

        execute_anti_detection_scripts(driver)

        return driver

    async def _launch_standard(self, chrome_options: Options) -> WebDriver:
        """Launch Chrome in standard mode."""
        loop = asyncio.get_event_loop()

        # Get Chrome binary path
        chrome_binary_path = self._config.get("chrome_manager.browser.chrome_binary_path")
        if chrome_binary_path and Path(chrome_binary_path).exists():
            chrome_options.binary_location = str(chrome_binary_path)

        # Get ChromeDriver path
        chromedriver_path = self._config.get("chrome_manager.browser.chromedriver_path")

        # Create service and driver
        self._service = Service(executable_path=chromedriver_path) if chromedriver_path else Service()
        driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(service=self._service, options=chrome_options))

        # Set timeouts
        driver.set_page_load_timeout(DEFAULT_PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)

        return driver

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

            # Force kill if needed
            if force and self._service:
                try:
                    self._service.stop()
                except Exception as e:
                    logger.error(f"Failed to stop service: {e}")

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
        except Exception:
            return False
