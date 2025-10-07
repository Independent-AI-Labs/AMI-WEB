"""HTML parsing and text extraction utilities."""

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment, Tag
from bs4.element import AttributeValueList, NavigableString, PageElement
from loguru import logger

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

# Size limits to prevent DoS attacks
MAX_HTML_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 1024 * 1024  # 1MB

# Pre-compiled regex patterns for performance
HIDDEN_STYLE_PATTERN = re.compile(r"display:\s*none", re.IGNORECASE)
HIDDEN_CLASS_PATTERN = re.compile(r"hidden|invisible", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r" +")
NEWLINE_CLEANUP_PATTERN = re.compile(r" *\n *")


class HTMLParser:
    """HTML parser with text extraction capabilities."""

    def __init__(self, html: str, max_size: int = MAX_HTML_SIZE):
        """Initialize parser with HTML content.

        Args:
            html: Raw HTML string to parse
            max_size: Maximum allowed HTML size in bytes

        Raises:
            ValueError: If HTML exceeds maximum size
        """
        if len(html) > max_size:
            raise ValueError(f"HTML size ({len(html)} bytes) exceeds maximum allowed size ({max_size} bytes)")

        # Use html.parser for better security, lxml only if explicitly needed
        self.soup = BeautifulSoup(html, "html.parser")
        self._compiled_patterns = {
            "hidden_style": HIDDEN_STYLE_PATTERN,
            "hidden_class": HIDDEN_CLASS_PATTERN,
            "whitespace": WHITESPACE_PATTERN,
            "newline_cleanup": NEWLINE_CLEANUP_PATTERN,
        }

    @classmethod
    def from_url(cls, driver: "WebDriver", url: str | None = None) -> "HTMLParser":
        """Create parser from browser's current page.

        Args:
            driver: Selenium WebDriver instance
            url: Optional URL to navigate to first

        Returns:
            HTMLParser instance with page content
        """
        if url:
            driver.get(url)
        html = driver.page_source
        return cls(html)

    def extract_text(
        self,
        preserve_structure: bool = True,
        remove_scripts: bool = True,
        remove_styles: bool = True,
        remove_comments: bool = True,
        max_whitespace: int = 2,
    ) -> str:
        """Extract human-readable text from HTML.

        Args:
            preserve_structure: Keep paragraph/line breaks
            remove_scripts: Remove script tags and content
            remove_styles: Remove style tags and content
            remove_comments: Remove HTML comments
            max_whitespace: Maximum consecutive whitespace chars

        Returns:
            Cleaned, human-readable text
        """
        # Clone soup to avoid modifying original
        soup = self.soup

        # Remove unwanted elements
        if remove_scripts:
            for script in soup.find_all("script"):
                script.decompose()

        if remove_styles:
            for style in soup.find_all("style"):
                style.decompose()

        if remove_comments:
            # More efficient comment removal using BS4's Comment type

            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

        # Remove hidden elements using pre-compiled patterns
        for hidden in soup.find_all(attrs={"style": self._compiled_patterns["hidden_style"]}):
            hidden.decompose()
        for hidden in soup.find_all(class_=self._compiled_patterns["hidden_class"]):
            hidden.decompose()

        # Extract text
        text = self._extract_with_structure(soup) if preserve_structure else soup.get_text()

        # Limit text length to prevent memory issues
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(f"Extracted text exceeds {MAX_TEXT_LENGTH} chars, truncating")
            text = text[:MAX_TEXT_LENGTH]

        # Clean up whitespace
        text = self._clean_whitespace(text, max_whitespace)

        return text.strip()

    def _extract_with_structure(self, element: Tag | NavigableString | PageElement) -> str:
        """Extract text while preserving document structure.

        Args:
            element: BeautifulSoup element to extract from

        Returns:
            Text with preserved structure
        """
        if isinstance(element, NavigableString):
            return str(element)

        # Handle different element types
        if isinstance(element, Tag):
            return self._handle_element(element)
        return str(element)

    def _handle_element(self, element: Tag | PageElement) -> str:
        """Handle specific element types for text extraction."""
        if not isinstance(element, Tag):
            return str(element)

        # Handle special elements that need specific formatting
        special_handlers = {
            "a": self._handle_link,
            "img": self._handle_image,
        }

        if element.name in special_handlers:
            return special_handlers[element.name](element)

        # Handle elements with specific formatting patterns
        return self._format_element_content(element)

    def _format_element_content(self, element: Tag) -> str:
        """Format element content based on element type."""
        # For elements that don't need content (br, hr)
        if element.name in ["br", "hr"]:
            return "\n"

        # Extract content for all other elements
        content = "".join(self._extract_with_structure(child) for child in element.children if isinstance(child, Tag | NavigableString | PageElement))

        # Apply formatting based on element type
        if element.name in [
            "p",
            "div",
            "section",
            "article",
            "header",
            "footer",
            "li",
            "tr",
        ]:
            return f"\n{content}\n"
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            return f"\n\n{content}\n\n"

        # Default: return content as-is
        return content

    def _handle_link(self, element: Tag) -> str:
        """Handle link element text extraction."""
        text = "".join(self._extract_with_structure(child) for child in element.children if isinstance(child, Tag | NavigableString | PageElement))
        href = element.get("href", "")
        if href and isinstance(href, str) and not href.startswith("#"):
            return f"{text} ({href})"
        if href and isinstance(href, AttributeValueList) and len(href) > 0 and not str(href[0]).startswith("#"):
            return f"{text} ({href[0]})"
        return text

    def _handle_image(self, element: Tag) -> str:
        """Handle image element text extraction."""
        alt = element.get("alt", "")
        if alt:
            return f"[Image: {alt}]"
        return ""

    def _clean_whitespace(self, text: str, max_consecutive: int = 2) -> str:
        """Clean up excessive whitespace.

        Args:
            text: Text to clean
            max_consecutive: Maximum consecutive whitespace characters

        Returns:
            Cleaned text
        """
        # Replace tabs with spaces
        text = text.replace("\t", " ")

        # Replace multiple spaces with single space using pre-compiled pattern
        text = self._compiled_patterns["whitespace"].sub(" ", text)

        # Limit consecutive newlines
        if max_consecutive > 0:
            # Compile pattern once if not cached
            pattern_key = f"newline_{max_consecutive}"
            if pattern_key not in self._compiled_patterns:
                pattern = r"\n{" + str(max_consecutive + 1) + ",}"
                self._compiled_patterns[pattern_key] = re.compile(pattern)

            replacement = "\n" * max_consecutive
            text = self._compiled_patterns[pattern_key].sub(replacement, text)

        # Clean up space around newlines using pre-compiled pattern
        return self._compiled_patterns["newline_cleanup"].sub("\n", text)

    def extract_links(self, absolute: bool = True, base_url: str = "") -> list[dict[str, Any]]:
        """Extract all links from the page.

        Args:
            absolute: Convert relative URLs to absolute
            base_url: Base URL for resolving relative links

        Returns:
            List of dictionaries with 'text', 'href', and 'title' keys
        """
        links: list[dict[str, Any]] = []

        link_iter = cast(Iterable[Tag], self.soup.find_all("a", href=True))
        for link in link_iter:
            href = link.get("href", "")
            if not isinstance(href, str):
                href = str(href) if href else ""

            # Convert to absolute URL if needed using proper URL joining
            if absolute and base_url and href:
                try:
                    # Use urljoin for proper URL resolution
                    if not href.startswith(("http://", "https://", "//", "mailto:", "tel:", "#")):
                        href = urljoin(base_url, href)
                except Exception as e:
                    logger.debug(f"Failed to resolve URL {href}: {e}")

            links.append(
                {
                    "text": link.get_text(strip=True),
                    "href": href,
                    "title": str(link.get("title", "")),
                },
            )

        return links

    def extract_images(self) -> list[dict[str, Any]]:
        """Extract all images from the page.

        Returns:
            List of dictionaries with 'src', 'alt', and 'title' keys
        """
        images: list[dict[str, Any]] = []

        image_iter = cast(Iterable[Tag], self.soup.find_all("img"))
        for img in image_iter:
            images.append(
                {
                    "src": str(img.get("src", "")),
                    "alt": str(img.get("alt", "")),
                    "title": str(img.get("title", "")),
                },
            )

        return images

    def extract_forms(self) -> list[dict[str, Any]]:
        """Extract form information from the page.

        Returns:
            List of form dictionaries with fields and attributes
        """
        forms: list[dict[str, Any]] = []

        form_iter = cast(Iterable[Tag], self.soup.find_all("form"))
        for form in form_iter:
            form_data: dict[str, Any] = {
                "action": str(form.get("action", "")),
                "method": str(form.get("method", "GET")).upper(),
                "id": str(form.get("id", "")),
                "name": str(form.get("name", "")),
                "fields": [],
            }

            # Extract input fields
            field_iter = cast(Iterable[Tag], form.find_all(["input", "textarea", "select"]))
            for input_field in field_iter:
                field: dict[str, Any] = {
                    "type": str(input_field.get("type", "text")) if input_field.name == "input" else input_field.name,
                    "name": str(input_field.get("name", "")),
                    "id": str(input_field.get("id", "")),
                    "value": str(input_field.get("value", "")),
                    "hint": str(input_field.get("placeholder", "")),
                    "required": input_field.has_attr("required"),
                }

                # For select elements, get options
                if input_field.name == "select":
                    option_iter = cast(Iterable[Tag], input_field.find_all("option"))
                    field["options"] = [
                        {
                            "value": str(opt.get("value", "")),
                            "text": opt.get_text(strip=True),
                        }
                        for opt in option_iter
                    ]

                form_data["fields"].append(field)

            forms.append(form_data)

        return forms

    def extract_tables(self) -> list[dict[str, Any]]:
        """Extract table data from the page.

        Returns:
            List of table dictionaries with headers and rows
        """
        tables: list[dict[str, Any]] = []

        table_iter = cast(Iterable[Tag], self.soup.find_all("table"))
        for table in table_iter:
            table_data = self._extract_single_table(table)
            if table_data["headers"] or table_data["rows"]:
                tables.append(table_data)

        return tables

    def _extract_single_table(self, table: Tag) -> dict[str, Any]:
        """Extract data from a single table element."""
        table_data: dict[str, Any] = {"headers": [], "rows": []}

        # Extract headers
        table_data["headers"] = self._extract_table_headers(table)

        # Extract rows
        table_data["rows"] = self._extract_table_rows(table)

        return table_data

    def _extract_table_headers(self, table: Tag) -> list[str]:
        """Extract headers from a table."""
        headers = []
        header_iter = cast(Iterable[Tag], table.find_all("th"))
        for th in header_iter:
            headers.append(th.get_text(strip=True))
        return headers

    def _extract_table_rows(self, table: Tag) -> list[list[str]]:
        """Extract data rows from a table."""
        rows = []
        row_iter = cast(Iterable[Tag], table.find_all("tr"))
        for tr in row_iter:
            row = []
            cell_iter = cast(Iterable[Tag], tr.find_all("td"))
            for td in cell_iter:
                row.append(td.get_text(strip=True))
            if row:
                rows.append(row)
        return rows

    def find_by_text(self, text: str, tag: str | None = None, limit: int = 100) -> list[Any]:
        """Find elements containing specific text.

        Args:
            text: Text to search for
            tag: Optional tag name to limit search
            limit: Maximum number of results to return

        Returns:
            List of matching elements
        """
        # Limit search text length to prevent regex DoS
        max_search_length = 1000
        if len(text) > max_search_length:
            logger.warning(f"Search text too long, truncating to {max_search_length} chars")
            text = text[:max_search_length]

        # Cache compiled pattern for this session
        pattern: re.Pattern[str] = re.compile(re.escape(text), re.IGNORECASE)

        def _matches(node_text: str | None) -> bool:
            if node_text is None:
                return False
            return pattern.search(node_text) is not None

        if tag is not None:
            matches: list[Any] = []
            tag_iter = cast(Iterable[Tag], self.soup.find_all(tag))
            for candidate in tag_iter:
                if _matches(candidate.get_text()):
                    matches.append(candidate)
                    if len(matches) >= limit:
                        break
            return matches
        results_without_tag = self.soup.find_all(string=_matches, limit=limit)
        return list(results_without_tag)

    def get_meta_data(self) -> dict[str, str]:
        """Extract metadata from the page.

        Returns:
            Dictionary of meta tag information
        """
        meta_data = {
            "title": "",
            "description": "",
            "keywords": "",
            "author": "",
            "og:title": "",
            "og:description": "",
            "og:image": "",
        }

        # Get title
        title_tag = self.soup.find("title")
        if title_tag:
            meta_data["title"] = title_tag.get_text(strip=True)

        # Get meta tags
        meta_iter = cast(Iterable[Tag], self.soup.find_all("meta"))
        for meta in meta_iter:
            name = str(meta.get("name", "")).lower()
            property_name = str(meta.get("property", "")).lower()
            content = str(meta.get("content", ""))

            if name in meta_data:
                meta_data[name] = content
            elif property_name in meta_data:
                meta_data[property_name] = content

        return meta_data
