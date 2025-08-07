"""HTML parsing and text extraction utilities."""

import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag


class HTMLParser:
    """HTML parser with text extraction capabilities."""

    def __init__(self, html: str):
        """Initialize parser with HTML content.

        Args:
            html: Raw HTML string to parse
        """
        self.soup = BeautifulSoup(html, "lxml")

    @classmethod
    def from_url(cls, driver, url: str | None = None) -> "HTMLParser":
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
            for comment in soup.find_all(string=lambda text: isinstance(text, NavigableString) and isinstance(text, type(text))):
                if "<!--" in str(comment):
                    comment.extract()

        # Remove hidden elements
        for hidden in soup.find_all(attrs={"style": re.compile(r"display:\s*none", re.I)}):
            hidden.decompose()
        for hidden in soup.find_all(class_=re.compile(r"hidden|invisible", re.I)):
            hidden.decompose()

        # Extract text
        text = self._extract_with_structure(soup) if preserve_structure else soup.get_text()

        # Clean up whitespace
        text = self._clean_whitespace(text, max_whitespace)

        return text.strip()

    def _extract_with_structure(self, element) -> str:
        """Extract text while preserving document structure.

        Args:
            element: BeautifulSoup element to extract from

        Returns:
            Text with preserved structure
        """
        if isinstance(element, NavigableString):
            return str(element)

        # Handle different element types
        return self._handle_element(element)

    def _handle_element(self, element) -> str:
        """Handle specific element types for text extraction."""
        if element.name in ["br", "hr"]:
            return "\n"

        if element.name in ["p", "div", "section", "article", "header", "footer", "li", "tr"]:
            content = "".join(self._extract_with_structure(child) for child in element.children)
            return f"\n{content}\n"

        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            content = "".join(self._extract_with_structure(child) for child in element.children)
            return f"\n\n{content}\n\n"

        if element.name == "a":
            return self._handle_link(element)

        if element.name == "img":
            return self._handle_image(element)

        # Default: recursively extract from children
        return "".join(self._extract_with_structure(child) for child in element.children)

    def _handle_link(self, element) -> str:
        """Handle link element text extraction."""
        text = "".join(self._extract_with_structure(child) for child in element.children)
        href = element.get("href", "")
        if href and not href.startswith("#"):
            return f"{text} ({href})"
        return text

    def _handle_image(self, element) -> str:
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

        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Limit consecutive newlines
        if max_consecutive > 0:
            pattern = r"\n{" + str(max_consecutive + 1) + ",}"
            replacement = "\n" * max_consecutive
            text = re.sub(pattern, replacement, text)

        # Clean up space around newlines
        return re.sub(r" *\n *", "\n", text)

    def extract_links(self, absolute: bool = True, base_url: str = "") -> list[dict[str, Any]]:
        """Extract all links from the page.

        Args:
            absolute: Convert relative URLs to absolute
            base_url: Base URL for resolving relative links

        Returns:
            List of dictionaries with 'text', 'href', and 'title' keys
        """
        links = []

        for link in self.soup.find_all("a", href=True):
            if not isinstance(link, Tag):
                continue
            href = str(link.get("href", ""))

            # Convert to absolute URL if needed
            if absolute and base_url and not href.startswith(("http://", "https://", "//")):
                if href.startswith("/"):
                    # Absolute path
                    from urllib.parse import urlparse

                    parsed = urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                else:
                    # Relative path
                    href = f"{base_url.rstrip('/')}/{href}"

            links.append(
                {
                    "text": link.get_text(strip=True),
                    "href": href,
                    "title": str(link.get("title", "")),
                }
            )

        return links

    def extract_images(self) -> list[dict[str, Any]]:
        """Extract all images from the page.

        Returns:
            List of dictionaries with 'src', 'alt', and 'title' keys
        """
        images = []

        for img in self.soup.find_all("img"):
            if not isinstance(img, Tag):
                continue
            images.append(
                {
                    "src": str(img.get("src", "")),
                    "alt": str(img.get("alt", "")),
                    "title": str(img.get("title", "")),
                }
            )

        return images

    def extract_forms(self) -> list[dict[str, Any]]:
        """Extract form information from the page.

        Returns:
            List of form dictionaries with fields and attributes
        """
        forms = []

        for form in self.soup.find_all("form"):
            if not isinstance(form, Tag):
                continue
            form_data: dict[str, Any] = {
                "action": str(form.get("action", "")),
                "method": str(form.get("method", "GET")).upper(),
                "id": str(form.get("id", "")),
                "name": str(form.get("name", "")),
                "fields": [],
            }

            # Extract input fields
            for input_field in form.find_all(["input", "textarea", "select"]):
                if not isinstance(input_field, Tag):
                    continue
                field: dict[str, Any] = {
                    "type": str(input_field.get("type", "text")) if input_field.name == "input" else input_field.name,
                    "name": str(input_field.get("name", "")),
                    "id": str(input_field.get("id", "")),
                    "value": str(input_field.get("value", "")),
                    "placeholder": str(input_field.get("placeholder", "")),
                    "required": input_field.has_attr("required"),
                }

                # For select elements, get options
                if input_field.name == "select":
                    field["options"] = [
                        {"value": str(opt.get("value", "")), "text": opt.get_text(strip=True)} for opt in input_field.find_all("option") if isinstance(opt, Tag)
                    ]

                form_data["fields"].append(field)

            forms.append(form_data)

        return forms

    def extract_tables(self) -> list[dict[str, Any]]:
        """Extract table data from the page.

        Returns:
            List of table dictionaries with headers and rows
        """
        tables = []

        for table in self.soup.find_all("table"):
            if not isinstance(table, Tag):
                continue

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
        for th in table.find_all("th"):
            if isinstance(th, Tag):
                headers.append(th.get_text(strip=True))
        return headers

    def _extract_table_rows(self, table: Tag) -> list[list[str]]:
        """Extract data rows from a table."""
        rows = []
        for tr in table.find_all("tr"):
            if not isinstance(tr, Tag):
                continue
            row = []
            for td in tr.find_all("td"):
                if isinstance(td, Tag):
                    row.append(td.get_text(strip=True))
            if row:
                rows.append(row)
        return rows

    def find_by_text(self, text: str, tag: str | None = None) -> list[Any]:
        """Find elements containing specific text.

        Args:
            text: Text to search for
            tag: Optional tag name to limit search

        Returns:
            List of matching elements
        """
        if tag:
            return self.soup.find_all(tag, string=re.compile(re.escape(text), re.I))
        return self.soup.find_all(string=re.compile(re.escape(text), re.I))

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
        for meta in self.soup.find_all("meta"):
            if not isinstance(meta, Tag):
                continue
            name = str(meta.get("name", "")).lower()
            property_name = str(meta.get("property", "")).lower()
            content = str(meta.get("content", ""))

            if name in meta_data:
                meta_data[name] = content
            elif property_name in meta_data:
                meta_data[property_name] = content

        return meta_data
