from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class MCPResource(BaseModel):
    name: str
    description: str
    mime_type: str = "application/json"
    uri: str | None = None


class MCPRequest(BaseModel):
    tool: str
    parameters: dict[str, Any]
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class MCPResponse(BaseModel):
    success: bool
    result: Any | None = None
    error: str | None = None
    request_id: str
    execution_time: float


class MCPEvent(BaseModel):
    event_type: str
    instance_id: str | None = None
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
