import asyncio

from loguru import logger
from selenium.webdriver.common.by import By

from ..core.browser.instance import BrowserInstance
from ..models.browser import TabInfo
from ..utils.exceptions import NavigationError


class ContextManager:
    def __init__(self, instance: BrowserInstance):
        self.instance = instance
        self.driver = instance.driver

    async def create_tab(self, url: str | None = None) -> TabInfo:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            await loop.run_in_executor(None, self.driver.execute_script, "window.open('', '_blank');")

            handles = self.driver.window_handles
            new_handle = handles[-1]

            await loop.run_in_executor(None, self.driver.switch_to.window, new_handle)

            if url:
                await loop.run_in_executor(None, self.driver.get, url)

            tab_info = TabInfo(
                id=new_handle, title=self.driver.title, url=self.driver.current_url, active=True, index=len(handles) - 1, window_handle=new_handle
            )

            logger.debug(f"Created new tab: {new_handle}")
            return tab_info

        except Exception as e:
            logger.error(f"Failed to create tab: {e}")
            raise NavigationError(f"Failed to create tab: {e}") from e

    async def switch_tab(self, tab_id: str) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.switch_to.window, tab_id)
            logger.debug(f"Switched to tab: {tab_id}")

        except Exception as e:
            logger.error(f"Failed to switch tab: {e}")
            raise NavigationError(f"Failed to switch to tab {tab_id}: {e}") from e

    async def close_tab(self, tab_id: str | None = None) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            if tab_id:
                current_handle = self.driver.current_window_handle
                await loop.run_in_executor(None, self.driver.switch_to.window, tab_id)
                await loop.run_in_executor(None, self.driver.close)

                remaining_handles = self.driver.window_handles
                if remaining_handles:
                    if current_handle in remaining_handles:
                        await loop.run_in_executor(None, self.driver.switch_to.window, current_handle)
                    else:
                        await loop.run_in_executor(None, self.driver.switch_to.window, remaining_handles[0])
            else:
                await loop.run_in_executor(None, self.driver.close)
                remaining_handles = self.driver.window_handles
                if remaining_handles:
                    await loop.run_in_executor(None, self.driver.switch_to.window, remaining_handles[0])

            logger.debug(f"Closed tab: {tab_id or 'current'}")

        except Exception as e:
            logger.error(f"Failed to close tab: {e}")
            raise NavigationError(f"Failed to close tab: {e}") from e

    async def list_tabs(self) -> list[TabInfo]:
        return await self.instance.get_tabs()

    async def switch_frame(self, frame) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            if isinstance(frame, str):
                frame = int(frame) if frame.isdigit() else self.driver.find_element(By.CSS_SELECTOR, frame)

            await loop.run_in_executor(None, self.driver.switch_to.frame, frame)

            logger.debug(f"Switched to frame: {frame}")

        except Exception as e:
            logger.error(f"Failed to switch frame: {e}")
            raise NavigationError(f"Failed to switch to frame: {e}") from e

    async def switch_to_default_content(self) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.switch_to.default_content)
            logger.debug("Switched to default content")

        except Exception as e:
            logger.error(f"Failed to switch to default content: {e}")
            raise NavigationError(f"Failed to switch to default content: {e}") from e

    async def switch_to_parent_frame(self) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.switch_to.parent_frame)
            logger.debug("Switched to parent frame")

        except Exception as e:
            logger.error(f"Failed to switch to parent frame: {e}")
            raise NavigationError(f"Failed to switch to parent frame: {e}") from e
