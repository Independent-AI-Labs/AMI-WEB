"""Tab management and control."""

import asyncio

from loguru import logger

from ...models.browser import TabInfo
from ...utils.exceptions import NavigationError
from ..base import BaseController


class TabController(BaseController):
    """Controller for browser tab management."""

    async def create_tab(self, url: str | None = None) -> TabInfo:
        """Create a new browser tab.

        Args:
            url: Optional URL to navigate to in the new tab

        Returns:
            TabInfo with new tab details
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            # Open new tab
            await loop.run_in_executor(None, self.driver.execute_script, "window.open('', '_blank');")

            handles = self.driver.window_handles
            if not handles:
                raise NavigationError("No window handles available after creating tab")

            new_handle = handles[-1]

            # Switch to new tab
            await loop.run_in_executor(None, self.driver.switch_to.window, new_handle)

            # Navigate if URL provided
            if url:
                # Validate URL format
                if not url.startswith(("http://", "https://", "file://", "about:")):
                    url = f"https://{url}"
                await loop.run_in_executor(None, self.driver.get, url)

            tab_info = TabInfo(
                id=new_handle,
                title=self.driver.title or "New Tab",
                url=self.driver.current_url or "about:blank",
                active=True,
                index=len(handles) - 1,
                window_handle=new_handle,
            )

            self.instance.update_activity()
            logger.debug(f"Created new tab: {new_handle}")
            return tab_info

        except Exception as e:
            logger.error(f"Failed to create tab: {e}")
            raise NavigationError(f"Failed to create tab: {e}") from e

    async def switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab.

        Args:
            tab_id: ID/handle of the tab to switch to
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        if not tab_id:
            raise ValueError("Tab ID cannot be empty")

        try:
            # Validate tab exists
            handles = self.driver.window_handles
            if tab_id not in handles:
                raise NavigationError(f"Tab {tab_id} not found. Available tabs: {handles}")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.switch_to.window, tab_id)

            self.instance.update_activity()
            logger.debug(f"Switched to tab: {tab_id}")

        except Exception as e:
            logger.error(f"Failed to switch tab: {e}")
            raise NavigationError(f"Failed to switch to tab {tab_id}: {e}") from e

    async def close_tab(self, tab_id: str | None = None) -> None:
        """Close a browser tab.

        Args:
            tab_id: ID of tab to close, or None to close current tab
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            handles_before = self.driver.window_handles

            if len(handles_before) <= 1:
                logger.warning("Cannot close last tab")
                return

            if tab_id:
                # Validate tab exists
                if tab_id not in handles_before:
                    raise NavigationError(f"Tab {tab_id} not found")

                current_handle = self.driver.current_window_handle

                # Switch to target tab if not current
                if tab_id != current_handle:
                    await loop.run_in_executor(None, self.driver.switch_to.window, tab_id)

                # Close the tab
                await loop.run_in_executor(None, self.driver.close)

                # Switch back to a remaining tab
                remaining_handles = self.driver.window_handles
                if remaining_handles:
                    # Prefer switching back to original tab if it still exists
                    if current_handle != tab_id and current_handle in remaining_handles:
                        await loop.run_in_executor(None, self.driver.switch_to.window, current_handle)
                    else:
                        await loop.run_in_executor(None, self.driver.switch_to.window, remaining_handles[0])
            else:
                # Close current tab
                await loop.run_in_executor(None, self.driver.close)

                # Switch to first remaining tab
                remaining_handles = self.driver.window_handles
                if remaining_handles:
                    await loop.run_in_executor(None, self.driver.switch_to.window, remaining_handles[0])

            self.instance.update_activity()
            logger.debug(f"Closed tab: {tab_id or 'current'}")

        except Exception as e:
            logger.error(f"Failed to close tab: {e}")
            raise NavigationError(f"Failed to close tab: {e}") from e

    async def list_tabs(self) -> list[TabInfo]:
        """Get list of all open tabs.

        Returns:
            List of TabInfo objects
        """
        return await self.instance.get_tabs()

    async def get_current_tab(self) -> TabInfo:
        """Get information about the current tab.

        Returns:
            TabInfo for current tab
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            current_handle = self.driver.current_window_handle
            handles = self.driver.window_handles

            return TabInfo(
                id=current_handle,
                title=self.driver.title or "",
                url=self.driver.current_url or "about:blank",
                active=True,
                index=handles.index(current_handle) if current_handle in handles else 0,
                window_handle=current_handle,
            )
        except Exception as e:
            logger.error(f"Failed to get current tab info: {e}")
            raise NavigationError(f"Failed to get current tab info: {e}") from e

    async def switch_to_tab_by_index(self, index: int) -> None:
        """Switch to tab by index.

        Args:
            index: Zero-based index of the tab
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        if index < 0:
            raise ValueError("Tab index cannot be negative")

        try:
            handles = self.driver.window_handles

            if index >= len(handles):
                raise NavigationError(f"Tab index {index} out of range (0-{len(handles)-1})")

            await self.switch_tab(handles[index])

        except Exception as e:
            logger.error(f"Failed to switch to tab by index: {e}")
            raise NavigationError(f"Failed to switch to tab index {index}: {e}") from e

    async def switch_to_tab_by_title(self, title: str, partial: bool = True) -> None:
        """Switch to tab by title.

        Args:
            title: Title to search for
            partial: If True, match partial title
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        if not title:
            raise ValueError("Title cannot be empty")

        try:
            tabs = await self.list_tabs()

            for tab in tabs:
                if partial and title.lower() in tab.title.lower() or not partial and tab.title.lower() == title.lower():
                    await self.switch_tab(tab.id)
                    return

            raise NavigationError(f"No tab found with title {'containing' if partial else 'matching'} '{title}'")

        except Exception as e:
            logger.error(f"Failed to switch to tab by title: {e}")
            raise NavigationError(f"Failed to switch to tab by title '{title}': {e}") from e
