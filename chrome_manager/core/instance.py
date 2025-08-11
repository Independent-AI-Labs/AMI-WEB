import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.service import utils
from selenium.webdriver.remote.webdriver import WebDriver

from ..models.browser import BrowserStatus, ChromeOptions, ConsoleEntry, InstanceInfo, NetworkEntry, PerformanceMetrics, TabInfo
from ..models.browser_properties import BrowserProperties
from ..models.security import SecurityConfig, SecurityLevel
from ..utils.config import Config
from ..utils.exceptions import InstanceError

if TYPE_CHECKING:
    from .profile_manager import ProfileManager
    from .properties_manager import PropertiesManager
    from .simple_tab_injector import SimpleTabInjector


class BrowserInstance:
    def __init__(
        self,
        instance_id: str | None = None,
        config: Config | None = None,
        properties_manager: "PropertiesManager | None" = None,
        profile_manager: "ProfileManager | None" = None,
    ):
        self.id = instance_id or str(uuid.uuid4())
        self.driver: WebDriver | None = None
        self.status = BrowserStatus.IDLE
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.process: psutil.Process | None = None
        self._options: ChromeOptions | None = None
        self._service: Service | None = None
        self._logs: list[ConsoleEntry] = []
        self._network_logs: list[NetworkEntry] = []
        self._config = config or Config()
        self._properties_manager = properties_manager
        self._profile_manager = profile_manager
        self._profile_name: str | None = None
        self._download_dir: Path | None = None
        self._security_config: SecurityConfig | None = None
        self.window_monitor: "SimpleTabInjector | None" = None

    async def launch(
        self,
        headless: bool = True,
        profile: str | None = None,
        extensions: list[str] | None = None,
        options: ChromeOptions | None = None,
        anti_detect: bool = False,
        browser_properties: "BrowserProperties | None" = None,
        download_dir: str | None = None,
        security_config: SecurityConfig | None = None,
    ) -> WebDriver:
        try:
            self.status = BrowserStatus.STARTING
            self._options = options or ChromeOptions()
            self._anti_detect = anti_detect
            self._profile_name = profile

            # Set up security configuration
            if security_config:
                self._security_config = security_config
            else:
                # Load from config or use default
                security_level = self._config.get("chrome_manager.security.level", "standard")
                self._security_config = SecurityConfig.from_level(SecurityLevel(security_level))

            # Set up download directory
            if download_dir:
                self._download_dir = Path(download_dir).resolve()
            elif profile and self._profile_manager:
                # Use profile-specific download directory
                profile_dir = self._profile_manager.get_profile_dir(profile)
                self._download_dir = profile_dir / "Downloads"
            else:
                # Use default download directory
                self._download_dir = Path(self._config.get("chrome_manager.storage.download_dir", "./downloads")).resolve()

            self._download_dir.mkdir(parents=True, exist_ok=True)

            chrome_options = self._build_chrome_options(
                headless=headless,
                profile=profile,
                extensions=extensions or [],
                anti_detect=anti_detect,
                download_dir=str(self._download_dir),
                security_config=self._security_config,
            )

            # Apply browser properties if properties manager is available
            if self._properties_manager and browser_properties:
                self._properties_manager.set_instance_properties(self.id, browser_properties)
                self._properties_manager.apply_to_chrome_options(chrome_options, browser_properties)
            elif self._properties_manager:
                # Apply default properties
                props = self._properties_manager.get_instance_properties(self.id)
                self._properties_manager.apply_to_chrome_options(chrome_options, props)

            if anti_detect:
                # Use undetected mode with patched ChromeDriver
                self.driver = await self._launch_undetected_mode(chrome_options)
            else:
                # Use standard driver with our ChromeDriver 141
                self.driver = await self._launch_standard(chrome_options)

            if self.driver and hasattr(self.driver, "service") and self.driver.service.process:  # type: ignore[attr-defined]
                self.process = psutil.Process(self.driver.service.process.pid)  # type: ignore[attr-defined]

            self.status = BrowserStatus.IDLE
            self.last_activity = datetime.now()

            # Inject browser properties after launch
            if self._properties_manager:
                props = browser_properties or self._properties_manager.get_instance_properties(self.id)
                self._properties_manager.inject_properties(self.driver, props)

            await self._setup_logging()

            logger.info(f"Browser instance {self.id} launched successfully")
            return self.driver

        except Exception as e:
            self.status = BrowserStatus.CRASHED
            logger.error(f"Failed to launch browser instance {self.id}: {e}")
            raise InstanceError(f"Failed to launch browser: {e}") from e

    def _add_basic_options(self, chrome_options: Options, headless: bool) -> None:
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f"--window-size={self._options.window_size[0]},{self._options.window_size[1]}")

    def _add_conditional_options(self, chrome_options: Options) -> None:
        if self._options.user_agent:
            chrome_options.add_argument(f"--user-agent={self._options.user_agent}")
        if self._options.proxy:
            chrome_options.add_argument(f"--proxy-server={self._options.proxy}")
        if self._options.disable_gpu:
            chrome_options.add_argument("--disable-gpu")
        if self._options.no_sandbox:
            chrome_options.add_argument("--no-sandbox")
        if self._options.disable_dev_shm_usage:
            chrome_options.add_argument("--disable-dev-shm-usage")

    def _apply_anti_detection_options(self, chrome_options: Options) -> None:
        """Apply anti-detection options to Chrome."""
        from .antidetect import get_anti_detection_arguments, get_anti_detection_experimental_options

        # Add anti-detection arguments
        for arg in get_anti_detection_arguments():
            chrome_options.add_argument(arg)

        # Add experimental options for anti-detection
        exp_options = get_anti_detection_experimental_options()
        for key, value in exp_options.items():
            if key != "prefs":
                chrome_options.add_experimental_option(key, value)

        # Add anti-detection prefs
        if "prefs" in exp_options:
            chrome_options.add_experimental_option("prefs", exp_options["prefs"])

    def _add_antidetect_extension(self, chrome_options: Options) -> None:
        """Add the anti-detection extension if it exists."""
        from pathlib import Path

        ext_path = Path(__file__).parent.parent / "extensions" / "antidetect"
        if ext_path.exists():
            chrome_options.add_argument(f"--load-extension={ext_path.resolve()}")

    def _configure_anti_detect_mode(self, chrome_options: Options, headless: bool) -> None:
        """Configure Chrome for anti-detection mode."""
        self._apply_anti_detection_options(chrome_options)
        self._add_antidetect_extension(chrome_options)
        if headless:
            chrome_options.add_argument("--headless=new")

    def _configure_standard_mode(self, chrome_options: Options, headless: bool) -> None:
        """Configure Chrome for standard mode."""
        self._add_basic_options(chrome_options, headless)
        self._add_conditional_options(chrome_options)

        # Suppress GPU errors and warnings
        chrome_options.add_argument("--disable-gpu-sandbox")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--use-gl=swiftshader")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")

        # These features conflict with anti-detection
        chrome_options.add_argument("--disable-features=ChromeWhatsNewUI,TranslateUI")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    def _add_common_arguments(self, chrome_options: Options) -> None:
        """Add common arguments for all modes."""
        # Disable features that cause GCM/sync errors and slow down tests
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")

    def _apply_custom_options(self, chrome_options: Options, extensions: list[str]) -> None:
        """Apply custom options from configuration."""
        for feature in self._options.disable_blink_features:
            chrome_options.add_argument(f"--disable-blink-features={feature}")
        for arg in self._options.arguments:
            chrome_options.add_argument(arg)
        for ext_path in extensions:
            chrome_options.add_extension(ext_path)

    def _apply_preferences(
        self,
        chrome_options: Options,
        download_dir: str | None,
        security_config: SecurityConfig | None,
    ) -> None:
        """Apply Chrome preferences."""
        prefs = self._options.prefs.copy() if self._options.prefs else {}

        if security_config:
            prefs.update(security_config.to_chrome_prefs())

        if download_dir:
            prefs.update(
                {
                    "download.default_directory": download_dir,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                }
            )

        if prefs:
            chrome_options.add_experimental_option("prefs", prefs)

        for key, value in self._options.experimental_options.items():
            if key != "prefs":
                chrome_options.add_experimental_option(key, value)

    def _build_chrome_options(
        self,
        headless: bool,
        profile: str | None,
        extensions: list[str],
        anti_detect: bool = False,
        download_dir: str | None = None,
        security_config: SecurityConfig | None = None,
    ) -> Options:
        chrome_options = Options()

        # Configure based on mode
        if anti_detect:
            self._configure_anti_detect_mode(chrome_options, headless)
        else:
            self._configure_standard_mode(chrome_options, headless)

        # Add common arguments
        self._add_common_arguments(chrome_options)

        # Apply custom options
        self._apply_custom_options(chrome_options, extensions)

        # Apply security configuration
        if security_config:
            for arg in security_config.to_chrome_args():
                chrome_options.add_argument(arg)
            for key, value in security_config.to_capabilities().items():
                chrome_options.set_capability(key, value)

        # Apply preferences
        self._apply_preferences(chrome_options, download_dir, security_config)

        # Set up profile directory
        if profile:
            if self._profile_manager:
                profile_dir = self._profile_manager.get_profile_dir(profile)
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            else:
                chrome_options.add_argument(f"--user-data-dir={profile}")

        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
        return chrome_options

    async def _launch_undetected_mode(self, chrome_options: Options) -> WebDriver:
        """Launch Chrome with anti-detection features."""
        loop = asyncio.get_event_loop()

        # Get Chrome and ChromeDriver paths
        chrome_binary_path = self._config.get("chrome_manager.browser.chrome_binary_path")
        chromedriver_path = self._config.get("chrome_manager.browser.chromedriver_path")

        # Set Chrome binary location
        if chrome_binary_path and Path(chrome_binary_path).exists():
            chrome_options.binary_location = str(chrome_binary_path)

        # Patch ChromeDriver but more carefully
        patched_driver_path = chromedriver_path
        logger.info(f"ChromeDriver path from config: {chromedriver_path}")

        if chromedriver_path and Path(chromedriver_path).exists():
            from .antidetect import ChromeDriverPatcher

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
            logger.error(f"ChromeDriver not found at: {chromedriver_path}")

        # Set up remote debugging
        debug_port = utils.free_port()
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")
        chrome_options.add_argument("--remote-debugging-host=127.0.0.1")

        # Create service with patched ChromeDriver
        if patched_driver_path and Path(patched_driver_path).exists():
            service = Service(executable_path=patched_driver_path)
        else:
            logger.error(f"Patched ChromeDriver not found at: {patched_driver_path}")
            raise InstanceError("ChromeDriver path not found for anti-detection mode")

        # Launch Chrome with timeout configuration
        driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(service=service, options=chrome_options))

        # Set timeouts for better test performance
        driver.set_page_load_timeout(30)  # 30 seconds for page loads
        driver.implicitly_wait(5)  # 5 seconds implicit wait

        # Apply anti-detection scripts via CDP BEFORE any navigation
        from .antidetect import execute_anti_detection_scripts

        execute_anti_detection_scripts(driver)

        # Start simple tab monitoring for new tabs
        from .simple_tab_injector import SimpleTabInjector

        self.window_monitor = SimpleTabInjector(driver)
        self.window_monitor.start_monitoring()

        return driver

    async def _launch_standard(self, chrome_options: Options) -> WebDriver:
        loop = asyncio.get_event_loop()
        chrome_binary_path = self._config.get("chrome_manager.browser.chrome_binary_path")
        if chrome_binary_path:
            chrome_path = Path(chrome_binary_path)
            if chrome_path.exists():
                chrome_options.binary_location = str(chrome_path)

        # Try to use ChromeDriver from config, otherwise auto-download
        chromedriver_path = self._config.get("chrome_manager.browser.chromedriver_path")

        if chromedriver_path and Path(chromedriver_path).exists():
            # Use specified ChromeDriver
            service = Service(executable_path=chromedriver_path)
        else:
            # Auto-download ChromeDriver using webdriver-manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager

                logger.info("Auto-downloading ChromeDriver...")
                chromedriver_path = ChromeDriverManager().install()
                service = Service(executable_path=chromedriver_path)
            except ImportError as e:
                raise InstanceError(
                    "ChromeDriver not found and webdriver-manager not installed. Please install webdriver-manager or provide a chromedriver_path in config."
                ) from e

        driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(service=service, options=chrome_options))

        # Set timeouts for better test performance
        driver.set_page_load_timeout(30)  # 30 seconds for page loads
        driver.implicitly_wait(5)  # 5 seconds implicit wait

        return driver

    async def _setup_logging(self):
        if not self.driver:
            return

        try:
            self.driver.execute_cdp_cmd("Performance.enable", {})  # type: ignore[attr-defined]
            self.driver.execute_cdp_cmd("Network.enable", {})  # type: ignore[attr-defined]
            self.driver.execute_cdp_cmd("Console.enable", {})  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning(f"Failed to enable CDP logging: {e}")

    async def _kill_via_service(self) -> None:
        """Kill browser via service process."""
        service = getattr(self.driver, "service", None)
        if service and hasattr(service, "process") and service.process and service.process.poll() is None:
            service.process.terminate()
            await asyncio.sleep(0.1)
            if service.process.poll() is None:
                service.process.kill()

    async def _kill_via_psutil(self) -> None:
        """Kill browser via psutil process."""
        if self.process and self.process.is_running():
            self.process.terminate()
            await asyncio.sleep(0.1)
            if self.process.is_running():
                self.process.kill()

    async def terminate(self, force: bool = False) -> None:
        try:
            self.status = BrowserStatus.TERMINATED

            # Stop window monitoring if active
            if self.window_monitor:
                self.window_monitor.stop_monitoring()

            if self.driver:
                try:
                    # Properly close the browser using quit() first
                    # This sends the proper shutdown signal to Chrome
                    self.driver.quit()
                    logger.debug(f"Browser {self.id} quit successfully")

                except Exception as e:
                    logger.debug(f"Normal quit failed for {self.id}: {e}")

                    # If normal quit fails, force kill the processes
                    try:
                        await self._kill_via_service()
                        await self._kill_via_psutil()
                    except Exception as kill_error:
                        logger.debug(f"Force kill error for {self.id}: {kill_error}")

                finally:
                    self.driver = None
                    self.process = None

            logger.info(f"Browser instance {self.id} terminated")

        except Exception as e:
            logger.error(f"Failed to terminate browser instance {self.id}: {e}")
            if not force:
                raise InstanceError(f"Failed to terminate browser: {e}") from e

    async def restart(self) -> WebDriver:
        logger.info(f"Restarting browser instance {self.id}")
        await self.terminate()
        return await self.launch(headless=self._options.headless if self._options else True, extensions=self._options.extensions if self._options else [])

    async def health_check(self) -> dict[str, Any]:
        try:
            if not self.driver:
                return {"healthy": False, "status": self.status.value, "error": "Driver not initialized"}

            _ = self.driver.current_url

            memory_info = self.process.memory_info() if self.process else None
            cpu_percent = self.process.cpu_percent() if self.process else 0

            return {
                "healthy": True,
                "status": self.status.value,
                "memory_mb": memory_info.rss / 1024 / 1024 if memory_info else 0,
                "cpu_percent": cpu_percent,
                "uptime_seconds": (datetime.now() - self.created_at).total_seconds(),
                "last_activity": self.last_activity.isoformat(),
            }

        except Exception as e:
            self.status = BrowserStatus.CRASHED
            return {"healthy": False, "status": self.status.value, "error": str(e)}

    async def get_tabs(self) -> list[TabInfo]:
        if not self.driver:
            raise InstanceError("Browser not initialized")

        tabs = []
        current_handle = self.driver.current_window_handle
        handles = self.driver.window_handles

        for i, handle in enumerate(handles):
            self.driver.switch_to.window(handle)
            tabs.append(
                TabInfo(id=handle, title=self.driver.title, url=self.driver.current_url, active=(handle == current_handle), index=i, window_handle=handle)
            )

        self.driver.switch_to.window(current_handle)
        return tabs

    async def get_performance_metrics(self) -> PerformanceMetrics:
        if not self.driver:
            raise InstanceError("Browser not initialized")

        try:
            timing = self.driver.execute_script("return window.performance.timing")

            paint_timing = self.driver.execute_script(
                """
                var entries = performance.getEntriesByType('paint');
                var result = {};
                for (var i = 0; i < entries.length; i++) {
                    var entry = entries[i];
                    result[entry.name] = entry.startTime;
                }
                return result;
            """
            )

            return PerformanceMetrics(
                timestamp=datetime.now(),
                dom_content_loaded=timing.get("domContentLoadedEventEnd", 0) - timing.get("navigationStart", 0),
                load_complete=timing.get("loadEventEnd", 0) - timing.get("navigationStart", 0),
                first_paint=paint_timing.get("first-paint"),
                first_contentful_paint=paint_timing.get("first-contentful-paint"),
            )
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            raise InstanceError(f"Failed to get performance metrics: {e}") from e

    async def get_console_logs(self) -> list[ConsoleEntry]:
        if not self.driver:
            raise InstanceError("Browser not initialized")

        try:
            logs = self.driver.get_log("browser")  # type: ignore[attr-defined]
            entries = []
            for log in logs:
                entries.append(
                    ConsoleEntry(
                        timestamp=datetime.fromtimestamp(log["timestamp"] / 1000), level=log["level"], message=log["message"], source=log.get("source")
                    )
                )
            return entries
        except Exception as e:
            logger.warning(f"Failed to get console logs: {e}")
            return []

    def get_security_config(self) -> SecurityConfig | None:
        """Get the security configuration for this instance."""
        return self._security_config

    def get_download_directory(self) -> Path | None:
        """Get the download directory for this instance."""
        return self._download_dir

    def list_downloads(self) -> list[dict[str, Any]]:
        """List all files in the download directory."""
        if not self._download_dir or not self._download_dir.exists():
            return []

        downloads = []
        for file_path in self._download_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                downloads.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        return sorted(downloads, key=lambda x: x["modified"], reverse=True)

    def wait_for_download(self, filename: str | None = None, timeout: int = 30) -> Path | None:
        """Wait for a download to complete."""
        import time

        if not self._download_dir:
            return None

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check for Chrome temp download files (.crdownload)
            temp_files = list(self._download_dir.glob("*.crdownload"))

            if not temp_files:
                # No downloads in progress
                if filename:
                    target_file = self._download_dir / filename
                    if target_file.exists():
                        return target_file
                else:
                    # Return the most recent file
                    files = [f for f in self._download_dir.iterdir() if f.is_file() and not f.name.endswith(".crdownload")]
                    if files:
                        return max(files, key=lambda f: f.stat().st_mtime)

            time.sleep(0.5)

        return None

    def clear_downloads(self) -> int:
        """Clear all files from the download directory."""
        if not self._download_dir or not self._download_dir.exists():
            return 0

        count = 0
        for file_path in self._download_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
                count += 1

        logger.info(f"Cleared {count} files from download directory")
        return count

    def save_cookies(self) -> list[dict]:
        """Save current cookies."""
        if not self.driver:
            raise InstanceError("Browser not initialized")

        cookies = self.driver.get_cookies()

        # If using a profile, save cookies to profile
        if self._profile_name and self._profile_manager:
            profile_dir = self._profile_manager.get_profile_dir(self._profile_name)
            cookies_file = profile_dir / "saved_cookies.json"

            with cookies_file.open("w") as f:
                json.dump(cookies, f, indent=2)

            logger.info(f"Saved {len(cookies)} cookies to profile {self._profile_name}")

        return cookies

    def _load_cookies_from_profile(self) -> list[dict] | None:
        """Load cookies from profile storage."""
        if not self._profile_name or not self._profile_manager:
            return None

        profile_dir = self._profile_manager.get_profile_dir(self._profile_name)
        cookies_file = profile_dir / "saved_cookies.json"

        if not cookies_file.exists():
            return None

        with cookies_file.open() as f:
            cookies = json.load(f)
        logger.info(f"Loaded {len(cookies)} cookies from profile {self._profile_name}")
        return cookies

    def _add_cookies_for_domain(self, domain: str, cookies: list[dict], navigate: bool) -> int:
        """Add cookies for a specific domain."""
        count = 0

        if navigate and domain:
            clean_domain = domain.lstrip(".")
            url = f"https://{clean_domain}/"
            try:
                self.driver.get(url)
            except Exception as e:
                logger.debug(f"Could not navigate to {url}: {e}")

        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
                count += 1
            except Exception as e:
                logger.debug(f"Could not add cookie: {e}")

        return count

    def load_cookies(self, cookies: list[dict] | None = None, navigate_to_domain: bool = True) -> int:
        """Load cookies into the browser.

        Args:
            cookies: List of cookie dicts to load, or None to load from profile
            navigate_to_domain: If True, navigate to cookie domain before adding
        """
        if not self.driver:
            raise InstanceError("Browser not initialized")

        # Load from profile if no cookies provided
        if not cookies:
            cookies = self._load_cookies_from_profile()

        if not cookies:
            return 0

        # Group cookies by domain
        cookies_by_domain: dict[str, list[dict]] = {}
        for cookie in cookies:
            domain = cookie.get("domain", "")
            if domain:
                cookies_by_domain.setdefault(domain, []).append(cookie)

        # Add cookies for each domain
        count = 0
        for domain, domain_cookies in cookies_by_domain.items():
            count += self._add_cookies_for_domain(domain, domain_cookies, navigate_to_domain)

        logger.info(f"Added {count} cookies to browser")
        return count

    def get_info(self) -> InstanceInfo:
        memory_usage = 0
        cpu_usage = 0.0

        if self.process and self.process.is_running():
            try:
                memory_info = self.process.memory_info()
                memory_usage = memory_info.rss
                cpu_usage = self.process.cpu_percent()
            except Exception:
                logger.debug("Failed to get process info")

        tab_count = len(self.driver.window_handles) if self.driver else 0

        return InstanceInfo(
            id=self.id,
            status=self.status,
            created_at=self.created_at,
            last_activity=self.last_activity,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            active_tabs=tab_count,
            headless=self._options.headless if self._options else True,
        )
