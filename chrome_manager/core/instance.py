import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import undetected_chromedriver as uc
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

from ..models.browser import BrowserStatus, ChromeOptions, ConsoleEntry, InstanceInfo, NetworkEntry, PerformanceMetrics, TabInfo
from ..utils.exceptions import InstanceError


class BrowserInstance:
    def __init__(self, instance_id: str | None = None):
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

    async def launch(
        self,
        headless: bool = True,
        profile: str | None = None,
        extensions: list[str] | None = None,
        options: ChromeOptions | None = None,
    ) -> WebDriver:
        try:
            self.status = BrowserStatus.STARTING
            self._options = options or ChromeOptions()

            chrome_options = self._build_chrome_options(headless=headless, profile=profile, extensions=extensions or [])

            # Use standard driver with our ChromeDriver 141
            self.driver = await self._launch_standard(chrome_options)

            if self.driver and hasattr(self.driver, "service") and self.driver.service.process:  # type: ignore[attr-defined]
                self.process = psutil.Process(self.driver.service.process.pid)  # type: ignore[attr-defined]

            self.status = BrowserStatus.IDLE
            self.last_activity = datetime.now()

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

    def _build_chrome_options(self, headless: bool, profile: str | None, extensions: list[str]) -> Options:
        chrome_options = Options()

        self._add_basic_options(chrome_options, headless)
        self._add_conditional_options(chrome_options)

        for feature in self._options.disable_blink_features:
            chrome_options.add_argument(f"--disable-blink-features={feature}")
        for arg in self._options.arguments:
            chrome_options.add_argument(arg)
        for ext_path in extensions:
            chrome_options.add_extension(ext_path)

        if self._options.prefs:
            chrome_options.add_experimental_option("prefs", self._options.prefs)
        for key, value in self._options.experimental_options.items():
            chrome_options.add_experimental_option(key, value)

        if profile:
            chrome_options.add_argument(f"--user-data-dir={profile}")

        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
        return chrome_options

    async def _launch_undetected(self, chrome_options: Options) -> WebDriver:
        loop = asyncio.get_event_loop()
        chrome_path = Path("C:/Users/vdonc/AMI-WEB/chromium-win/chrome.exe")
        if chrome_path.exists():
            chrome_options.binary_location = str(chrome_path)
        return await loop.run_in_executor(None, lambda: uc.Chrome(options=chrome_options, version_main=None, use_subprocess=True, driver_executable_path=None))

    async def _launch_standard(self, chrome_options: Options) -> WebDriver:
        loop = asyncio.get_event_loop()
        chrome_path = Path("C:/Users/vdonc/AMI-WEB/chromium-win/chrome.exe")
        if chrome_path.exists():
            chrome_options.binary_location = str(chrome_path)

        # Use our specific ChromeDriver
        chromedriver_path = "C:/Users/vdonc/AMI-WEB/chromedriver.exe"
        service = Service(executable_path=chromedriver_path)

        return await loop.run_in_executor(None, lambda: webdriver.Chrome(service=service, options=chrome_options))

    async def _setup_logging(self):
        if not self.driver:
            return

        try:
            self.driver.execute_cdp_cmd("Performance.enable", {})  # type: ignore[attr-defined]
            self.driver.execute_cdp_cmd("Network.enable", {})  # type: ignore[attr-defined]
            self.driver.execute_cdp_cmd("Console.enable", {})  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning(f"Failed to enable CDP logging: {e}")

    async def terminate(self, force: bool = False) -> None:
        try:
            self.status = BrowserStatus.TERMINATED

            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error during driver quit: {e}")
                    if force and self.process:
                        self.process.terminate()
                        await asyncio.sleep(1)
                        if self.process.is_running():
                            self.process.kill()

            logger.info(f"Browser instance {self.id} terminated")

        except Exception as e:
            logger.error(f"Failed to terminate browser instance {self.id}: {e}")
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
                const entries = performance.getEntriesByType('paint');
                const result = {};
                for (const entry of entries) {
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
            logs = self.driver.get_log("browser")
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
