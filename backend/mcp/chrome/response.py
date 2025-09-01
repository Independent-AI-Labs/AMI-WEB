"""Browser MCP response models."""

from typing import Any

# Import base response
from base.backend.mcp.core.response import MCPResponse
from pydantic import Field


class BrowserResponse(MCPResponse):
    """Response model for browser operations."""

    instance_id: str | None = Field(default=None, description="Browser instance ID")
    url: str | None = Field(default=None, description="Current page URL")
    screenshot: str | None = Field(default=None, description="Base64 encoded screenshot")
    element_count: int | None = Field(default=None, description="Number of elements found")
    text: str | None = Field(default=None, description="Extracted text content")
    cookies: list[dict[str, Any | None]] | None = Field(default=None, description="Browser cookies")
    result: Any = Field(default=None, description="Operation result")
