"""Service for generating browser property injection scripts."""

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from ..models.browser_properties import BrowserProperties


class PropertyInjectionService:
    """Service for generating browser property injection scripts from templates."""

    def __init__(self):
        """Initialize the service with Jinja2 template environment."""
        template_dir = Path(__file__).parent.parent.parent / "web" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_injection_script(self, properties: "BrowserProperties") -> str:
        """
        Generate JavaScript injection script from browser properties.

        Args:
            properties: Browser properties to inject

        Returns:
            JavaScript code for property injection
        """
        template = self.env.get_template("browser_properties.js")

        # Render template with context
        return template.render(**self._prepare_context(properties))

    def _prepare_context(self, properties: "BrowserProperties") -> dict[str, Any]:
        """
        Prepare template context from browser properties.

        Args:
            properties: Browser properties

        Returns:
            Template context dictionary
        """
        return {
            # Basic properties
            "user_agent": properties.user_agent,
            "platform": properties.platform,
            "hardware_concurrency": properties.hardware_concurrency,
            "device_memory": properties.device_memory,
            "max_touch_points": properties.max_touch_points,
            # Screen properties
            "screen_width": properties.screen_resolution[0],
            "screen_height": properties.screen_resolution[1],
            "color_depth": properties.color_depth,
            "pixel_depth": properties.color_depth,  # Same as color_depth in most cases
            "device_pixel_ratio": properties.pixel_ratio,
            # Languages
            "languages": properties.languages,
            "languages_json": json.dumps(properties.languages) if properties.languages else "[]",
            "primary_language": properties.languages[0] if properties.languages else "en-US",
            # Timezone
            "timezone": properties.timezone,
            "timezone_offset": self._calculate_timezone_offset(properties.timezone) if properties.timezone else 0,
            # WebGL
            "webgl_vendor": properties.webgl_vendor,
            "webgl_renderer": properties.webgl_renderer,
            # Media codecs
            "override_codecs": True,  # We have codec_support
            "video_codecs_json": self._get_video_codecs(properties),
            "audio_codecs_json": self._get_audio_codecs(properties),
            # Battery API
            "battery_charging": properties.battery_charging,
            "battery_charging_json": json.dumps(properties.battery_charging),
            "battery_charging_time": float("inf"),  # Default to infinity
            "battery_discharging_time": float("inf"),  # Default to infinity
            "battery_level": properties.battery_level,
            # Connection API
            "connection_type": properties.connection_type,
            "connection_effective_type": properties.effective_type,
            "connection_downlink": properties.downlink,
            "connection_rtt": properties.rtt,
            "connection_save_data_json": json.dumps(properties.save_data),
            # Permissions
            "override_permissions": True,
            "permissions_json": self._get_permissions_json(properties),
            # Client hints
            "client_hints": properties.client_hints,
            "client_hints_json": json.dumps(properties.client_hints) if properties.client_hints else "{}",
            "client_hints_brands_json": self._prepare_client_hints_brands(properties),
        }

    def _calculate_timezone_offset(self, timezone: str) -> int:
        """
        Calculate timezone offset in minutes.

        Args:
            timezone: Timezone string (e.g., "America/New_York")

        Returns:
            Offset in minutes from UTC
        """
        # This is a simplified implementation
        # In production, use pytz or zoneinfo to get actual offset
        timezone_offsets = {
            "America/New_York": 300,  # -5 hours
            "America/Chicago": 360,  # -6 hours
            "America/Denver": 420,  # -7 hours
            "America/Los_Angeles": 480,  # -8 hours
            "Europe/London": 0,
            "Europe/Paris": -60,  # +1 hour
            "Europe/Moscow": -180,  # +3 hours
            "Asia/Tokyo": -540,  # +9 hours
            "Australia/Sydney": -600,  # +10 hours
        }
        return timezone_offsets.get(timezone, 0)

    def _prepare_client_hints_brands(self, properties: "BrowserProperties") -> str:
        """
        Prepare client hints brands array.

        Args:
            properties: Browser properties

        Returns:
            JSON string of brands array
        """
        if not properties.client_hints or "brands" not in properties.client_hints:
            return "[]"

        brands = properties.client_hints.get("brands", [])
        if isinstance(brands, list):
            return json.dumps(brands)

        # Generate default brands based on user agent
        if properties.user_agent and "Chrome" in properties.user_agent:
            chrome_match = re.search(r"Chrome/(\d+)", properties.user_agent)
            if chrome_match:
                version = chrome_match.group(1)
                return json.dumps(
                    [
                        {"brand": "Not/A)Brand", "version": "99"},
                        {"brand": "Google Chrome", "version": version},
                        {"brand": "Chromium", "version": version},
                    ],
                )

        return "[]"

    def _get_video_codecs(self, properties: "BrowserProperties") -> str:
        """Get video codecs JSON based on codec support."""
        codecs = []
        if properties.codec_support.h264:
            codecs.extend(["h264", "avc1"])
        if properties.codec_support.h265:
            codecs.extend(["h265", "hev1", "hvc1"])
        if properties.codec_support.vp8:
            codecs.append("vp8")
        if properties.codec_support.vp9:
            codecs.append("vp9")
        if properties.codec_support.av1:
            codecs.append("av01")
        return json.dumps(codecs)

    def _get_audio_codecs(self, properties: "BrowserProperties") -> str:
        """Get audio codecs JSON based on codec support."""
        codecs = []
        if properties.codec_support.opus:
            codecs.append("opus")
        if properties.codec_support.vorbis:
            codecs.append("vorbis")
        if properties.codec_support.aac:
            codecs.append("aac")
        if properties.codec_support.mp3:
            codecs.append("mp3")
        if properties.codec_support.flac:
            codecs.append("flac")
        return json.dumps(codecs)

    def _get_permissions_json(self, properties: "BrowserProperties") -> str:
        """Get permissions JSON from individual permission properties."""
        permissions = {}
        if properties.notification_permission != "default":
            permissions["notifications"] = properties.notification_permission
        if properties.geolocation_permission != "prompt":
            permissions["geolocation"] = properties.geolocation_permission
        if properties.camera_permission != "prompt":
            permissions["camera"] = properties.camera_permission
        if properties.microphone_permission != "prompt":
            permissions["microphone"] = properties.microphone_permission
        return json.dumps(permissions)
