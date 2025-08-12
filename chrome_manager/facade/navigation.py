import asyncio
from typing import Any

from loguru import logger
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from ..models.browser import PageResult, WaitCondition
from ..utils.exceptions import NavigationError
from ..utils.parser import HTMLParser
from .base import BaseController
from .config import FACADE_CONFIG
from .utils import parameterized_js_execution


class NavigationController(BaseController):
    """Controller for browser navigation operations."""

    async def navigate(self, url: str, wait_for: WaitCondition | None = None, timeout: int = 30) -> PageResult:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Detect if we're in a thread context
        in_thread = self._is_in_thread_context()
        logger.debug(f"NavigationController.navigate: in_thread={in_thread}, url={url}")

        if in_thread:
            # Use synchronous operations directly when in thread context
            import time

            start_time = time.time()

            try:
                # Navigate synchronously
                logger.debug(f"Calling driver.get synchronously for {url}")
                self.driver.get(url)
                logger.debug(f"driver.get completed for {url}")

                if wait_for:
                    # Synchronous wait
                    self._wait_for_condition_sync(wait_for, timeout)
                else:
                    self._wait_for_load_sync(timeout)

                load_time = time.time() - start_time

                title = self.driver.title
                current_url = self.driver.current_url
                content_length = self.driver.execute_script("return document.documentElement.innerHTML.length")

                self.instance.update_activity()

                result = PageResult(url=current_url, title=title, status_code=200, load_time=load_time, content_length=content_length)
                logger.debug(f"Navigation result: {result}")
                return result

            except Exception as e:
                logger.error(f"Navigation failed for {url}: {e}")
                raise NavigationError(f"Failed to navigate to {url}: {e}") from e
        else:
            # Normal async operation
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

                self.instance.update_activity()

                return PageResult(url=current_url, title=title, status_code=200, load_time=load_time, content_length=content_length)

            except Exception as e:
                logger.error(f"Navigation failed for {url}: {e}")
                raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    async def back(self) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                self.driver.back()
                self._wait_for_load_sync()
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.back)
                await self._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to go back: {e}") from e

    async def forward(self) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                self.driver.forward()
                self._wait_for_load_sync()
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.forward)
                await self._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to go forward: {e}") from e

    async def refresh(self, force: bool = False) -> None:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                if force:
                    self.driver.execute_script("location.reload(true)")
                else:
                    self.driver.refresh()
                self._wait_for_load_sync()
            else:
                # Normal async operation
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

            if self._is_in_thread_context():
                # Synchronous operation in thread context
                element = wait.until(condition)
            else:
                # Normal async operation
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
            if element:
                script = parameterized_js_execution(
                    """
                const element = document.querySelector({element});
                if (element) {{
                    element.scrollIntoView({{
                        behavior: {behavior},
                        block: 'center'
                    }});
                }}
                """,
                    element=element,
                    behavior="smooth" if smooth else "auto",
                )
            else:
                behavior = "smooth" if smooth else "auto"
                script = f"window.scrollTo({{left: {x or 0}, top: {y or 0}, behavior: '{behavior}'}})"

            if self._is_in_thread_context():
                # Synchronous operation in thread context
                import time

                self.driver.execute_script(script)
                time.sleep(FACADE_CONFIG.scroll_wait_smooth if smooth else FACADE_CONFIG.scroll_wait_instant)
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)
                await asyncio.sleep(FACADE_CONFIG.scroll_wait_smooth if smooth else FACADE_CONFIG.scroll_wait_instant)

        except Exception as e:
            raise NavigationError(f"Failed to scroll: {e}") from e

    async def get_page_source(self) -> str:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                return self.driver.page_source
            # Normal async operation
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.driver.page_source)
        except Exception as e:
            raise NavigationError(f"Failed to get page source: {e}") from e

    async def execute_script(self, script: str, *args, async_script: bool = False) -> Any:
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                if async_script:
                    return self.driver.execute_async_script(script, *args)
                return self.driver.execute_script(script, *args)
            # Normal async operation
            loop = asyncio.get_event_loop()

            if async_script:
                return await loop.run_in_executor(None, self.driver.execute_async_script, script, *args)
            return await loop.run_in_executor(None, self.driver.execute_script, script, *args)
        except Exception as e:
            raise NavigationError(f"Failed to execute script: {e}") from e

    def _wait_for_load_sync(self, timeout: int = 30) -> None:
        """Synchronous version of _wait_for_load for thread context."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
        except Exception as e:
            logger.warning(f"Page load wait timeout: {e}")

    def _wait_for_condition_sync(self, condition: WaitCondition, timeout: int) -> None:
        """Synchronous version of _wait_for_condition for thread context."""
        wait = WebDriverWait(self.driver, timeout, poll_frequency=condition.poll_frequency)

        if condition.type == "load":
            self._wait_for_load_sync(timeout)

        elif condition.type == "networkidle":
            wait.until(
                lambda driver: driver.execute_script(
                    """
                    return performance.getEntriesByType('resource')
                        .filter(r => !r.responseEnd).length === 0
                """
                )
            )

        elif condition.type == "element" and condition.target:
            by, value = self._parse_selector(condition.target)
            wait.until(EC.presence_of_element_located((by, value)))

        elif condition.type == "function" and condition.target:
            wait.until(lambda driver: driver.execute_script(condition.target))

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

    async def get_page_content(self) -> str:
        """Get the full HTML content of the page."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                return self.driver.page_source
            # Normal async operation
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.driver.page_source)
        except Exception as e:
            raise NavigationError(f"Failed to get page content: {e}") from e

    async def get_element_html(self, selector: str) -> str:
        """Get the inner HTML of a specific element."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = parameterized_js_execution("return document.querySelector({selector}).innerHTML", selector=selector)
            return await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to get element HTML: {e}") from e

    async def get_html_with_depth_limit(self, max_depth: int | None = None, collapse_depth: int | None = None) -> str:
        """Get HTML with depth limitations to reduce size.

        Args:
            max_depth: Maximum depth to traverse (stops at this depth)
            collapse_depth: Depth at which to collapse elements to placeholders

        Returns:
            HTML string with depth limitations applied
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        function getHtmlWithDepth(element, currentDepth, maxDepth, collapseDepth) {
            if (maxDepth && currentDepth > maxDepth) {
                return '';
            }

            if (collapseDepth && currentDepth >= collapseDepth) {
                // Collapse to placeholder
                const tag = element.tagName.toLowerCase();
                const id = element.id ? ` id="${element.id}"` : '';
                const className = element.className ? ` class="${element.className}"` : '';
                const childCount = element.children.length;
                return `<${tag}${id}${className}><!-- ${childCount} child elements collapsed --></${tag}>`;
            }

            // Build the HTML string
            let html = '<' + element.tagName.toLowerCase();

            // Add attributes
            for (let attr of element.attributes) {
                html += ` ${attr.name}="${attr.value}"`;
            }
            html += '>';

            // Add text content if it's a text node
            if (element.childNodes.length > 0) {
                for (let child of element.childNodes) {
                    if (child.nodeType === Node.TEXT_NODE) {
                        html += child.textContent;
                    } else if (child.nodeType === Node.ELEMENT_NODE) {
                        html += getHtmlWithDepth(child, currentDepth + 1, maxDepth, collapseDepth);
                    }
                }
            }

            html += '</' + element.tagName.toLowerCase() + '>';
            return html;
        }

        const maxD = arguments[0];
        const collapseD = arguments[1];
        return getHtmlWithDepth(document.documentElement, 0, maxD, collapseD);
        """

        try:
            return await self.execute_script(script, max_depth, collapse_depth)
        except Exception as e:
            raise NavigationError(f"Failed to get HTML with depth limit: {e}") from e

    async def extract_text(self, preserve_structure: bool = True, **kwargs) -> str:
        """Extract human-readable text from the current page.

        Args:
            preserve_structure: Keep paragraph/line breaks
            **kwargs: Additional options for text extraction

        Returns:
            Cleaned, human-readable text from the page
        """
        html = await self.get_page_content()
        parser = HTMLParser(html)
        return parser.extract_text(preserve_structure=preserve_structure, **kwargs)

    async def extract_links(self, absolute: bool = True) -> list[dict[str, str]]:
        """Extract all links from the current page.

        Args:
            absolute: Convert relative URLs to absolute

        Returns:
            List of link dictionaries with text, href, and title
        """
        html = await self.get_page_content()
        parser = HTMLParser(html)
        base_url = self.driver.current_url if absolute else ""
        return parser.extract_links(absolute=absolute, base_url=base_url)

    async def extract_forms(self) -> list[dict[str, Any]]:
        """Extract form information from the current page."""
        html = await self.get_page_content()
        parser = HTMLParser(html)
        return parser.extract_forms()

    async def extract_tables(self) -> list[dict[str, Any]]:
        """Extract table data from the current page."""
        html = await self.get_page_content()
        parser = HTMLParser(html)
        return parser.extract_tables()

    async def extract_images(self) -> list[dict[str, str]]:
        """Extract all images from the current page."""
        html = await self.get_page_content()
        parser = HTMLParser(html)
        return parser.extract_images()

    async def find_elements_by_text(self, text: str, tag: str | None = None) -> list[dict[str, str]]:
        """Find elements containing specific text.

        Args:
            text: Text to search for
            tag: Optional tag name to limit search

        Returns:
            List of matching element selectors
        """
        html = await self.get_page_content()
        parser = HTMLParser(html)
        elements = parser.find_by_text(text, tag)

        # Convert elements to selectors
        results = []
        for elem in elements:
            selector = ""
            if elem.get("id"):
                selector = f"#{elem['id']}"
            elif elem.get("class"):
                classes = elem["class"]
                selector = f".{'.'.join(classes)}" if isinstance(classes, list) else f".{classes}"
            else:
                selector = elem.name

            results.append({"selector": selector, "tag": elem.name, "text": elem.get_text(strip=True)})

        return results

    async def get_local_storage(self, key: str | None = None) -> dict[str, str] | str | None:
        """Get local storage data.

        Args:
            key: Optional key to get specific value. If None, returns all items.

        Returns:
            If key is provided: the value for that key or None if not found
            If key is None: dictionary of all local storage items
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if key:
                script = f"return localStorage.getItem('{key}')"
                return await self.execute_script(script)
            script = """
            const items = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                items[key] = localStorage.getItem(key);
            }
            return items;
            """
            return await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to get local storage: {e}") from e

    async def set_local_storage(self, key: str, value: str) -> None:
        """Set a local storage item.

        Args:
            key: The key to set
            value: The value to store
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            # Escape single quotes in the value
            escaped_value = value.replace("'", "\\'")
            script = f"localStorage.setItem('{key}', '{escaped_value}')"
            await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to set local storage: {e}") from e

    async def remove_local_storage(self, key: str) -> None:
        """Remove a local storage item.

        Args:
            key: The key to remove
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = f"localStorage.removeItem('{key}')"
            await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to remove local storage item: {e}") from e

    async def clear_local_storage(self) -> None:
        """Clear all local storage items."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = "localStorage.clear()"
            await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to clear local storage: {e}") from e

    async def get_session_storage(self, key: str | None = None) -> dict[str, str] | str | None:
        """Get session storage data.

        Args:
            key: Optional key to get specific value. If None, returns all items.

        Returns:
            If key is provided: the value for that key or None if not found
            If key is None: dictionary of all session storage items
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if key:
                script = f"return sessionStorage.getItem('{key}')"
                return await self.execute_script(script)
            script = """
            const items = {};
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                items[key] = sessionStorage.getItem(key);
            }
            return items;
            """
            return await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to get session storage: {e}") from e

    async def set_session_storage(self, key: str, value: str) -> None:
        """Set a session storage item.

        Args:
            key: The key to set
            value: The value to store
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            # Escape single quotes in the value
            escaped_value = value.replace("'", "\\'")
            script = f"sessionStorage.setItem('{key}', '{escaped_value}')"
            await self.execute_script(script)
        except Exception as e:
            raise NavigationError(f"Failed to set session storage: {e}") from e
