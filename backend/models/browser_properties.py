"""Browser properties model for runtime configuration."""

import json
from enum import Enum
from typing import Any

from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from pydantic import BaseModel, Field  # noqa: E402

from browser.backend.services.property_injection import PropertyInjectionService  # noqa: E402


class WebGLVendor(str, Enum):
    """Common WebGL vendors for spoofing."""

    GOOGLE_INTEL = "Google Inc. (Intel)"
    GOOGLE_NVIDIA = "Google Inc. (NVIDIA Corporation)"
    GOOGLE_AMD = "Google Inc. (AMD)"
    GOOGLE_ARM = "Google Inc. (ARM)"
    INTEL = "Intel Inc."
    NVIDIA = "NVIDIA Corporation"
    AMD = "Advanced Micro Devices, Inc."
    APPLE = "Apple Inc."


class WebGLRenderer(str, Enum):
    """Common WebGL renderers for spoofing."""

    ANGLE_INTEL_UHD = "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"
    ANGLE_NVIDIA_GTX = "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    ANGLE_AMD_RADEON = "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    ANGLE_INTEL_IRIS = "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)"
    MESA_INTEL = "Mesa DRI Intel(R) HD Graphics"
    APPLE_M1 = "Apple M1"
    APPLE_M2 = "Apple M2"


class CodecSupport(BaseModel):
    """Media codec support configuration."""

    h264: bool = True
    h265: bool = False
    vp8: bool = True
    vp9: bool = True
    av1: bool = False
    opus: bool = True
    vorbis: bool = True
    aac: bool = True
    mp3: bool = True
    flac: bool = True


class PluginInfo(BaseModel):
    """Browser plugin information."""

    name: str
    filename: str
    description: str = ""
    version: str = ""
    mime_types: list[dict[str, str]] = Field(default_factory=list)


class BrowserProperties(BaseModel):
    """Comprehensive browser properties for spoofing and configuration."""

    # User Agent Configuration
    user_agent: str | None = None
    platform: str = "Win32"
    vendor: str = "Google Inc."
    app_version: str | None = None

    # Language & Locale
    language: str = "en-US"
    languages: list[str] = Field(default_factory=lambda: ["en-US", "en"])

    # Screen & Display
    screen_resolution: tuple[int, int] = (1920, 1080)
    color_depth: int = 24
    pixel_ratio: float = 1.0

    # Hardware & Performance
    hardware_concurrency: int = 8  # Number of CPU cores
    device_memory: int = 8  # GB
    max_touch_points: int = 0

    # WebGL Configuration
    webgl_vendor: str = WebGLVendor.GOOGLE_INTEL
    webgl_renderer: str = WebGLRenderer.ANGLE_INTEL_UHD
    webgl_version: str = "WebGL 2.0"
    webgl_shading_language_version: str = "WebGL GLSL ES 3.00"
    webgl_extensions: list[str] = Field(
        default_factory=lambda: [
            "EXT_color_buffer_float",
            "EXT_color_buffer_half_float",
            "EXT_float_blend",
            "OES_texture_float_linear",
            "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb",
            "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders",
            "WEBGL_lose_context",
        ],
    )

    # Media Codecs
    codec_support: CodecSupport = Field(default_factory=CodecSupport)

    # Plugins
    plugins: list[PluginInfo] = Field(
        default_factory=lambda: [
            PluginInfo(
                name="Chrome PDF Plugin",
                filename="internal-pdf-viewer",
                description="Portable Document Format",
                mime_types=[
                    {
                        "type": "application/pdf",
                        "suffixes": "pdf",
                        "description": "Portable Document Format",
                    },
                    {
                        "type": "text/pdf",
                        "suffixes": "pdf",
                        "description": "Portable Document Format",
                    },
                ],
            ),
            PluginInfo(
                name="Chrome PDF Viewer",
                filename="mhjfbmdgcfjbbpaeojofohoefgiehjai",
                description="",
                mime_types=[
                    {
                        "type": "application/pdf",
                        "suffixes": "pdf",
                        "description": "Portable Document Format",
                    },
                    {
                        "type": "text/pdf",
                        "suffixes": "pdf",
                        "description": "Portable Document Format",
                    },
                ],
            ),
            PluginInfo(
                name="Native Client",
                filename="internal-nacl-plugin",
                description="",
                mime_types=[
                    {
                        "type": "application/x-nacl",
                        "suffixes": "",
                        "description": "Native Client Executable",
                    },
                    {
                        "type": "application/x-pnacl",
                        "suffixes": "",
                        "description": "Portable Native Client Executable",
                    },
                ],
            ),
        ],
    )

    # Browser Features
    webdriver_visible: bool = False  # Whether to show webdriver property
    automation_controlled: bool = False  # Blink automation features

    # Network & Connectivity
    connection_type: str = "ethernet"
    effective_type: str = "4g"
    downlink: float = 10.0  # Mbps
    rtt: int = 50  # Round trip time in ms
    save_data: bool = False

    # Permissions & APIs
    notification_permission: str = "default"  # "granted", "denied", "default"
    geolocation_permission: str = "prompt"
    camera_permission: str = "prompt"
    microphone_permission: str = "prompt"

    # Battery API (null to disable)
    battery_level: float | None = None  # 0.0 to 1.0
    battery_charging: bool | None = None

    # Timezone
    timezone: str | None = None  # e.g., "America/New_York"
    timezone_offset: int | None = None  # Minutes from UTC

    # Canvas Fingerprint
    canvas_noise: bool = False  # Add noise to canvas operations

    # Audio Context
    audio_context_noise: bool = False  # Add noise to audio context

    # Client Hints
    client_hints: dict[str, Any] = Field(
        default_factory=lambda: {
            "brands": [
                {"brand": "Not_A Brand", "version": "8"},
                {"brand": "Chromium", "version": "120"},
                {"brand": "Google Chrome", "version": "120"},
            ],
            "mobile": False,
            "platform": "Windows",
            "platformVersion": "10.0.0",
            "architecture": "x86",
            "bitness": "64",
            "wow64": False,
        },
    )

    # Do Not Track
    do_not_track: str | None = None  # "1" to enable, None to disable

    # Advanced Chrome Arguments (additional)
    extra_chrome_args: list[str] = Field(default_factory=list)

    # Advanced Preferences
    extra_prefs: dict[str, Any] = Field(default_factory=dict)

    def to_injection_script(self) -> str:
        """Generate JavaScript injection script from properties."""

        service = PropertyInjectionService()
        return service.generate_injection_script(self)

    def to_chrome_options(self) -> dict[str, Any]:
        """Convert properties to Chrome options."""
        options: dict[str, Any] = {"args": [], "prefs": {}}

        # User agent
        if self.user_agent:
            options["args"].append(f"--user-agent={self.user_agent}")

        # Language
        options["args"].append(f"--lang={self.language}")

        # Window size from screen resolution
        options["args"].append(f"--window-size={self.screen_resolution[0]},{self.screen_resolution[1]}")

        # Automation flags based on settings
        if not self.automation_controlled:
            options["args"].append("--disable-blink-features=AutomationControlled")

        # Timezone
        if self.timezone:
            options["prefs"]["intl.accept_languages"] = ",".join(self.languages)

        # Notifications
        notification_map = {"granted": 1, "denied": 2, "default": 0}
        options["prefs"]["profile.default_content_setting_values.notifications"] = notification_map.get(self.notification_permission, 0)

        # Extra arguments and preferences
        options["args"].extend(self.extra_chrome_args)
        options["prefs"].update(self.extra_prefs)

        return options


class BrowserPropertiesPreset(str, Enum):
    """Predefined browser property presets."""

    WINDOWS_CHROME = "windows_chrome"
    MAC_SAFARI = "mac_safari"
    LINUX_FIREFOX = "linux_firefox"
    MOBILE_CHROME = "mobile_chrome"
    MOBILE_SAFARI = "mobile_safari"
    STEALTH = "stealth"
    MINIMAL = "minimal"
    CUSTOM = "custom"


def _load_user_agents_config() -> dict[str, Any]:
    """Load user agents configuration from JSON file."""
    config_path = MODULE_ROOT / "config" / "user_agents.json"
    if config_path.exists():
        with config_path.open() as f:
            result: dict[str, Any] = json.load(f)
            return result
    return {"presets": {}, "device_emulation": {}}


def get_preset_properties(preset: BrowserPropertiesPreset) -> BrowserProperties:
    """Get predefined browser properties for a preset."""
    user_agents = _load_user_agents_config()

    if preset == BrowserPropertiesPreset.WINDOWS_CHROME:
        preset_data = user_agents.get("presets", {}).get("windows_chrome", {})
        return BrowserProperties(
            user_agent=preset_data.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
            platform=preset_data.get("platform", "Win32"),
            webgl_vendor=WebGLVendor.GOOGLE_INTEL,
            webgl_renderer=WebGLRenderer.ANGLE_INTEL_UHD,
            screen_resolution=(1920, 1080),
            hardware_concurrency=8,
        )
    if preset == BrowserPropertiesPreset.MAC_SAFARI:
        preset_data = user_agents.get("presets", {}).get("mac_safari", {})
        return BrowserProperties(
            user_agent=preset_data.get(
                "user_agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            ),
            platform=preset_data.get("platform", "MacIntel"),
            vendor="Apple Computer, Inc.",
            webgl_vendor=WebGLVendor.APPLE,
            webgl_renderer=WebGLRenderer.APPLE_M1,
            screen_resolution=(2560, 1600),
            hardware_concurrency=8,
            plugins=[],  # Safari has no plugins
        )
    if preset == BrowserPropertiesPreset.STEALTH:
        # Maximum anti-detection settings
        preset_data = user_agents.get("presets", {}).get("stealth", {})
        return BrowserProperties(
            user_agent=preset_data.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
            webdriver_visible=False,
            automation_controlled=False,
            canvas_noise=True,
            audio_context_noise=True,
            battery_level=0.85,
            battery_charging=True,
        )
    if preset == BrowserPropertiesPreset.MINIMAL:
        # Minimal spoofing, mostly defaults
        return BrowserProperties(webdriver_visible=False, plugins=[])
    # Custom or default
    return BrowserProperties()
