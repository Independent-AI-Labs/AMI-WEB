"""Page content extraction and HTML processing."""

import asyncio
from typing import Any

from browser.backend.facade.base import BaseController
from browser.backend.facade.utils import parameterized_js_execution
from browser.backend.utils.exceptions import NavigationError
from browser.backend.utils.parser import HTMLParser


class ContentExtractor(BaseController):
    """Handles extraction of page content and HTML processing."""

    async def get_page_source(self) -> str:
        """Get the full HTML source of the page."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                return str(self.driver.page_source)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: str(self.driver.page_source) if self.driver else "")
        except Exception as e:
            raise NavigationError(f"Failed to get page source: {e}") from e

    async def get_page_content(self) -> str:
        """Get the full HTML content of the page."""
        return await self.get_page_source()

    async def get_element_html(self, selector: str) -> str:
        """Get the inner HTML of a specific element.

        Args:
            selector: CSS selector for the element

        Returns:
            Inner HTML of the element
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = parameterized_js_execution("return document.querySelector({selector}).innerHTML", selector=selector)
            result = await self.execute_script(script)
            return str(result) if result is not None else ""
        except Exception as e:
            raise NavigationError(f"Failed to get element HTML: {e}") from e

    async def get_element_text(self, selector: str) -> str:
        """Get the text content of a specific element.

        Args:
            selector: CSS selector for the element

        Returns:
            Text content of the element
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = parameterized_js_execution("return document.querySelector({selector}).textContent", selector=selector)
            result = await self.execute_script(script)
            return str(result) if result is not None else ""
        except Exception as e:
            raise NavigationError(f"Failed to get element text: {e}") from e

    async def get_text_with_tags(
        self,
        selector: str | None = None,
        ellipsize_text_after: int = 128,
        include_tag_names: bool = True,
        skip_hidden: bool = True,
        max_depth: int | None = None,
    ) -> str:
        """Get text content with element tags and auto-ellipsization.

        Args:
            selector: CSS selector for root element (null = document.body)
            ellipsize_text_after: Truncate each element's text after N chars
            include_tag_names: Prefix each text with element tag name
            skip_hidden: Skip hidden/invisible elements
            max_depth: Maximum DOM depth to traverse

        Returns:
            Text content with tags, one line per element
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        function getTextWithTags(element, depth, maxDepth, ellipsizeAfter, includeTags, skipHidden) {
            // Skip script/style/noscript nodes
            if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(element.tagName)) {
                return '';
            }

            // Skip hidden elements (not rendered)
            if (skipHidden && element.offsetParent === null && element.tagName !== 'BODY') {
                return '';
            }

            // Get direct text nodes only (not from children)
            let text = Array.from(element.childNodes)
                .filter(n => n.nodeType === 3) // Text nodes only
                .map(n => n.textContent.trim())
                .filter(t => t.length > 0)
                .join(' ');

            // Ellipsize if needed
            if (text && ellipsizeAfter && text.length > ellipsizeAfter) {
                text = text.substring(0, ellipsizeAfter) + '...';
            }

            let result = '';
            if (text) {
                if (includeTags) {
                    const tag = element.tagName.toLowerCase();
                    const id = element.id ? `#${element.id}` : '';
                    const cls = element.className && typeof element.className === 'string'
                        ? `.${element.className.split(' ')[0]}`
                        : '';
                    result = `${tag}${id}${cls}: ${text}\n`;
                } else {
                    result = `${text}\n`;
                }
            }

            // Recurse to children
            if (!maxDepth || depth < maxDepth) {
                for (let child of element.children) {
                    result += getTextWithTags(child, depth + 1, maxDepth, ellipsizeAfter, includeTags, skipHidden);
                }
            }

            return result;
        }

        const selector = arguments[0];
        const ellipsizeAfter = arguments[1];
        const includeTags = arguments[2];
        const skipHidden = arguments[3];
        const maxDepth = arguments[4];

        const element = selector ? document.querySelector(selector) : document.body;
        if (!element) {
            return '';
        }

        return getTextWithTags(element, 0, maxDepth, ellipsizeAfter, includeTags, skipHidden);
        """

        try:
            result = await self.execute_script(script, selector, ellipsize_text_after, include_tag_names, skip_hidden, max_depth)
            return str(result) if result is not None else ""
        except Exception as e:
            raise NavigationError(f"Failed to get text with tags: {e}") from e

    async def execute_script(self, script: str, *args: Any, async_script: bool = False) -> Any:
        """Execute JavaScript in the page context.

        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script
            async_script: If True, use execute_async_script

        Returns:
            Result of script execution
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                if async_script:
                    return self.driver.execute_async_script(script, *args)
                return self.driver.execute_script(script, *args)

            loop = asyncio.get_event_loop()
            if async_script:
                return await loop.run_in_executor(None, lambda: self.driver.execute_async_script(script, *args) if self.driver else None)
            return await loop.run_in_executor(None, lambda: self.driver.execute_script(script, *args) if self.driver else None)
        except Exception as e:
            raise NavigationError(f"Failed to execute script: {e}") from e

    async def get_html_with_depth_limit(self, max_depth: int | None = None, collapse_depth: int | None = None, ellipsize_text_after: int | None = None) -> str:
        """Get HTML with depth limitations to reduce size.

        Args:
            max_depth: Maximum depth to traverse (stops at this depth)
            collapse_depth: Depth at which to collapse elements to summaries
            ellipsize_text_after: Truncate text content after this many characters (for structure extraction)

        Returns:
            HTML string with depth limitations applied
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        function getHtmlWithDepth(element, currentDepth, maxDepth, collapseDepth, ellipsizeAfter) {
            if (maxDepth && currentDepth > maxDepth) {
                return '';
            }

            if (collapseDepth && currentDepth >= collapseDepth) {
                // Collapse to summary
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

            // Add children or text content
            if (element.children.length > 0) {
                for (let child of element.children) {
                    html += getHtmlWithDepth(child, currentDepth + 1, maxDepth, collapseDepth, ellipsizeAfter);
                }
            } else if (element.textContent) {
                let text = element.textContent;
                // Ellipsize text content if configured
                if (ellipsizeAfter && text.length > ellipsizeAfter) {
                    text = text.substring(0, ellipsizeAfter) + '...';
                }
                html += text;
            }

            html += '</' + element.tagName.toLowerCase() + '>';
            return html;
        }

        const maxDepth = arguments[0];
        const collapseDepth = arguments[1];
        const ellipsizeAfter = arguments[2];
        return getHtmlWithDepth(document.documentElement, 0, maxDepth, collapseDepth, ellipsizeAfter);
        """

        try:
            result = await self.execute_script(script, max_depth, collapse_depth, ellipsize_text_after)
            return str(result) if result is not None else ""
        except Exception as e:
            raise NavigationError(f"Failed to get HTML with depth limit: {e}") from e

    async def get_parsed_html(self, max_depth: int | None = None, max_tokens: int = 25000) -> str:  # noqa: ARG002
        """Get parsed and limited HTML suitable for LLM consumption.

        Args:
            max_depth: Maximum depth to traverse
            max_tokens: Maximum tokens (approx 4 chars per token)

        Returns:
            Parsed and limited HTML
        """
        # Note: max_tokens and max_depth are not supported yet
        # For now, just return the HTML as-is
        # TODO: Implement token/depth limiting
        return await self.get_page_source()

    async def get_text(self) -> str:
        """Get the text content of the page.

        Returns:
            Text content of the page
        """
        return await self.extract_text()

    async def extract_text(
        self,
        preserve_structure: bool = True,
        remove_scripts: bool = True,
        remove_styles: bool = True,
        remove_comments: bool = True,
        max_whitespace: int = 2,
    ) -> str:
        """Extract human-readable text from the current page.

        Args:
            preserve_structure: Keep paragraph/line breaks
            remove_scripts: Remove script tags and content
            remove_styles: Remove style tags and content
            remove_comments: Remove HTML comments
            max_whitespace: Maximum consecutive whitespace chars

        Returns:
            Extracted text content
        """
        html = await self.get_page_source()
        parser = HTMLParser(html)
        return parser.extract_text(
            preserve_structure=preserve_structure,
            remove_scripts=remove_scripts,
            remove_styles=remove_styles,
            remove_comments=remove_comments,
            max_whitespace=max_whitespace,
        )

    async def extract_links(self, absolute: bool = True) -> list[dict[str, str]]:
        """Extract all links from the page.

        Args:
            absolute: If True, convert relative URLs to absolute

        Returns:
            List of dictionaries with 'href' and 'text' keys
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        const links = Array.from(document.querySelectorAll('a[href]'));
        const absolute = arguments[0];

        return links.map(link => {
            let href = link.href;
            if (!absolute && link.getAttribute('href').startsWith('/')) {
                href = link.getAttribute('href');
            }
            return {
                href: href,
                text: link.textContent.trim(),
                title: link.title || ''
            };
        });
        """

        try:
            result = await self.execute_script(script, absolute)
            return result if isinstance(result, list) else []
        except Exception as e:
            raise NavigationError(f"Failed to extract links: {e}") from e

    async def extract_images(self) -> list[dict[str, str]]:
        """Extract all images from the page.

        Returns:
            List of dictionaries with image information
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        const images = Array.from(document.querySelectorAll('img'));
        return images.map(img => ({
            src: img.src,
            alt: img.alt,
            width: img.naturalWidth,
            height: img.naturalHeight,
            title: img.title || ''
        }));
        """

        try:
            result = await self.execute_script(script)
            return result if isinstance(result, list) else []
        except Exception as e:
            raise NavigationError(f"Failed to extract images: {e}") from e

    async def extract_forms(self) -> list[dict[str, Any]]:
        """Extract all forms from the page.

        Returns:
            List of dictionaries containing form information
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        const forms = Array.from(document.querySelectorAll('form'));
        return forms.map(form => {
            const fields = Array.from(form.elements).map(el => ({
                name: el.name || '',
                type: el.type || el.tagName.toLowerCase(),
                id: el.id || '',
                value: el.value || '',
                required: el.required || false,
                hint: el.placeholder || ''
            }));
            return {
                id: form.id || '',
                name: form.name || '',
                action: form.action || '',
                method: form.method || 'get',
                fields: fields
            };
        });
        """

        try:
            return await self.execute_script(script) or []
        except Exception as e:
            raise NavigationError(f"Failed to extract forms: {e}") from e
