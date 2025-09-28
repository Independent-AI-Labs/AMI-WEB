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
    truncated: bool = Field(default=False, description="True when textual payload was truncated or chunked")
    returned_bytes: int | None = Field(default=None, description="Number of bytes returned in text/result")
    total_bytes_estimate: int | None = Field(default=None, description="Estimated total byte length of original payload")
    chunk_start: int | None = Field(default=None, description="Chunk start byte offset (inclusive)")
    chunk_end: int | None = Field(default=None, description="Chunk end byte offset (exclusive)")
    next_offset: int | None = Field(default=None, description="Next byte offset to request for continuation")
    remaining_bytes: int | None = Field(default=None, description="Remaining bytes after this chunk")
    snapshot_checksum: str | None = Field(default=None, description="SHA256 checksum for the source snapshot")
