"""Video recording functionality for browser sessions."""

import asyncio
import base64
import contextlib
import io
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
from loguru import logger
from PIL import Image

from browser.backend.facade.base import BaseController
from browser.backend.models.media import RecordingSession
from browser.backend.utils.exceptions import MediaError

if TYPE_CHECKING:
    from browser.backend.core.browser.instance import BrowserInstance


class VideoRecorder(BaseController):
    """Controller for video recording operations."""

    def __init__(self, instance: "BrowserInstance") -> None:
        super().__init__(instance)
        self.recording_sessions: dict[str, dict[str, Any]] = {}

    async def start_recording(self, output_path: str, fps: int = 30, codec: str = "h264") -> RecordingSession:
        """Start recording browser session to video.

        Args:
            output_path: Path to save video file
            fps: Frames per second
            codec: Video codec to use

        Returns:
            RecordingSession with session details
        """
        session_id = str(uuid.uuid4())

        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        session = RecordingSession(  # type: ignore[call-arg]
            session_id=session_id,
            output_path=str(output_file),
            fps=fps,
            codec=codec,
            start_time=datetime.now(),
        )

        self.recording_sessions[session_id] = {
            "session": session,
            "writer": None,
            "task": asyncio.create_task(self._record_loop(session_id, str(output_file), fps, codec)),
        }

        logger.info(f"Started recording session {session_id} to {output_path}")
        return session

    async def stop_recording(self, session_id: str) -> RecordingSession:
        """Stop an active recording session.

        Args:
            session_id: ID of the recording session

        Returns:
            RecordingSession with final details
        """
        if session_id not in self.recording_sessions:
            raise MediaError(f"Recording session {session_id} not found")

        recording = self.recording_sessions[session_id]
        recording["session"].status = "stopped"

        if recording["task"]:
            recording["task"].cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await recording["task"]

        if recording["writer"]:
            recording["writer"].release()

        session = recording["session"]
        if not isinstance(session, RecordingSession):
            raise MediaError(f"Invalid session type for {session_id}")
        # Cleanup handled in _record_loop finally block

        logger.info(f"Stopped recording session {session_id}")
        return session

    async def pause_recording(self, session_id: str) -> None:
        """Pause an active recording session.

        Args:
            session_id: ID of the recording session
        """
        if session_id not in self.recording_sessions:
            raise MediaError(f"Recording session {session_id} not found")

        self.recording_sessions[session_id]["session"].status = "paused"
        logger.info(f"Paused recording session {session_id}")

    async def resume_recording(self, session_id: str) -> None:
        """Resume a paused recording session.

        Args:
            session_id: ID of the recording session
        """
        if session_id not in self.recording_sessions:
            raise MediaError(f"Recording session {session_id} not found")

        self.recording_sessions[session_id]["session"].status = "recording"
        logger.info(f"Resumed recording session {session_id}")

    async def _record_loop(self, session_id: str, output_path: str, fps: int, _codec: str) -> None:
        """Recording loop that captures frames.

        Args:
            session_id: ID of the recording session
            output_path: Path to save video
            fps: Frames per second
            codec: Video codec (unused, using mp4v)
        """
        writer = None
        try:
            recording = self.recording_sessions[session_id]
            frame_interval = 1.0 / fps

            if self.driver is None:
                raise RuntimeError("Driver not initialized")
            viewport_size = self.driver.get_window_size()
            width = viewport_size["width"]
            height = viewport_size["height"]

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            recording["writer"] = writer

            start_time = time.time()

            while recording["session"].status != "stopped":
                if recording["session"].status == "recording":
                    if self.driver is None:
                        raise RuntimeError("Driver lost during recording")
                    screenshot_base64 = self.driver.get_screenshot_as_base64()
                    screenshot_bytes = base64.b64decode(screenshot_base64)

                    img = Image.open(io.BytesIO(screenshot_bytes))
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                    writer.write(frame)
                    recording["session"].frame_count += 1
                    recording["session"].duration = time.time() - start_time

                await asyncio.sleep(frame_interval)

        except asyncio.CancelledError:
            logger.debug(f"Recording loop cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Error in recording loop for session {session_id}: {e}")
            # Mark session as error
            if session_id in self.recording_sessions:
                self.recording_sessions[session_id]["session"].status = "error"
        finally:
            if writer:
                writer.release()
            # Always clean up the session from dict to prevent memory leak
            if session_id in self.recording_sessions:
                logger.debug(f"Cleaning up recording session {session_id}")
                del self.recording_sessions[session_id]

    def get_active_sessions(self) -> list[RecordingSession]:
        """Get list of all active recording sessions.

        Returns:
            List of active RecordingSession objects
        """
        return [rec["session"] for rec in self.recording_sessions.values()]

    def get_session(self, session_id: str) -> RecordingSession | None:
        """Get details of a specific recording session.

        Args:
            session_id: ID of the recording session

        Returns:
            RecordingSession or None if not found
        """
        if session_id in self.recording_sessions:
            session = self.recording_sessions[session_id]["session"]
            return session if isinstance(session, RecordingSession) else None
        return None

    async def record_action(self, action: str, duration: float = 5.0, output_path: str | None = None) -> str:
        """Record a specific action for a duration.

        Args:
            action: Description of the action being recorded
            duration: How long to record in seconds
            output_path: Optional output path (auto-generated if not provided)

        Returns:
            Path to the recorded video
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"recordings/action_{action.replace(' ', '_')}_{timestamp}.mp4"

        # Start recording
        session = await self.start_recording(output_path)

        try:
            # Record for specified duration
            await asyncio.sleep(duration)
        finally:
            # Stop recording
            await self.stop_recording(session.session_id)

        logger.info(f"Recorded action '{action}' to {output_path}")
        return output_path

    async def capture_gif(self, duration: float = 3.0, fps: int = 10, output_path: str | None = None) -> str:
        """Capture a GIF animation of the browser.

        Args:
            duration: Duration to capture in seconds
            fps: Frames per second for the GIF
            output_path: Optional output path

        Returns:
            Path to the saved GIF
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"recordings/capture_{timestamp}.gif"

        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        frames = []
        frame_interval = 1.0 / fps
        num_frames = int(duration * fps)

        for _ in range(num_frames):
            # Capture frame
            if self.driver is None:
                raise RuntimeError("Driver not initialized for GIF capture")
            if self._is_in_thread_context():
                screenshot_base64 = self.driver.get_screenshot_as_base64()
            else:
                loop = asyncio.get_event_loop()
                screenshot_base64 = await loop.run_in_executor(None, lambda: self.driver.get_screenshot_as_base64() if self.driver else "")

            screenshot_bytes = base64.b64decode(screenshot_base64)
            img = Image.open(io.BytesIO(screenshot_bytes))
            frames.append(img)

            await asyncio.sleep(frame_interval)

        # Save as GIF
        if frames:
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=int(frame_interval * 1000),  # Duration in milliseconds
                loop=0,
            )

        logger.info(f"Captured GIF to {output_path}")
        return output_path
