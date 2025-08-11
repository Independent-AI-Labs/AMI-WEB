"""Browser properties model for runtime configuration."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
        ]
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
                    {"type": "application/pdf", "suffixes": "pdf", "description": "Portable Document Format"},
                    {"type": "text/pdf", "suffixes": "pdf", "description": "Portable Document Format"},
                ],
            ),
            PluginInfo(
                name="Chrome PDF Viewer",
                filename="mhjfbmdgcfjbbpaeojofohoefgiehjai",
                description="",
                mime_types=[
                    {"type": "application/pdf", "suffixes": "pdf", "description": "Portable Document Format"},
                    {"type": "text/pdf", "suffixes": "pdf", "description": "Portable Document Format"},
                ],
            ),
            PluginInfo(
                name="Native Client",
                filename="internal-nacl-plugin",
                description="",
                mime_types=[
                    {"type": "application/x-nacl", "suffixes": "", "description": "Native Client Executable"},
                    {"type": "application/x-pnacl", "suffixes": "", "description": "Portable Native Client Executable"},
                ],
            ),
        ]
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
            "brands": [{"brand": "Not_A Brand", "version": "8"}, {"brand": "Chromium", "version": "120"}, {"brand": "Google Chrome", "version": "120"}],
            "mobile": False,
            "platform": "Windows",
            "platformVersion": "10.0.0",
            "architecture": "x86",
            "bitness": "64",
            "wow64": False,
        }
    )

    # Do Not Track
    do_not_track: str | None = None  # "1" to enable, None to disable

    # Advanced Chrome Arguments (additional)
    extra_chrome_args: list[str] = Field(default_factory=list)

    # Advanced Preferences
    extra_prefs: dict[str, Any] = Field(default_factory=dict)

    def to_injection_script(self) -> str:
        """Generate JavaScript injection script from properties."""
        script_parts = []

        # User agent override
        if self.user_agent:
            script_parts.append(
                f"""
                Object.defineProperty(navigator, 'userAgent', {{
                    get: () => '{self.user_agent}',
                    configurable: true
                }});
            """
            )

        # Platform override
        script_parts.append(
            f"""
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{self.platform}',
                configurable: true
            }});
        """
        )

        # Language overrides
        script_parts.append(
            f"""
            Object.defineProperty(navigator, 'language', {{
                get: () => '{self.language}',
                configurable: true
            }});
            Object.defineProperty(navigator, 'languages', {{
                get: () => {self.languages},
                configurable: true
            }});
        """
        )

        # Hardware concurrency
        script_parts.append(
            f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {self.hardware_concurrency},
                configurable: true
            }});
        """
        )

        # Device memory
        if self.device_memory:
            script_parts.append(
                f"""
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {self.device_memory},
                    configurable: true
                }});
            """
            )

        # WebGL spoofing
        script_parts.append(
            f"""
            (function() {{
                var originalGetContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function() {{
                    var context = originalGetContext.apply(this, arguments);
                    if (context && (arguments[0] === 'webgl' || arguments[0] === 'webgl2' || arguments[0] === 'experimental-webgl')) {{
                        if (context.getParameter) {{
                            var originalGetParameter = context.getParameter.bind(context);
                            context.getParameter = function(pname) {{
                                // UNMASKED_VENDOR_WEBGL
                                if (pname === 0x9245) return '{self.webgl_vendor}';
                                // UNMASKED_RENDERER_WEBGL
                                if (pname === 0x9246) return '{self.webgl_renderer}';
                                // VERSION
                                if (pname === 0x1F02) return '{self.webgl_version}';
                                // SHADING_LANGUAGE_VERSION
                                if (pname === 0x8B8C) return '{self.webgl_shading_language_version}';
                                return originalGetParameter(pname);
                            }};
                        }}

                        // Override getSupportedExtensions
                        if (context.getSupportedExtensions) {{
                            context.getSupportedExtensions = function() {{
                                return {self.webgl_extensions};
                            }};
                        }}
                    }}
                    return context;
                }};
            }})();
        """
        )

        # Codec support
        codec_map = {
            "h264": ['video/mp4; codecs="avc1"', 'video/mp4; codecs="avc1.42E01E"'],
            "h265": ['video/mp4; codecs="hev1"', 'video/mp4; codecs="hvc1"'],
            "vp8": ['video/webm; codecs="vp8"'],
            "vp9": ['video/webm; codecs="vp9"'],
            "av1": ['video/mp4; codecs="av01"'],
            "opus": ['audio/webm; codecs="opus"', 'audio/ogg; codecs="opus"'],
            "vorbis": ['audio/ogg; codecs="vorbis"'],
            "aac": ['audio/mp4; codecs="mp4a.40.2"'],
            "mp3": ["audio/mpeg"],
            "flac": ["audio/flac"],
        }

        script_parts.append(
            """
            (function() {
                var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
                HTMLMediaElement.prototype.canPlayType = function(type) {
                    if (!type) return '';
                    var codecSupport = """
            + str({codec: formats for codec, formats in codec_map.items() if getattr(self.codec_support, codec)})
            + """;

                    for (var codec in codecSupport) {
                        for (var i = 0; i < codecSupport[codec].length; i++) {
                            if (type.toLowerCase().indexOf(codecSupport[codec][i].toLowerCase()) !== -1) {
                                return 'probably';
                            }
                        }
                    }

                    return originalCanPlayType ? originalCanPlayType.apply(this, arguments) : '';
                };
            })();
        """
        )

        # Battery API
        if self.battery_level is not None:
            script_parts.append(
                f"""
                navigator.getBattery = async function() {{
                    return {{
                        level: {self.battery_level},
                        charging: {str(self.battery_charging).lower()},
                        chargingTime: Infinity,
                        dischargingTime: Infinity,
                        addEventListener: function() {{}},
                        removeEventListener: function() {{}}
                    }};
                }};
            """
            )

        # Connection API
        script_parts.append(
            f"""
            if (navigator.connection) {{
                Object.defineProperty(navigator.connection, 'effectiveType', {{
                    get: () => '{self.effective_type}',
                    configurable: true
                }});
                Object.defineProperty(navigator.connection, 'downlink', {{
                    get: () => {self.downlink},
                    configurable: true
                }});
                Object.defineProperty(navigator.connection, 'rtt', {{
                    get: () => {self.rtt},
                    configurable: true
                }});
                Object.defineProperty(navigator.connection, 'saveData', {{
                    get: () => {str(self.save_data).lower()},
                    configurable: true
                }});
            }}
        """
        )

        return "\n".join(script_parts)

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


def get_preset_properties(preset: BrowserPropertiesPreset) -> BrowserProperties:
    """Get predefined browser properties for a preset."""
    if preset == BrowserPropertiesPreset.WINDOWS_CHROME:
        return BrowserProperties(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            platform="Win32",
            webgl_vendor=WebGLVendor.GOOGLE_INTEL,
            webgl_renderer=WebGLRenderer.ANGLE_INTEL_UHD,
            screen_resolution=(1920, 1080),
            hardware_concurrency=8,
        )
    if preset == BrowserPropertiesPreset.MAC_SAFARI:
        return BrowserProperties(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            platform="MacIntel",
            vendor="Apple Computer, Inc.",
            webgl_vendor=WebGLVendor.APPLE,
            webgl_renderer=WebGLRenderer.APPLE_M1,
            screen_resolution=(2560, 1600),
            hardware_concurrency=8,
            plugins=[],  # Safari has no plugins
        )
    if preset == BrowserPropertiesPreset.STEALTH:
        # Maximum anti-detection settings
        return BrowserProperties(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
