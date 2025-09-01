from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class ImageFormat(Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class VideoCodec(Enum):
    H264 = "h264"
    VP8 = "vp8"
    VP9 = "vp9"


class ScreenshotOptions(BaseModel):
    format: ImageFormat = ImageFormat.PNG
    quality: int = 100
    full_page: bool = False
    clip: dict[str, Any] | None = None


class VideoOptions(BaseModel):
    fps: int = 30
    codec: VideoCodec = VideoCodec.H264
    bitrate: int | None = None
    audio: bool = False


class RecordingSession(BaseModel):
    session_id: str
    output_path: str
    started_at: str
    status: Literal["recording", "paused", "stopped"]
    duration: float = 0.0
    frame_count: int = 0
