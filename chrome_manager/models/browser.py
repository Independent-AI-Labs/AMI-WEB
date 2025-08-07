from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BrowserStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    CRASHED = "crashed"
    TERMINATED = "terminated"
    STARTING = "starting"


class InstanceInfo(BaseModel):
    id: str
    status: BrowserStatus
    created_at: datetime
    last_activity: datetime
    memory_usage: int = 0
    cpu_usage: float = 0.0
    active_tabs: int = 1
    profile: str | None = None
    headless: bool = True


class PageResult(BaseModel):
    url: str
    title: str
    status_code: int = 200
    load_time: float
    content_length: int = 0
    html: str | None = None


class ClickOptions(BaseModel):
    button: str = "left"
    click_count: int = 1
    delay: int = 0
    offset_x: int | None = None
    offset_y: int | None = None
    wait_after: int = 0


class WaitCondition(BaseModel):
    type: str = "load"
    target: str | None = None
    timeout: int = 30
    poll_frequency: float = 0.5


class ExtensionConfig(BaseModel):
    enabled: bool = True
    permissions: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ChromeOptions(BaseModel):
    headless: bool = True
    window_size: tuple = (1920, 1080)
    user_agent: str | None = None
    proxy: str | None = None
    disable_gpu: bool = True
    no_sandbox: bool = True
    disable_dev_shm_usage: bool = True
    disable_blink_features: list[str] = Field(default_factory=lambda: ["AutomationControlled"])
    arguments: list[str] = Field(default_factory=list)
    experimental_options: dict[str, Any] = Field(default_factory=dict)
    extensions: list[str] = Field(default_factory=list)
    prefs: dict[str, Any] = Field(default_factory=dict)


class TabInfo(BaseModel):
    id: str
    title: str
    url: str
    active: bool = False
    index: int
    window_handle: str


class NetworkEntry(BaseModel):
    timestamp: datetime
    method: str
    url: str
    status_code: int | None = None
    response_time: float | None = None
    size: int | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class ConsoleEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    source: str | None = None
    line_number: int | None = None


class PerformanceMetrics(BaseModel):
    timestamp: datetime
    dom_content_loaded: float
    load_complete: float
    first_paint: float | None = None
    first_contentful_paint: float | None = None
    largest_contentful_paint: float | None = None
    cumulative_layout_shift: float | None = None
    total_blocking_time: float | None = None
