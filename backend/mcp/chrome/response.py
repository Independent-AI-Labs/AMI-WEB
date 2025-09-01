"""Browser MCP response models."""

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from typing import Any  # noqa: E402

from base.backend.mcp.core.response import MCPResponse  # noqa: E402
from pydantic import Field  # noqa: E402


class BrowserResponse(MCPResponse):
    """Response model for browser operations."""

    instance_id: str | None = Field(default=None, description="Browser instance ID")
    url: str | None = Field(default=None, description="Current page URL")
    screenshot: str | None = Field(default=None, description="Base64 encoded screenshot")
    element_count: int | None = Field(default=None, description="Number of elements found")
    text: str | None = Field(default=None, description="Extracted text content")
    cookies: list[dict[str, Any | None]] | None = Field(default=None, description="Browser cookies")
    result: Any = Field(default=None, description="Operation result")
