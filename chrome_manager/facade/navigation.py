import asyncio
from datetime import datetime
from typing import Any

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from ..core.instance import BrowserInstance
from ..models.browser import PageResult, WaitCondition
from ..utils.exceptions import NavigationError


class NavigationController:
    def __init__(self, instance: BrowserInstance):
        self.instance = instance
        self.driver = instance.driver

    async def navigate(self, url: str, wait_for: WaitCondition | None = None, timeout: int = 30) -> PageResult:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        start_time = asyncio.get_event_loop().time()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.get, url)

            if wait_for:
                await self._wait_for_condition(wait_for, timeout)
            else:
                await self._wait_for_load(timeout)

            load_time = asyncio.get_event_loop().time() - start_time

            title = self.driver.title
            current_url = self.driver.current_url

            content_length = await loop.run_in_executor(None, self.driver.execute_script, "return document.documentElement.innerHTML.length")

            self.instance.last_activity = datetime.now()

            return PageResult(url=current_url, title=title, status_code=200, load_time=load_time, content_length=content_length)

        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    async def back(self) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.back)
            await self._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to go back: {e}") from e

    async def forward(self) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.forward)
            await self._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to go forward: {e}") from e

    async def refresh(self, force: bool = False) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            if force:
                await loop.run_in_executor(None, self.driver.execute_script, "location.reload(true)")
            else:
                await loop.run_in_executor(None, self.driver.refresh)

            await self._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to refresh: {e}") from e

    async def wait_for_navigation(self, timeout: int = 30) -> None:
        await self._wait_for_load(timeout)

    async def wait_for_element(self, selector: str, timeout: int = 30, visible: bool = True) -> bool:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            wait = WebDriverWait(self.driver, timeout)

            by, value = self._parse_selector(selector)

            condition = EC.visibility_of_element_located((by, value)) if visible else EC.presence_of_element_located((by, value))

            loop = asyncio.get_event_loop()
            element = await loop.run_in_executor(None, wait.until, condition)

            return element is not None

        except Exception as e:
            logger.warning(f"Element wait failed for {selector}: {e}")
            return False

    async def scroll_to(self, x: int | None = None, y: int | None = None, element: str | None = None, smooth: bool = True) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            if element:
                script = f"""
                const element = document.querySelector('{element}');
                if (element) {{
                    element.scrollIntoView({{
                        behavior: '{"smooth" if smooth else "auto"}',
                        block: 'center'
                    }});
                }}
                """
            else:
                behavior = "smooth" if smooth else "auto"
                script = f"window.scrollTo({{left: {x or 0}, top: {y or 0}, behavior: '{behavior}'}})"

            await loop.run_in_executor(None, self.driver.execute_script, script)
            await asyncio.sleep(0.5 if smooth else 0.1)

        except Exception as e:
            raise NavigationError(f"Failed to scroll: {e}") from e

    async def get_page_source(self) -> str:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.driver.page_source)
        except Exception as e:
            raise NavigationError(f"Failed to get page source: {e}") from e

    async def execute_script(self, script: str, *args, async_script: bool = False) -> Any:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            if async_script:
                return await loop.run_in_executor(None, self.driver.execute_async_script, script, *args)
            return await loop.run_in_executor(None, self.driver.execute_script, script, *args)
        except Exception as e:
            raise NavigationError(f"Failed to execute script: {e}") from e

    async def _wait_for_load(self, timeout: int = 30) -> None:
        try:
            wait = WebDriverWait(self.driver, timeout)
            loop = asyncio.get_event_loop()

            await loop.run_in_executor(None, wait.until, lambda driver: driver.execute_script("return document.readyState") == "complete")
        except Exception as e:
            logger.warning(f"Page load wait timeout: {e}")

    async def _wait_for_condition(self, condition: WaitCondition, timeout: int) -> None:
        wait = WebDriverWait(self.driver, timeout, poll_frequency=condition.poll_frequency)
        loop = asyncio.get_event_loop()

        if condition.type == "load":
            await self._wait_for_load(timeout)

        elif condition.type == "networkidle":
            await loop.run_in_executor(
                None,
                wait.until,
                lambda driver: driver.execute_script(
                    """
                    return performance.getEntriesByType('resource')
                        .filter(r => !r.responseEnd).length === 0
                """
                ),
            )

        elif condition.type == "element" and condition.target:
            by, value = self._parse_selector(condition.target)
            await loop.run_in_executor(None, wait.until, EC.presence_of_element_located((by, value)))

        elif condition.type == "function" and condition.target:
            await loop.run_in_executor(None, wait.until, lambda driver: driver.execute_script(condition.target))

    def _parse_selector(self, selector: str) -> tuple:
        if selector.startswith("//"):
            return (By.XPATH, selector)
        if selector.startswith("#"):
            return (By.ID, selector[1:])
        if selector.startswith("."):
            return (By.CLASS_NAME, selector[1:])
        return (By.CSS_SELECTOR, selector)
