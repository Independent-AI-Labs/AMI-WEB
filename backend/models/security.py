"""Security and TLS configuration models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TLSVersion(str, Enum):
    """TLS version options."""

    TLS_1_0 = "1.0"
    TLS_1_1 = "1.1"
    TLS_1_2 = "1.2"
    TLS_1_3 = "1.3"
    ANY = "any"


class SecurityLevel(str, Enum):
    """Browser security level presets."""

    STRICT = "strict"  # Enforce all security checks
    STANDARD = "standard"  # Default Chrome security
    RELAXED = "relaxed"  # Allow self-signed certs
    PERMISSIVE = "permissive"  # Allow all connections


class SecurityConfig(BaseModel):
    """Security configuration for browser instances."""

    # Security level preset
    level: SecurityLevel = Field(default=SecurityLevel.STANDARD)

    # Certificate validation
    ignore_certificate_errors: bool = Field(default=False)
    allow_insecure_localhost: bool = Field(default=True)
    accept_insecure_certs: bool = Field(default=False)

    # TLS configuration
    min_tls_version: TLSVersion = Field(default=TLSVersion.TLS_1_2)
    max_tls_version: TLSVersion = Field(default=TLSVersion.TLS_1_3)

    # Mixed content
    allow_running_insecure_content: bool = Field(default=False)
    allow_mixed_content: bool = Field(default=False)

    # Safe browsing
    safe_browsing_enabled: bool = Field(default=True)
    safe_browsing_enhanced: bool = Field(default=False)

    # Download protection
    download_protection_enabled: bool = Field(default=True)
    download_warnings_enabled: bool = Field(default=True)

    # Site isolation
    site_isolation_enabled: bool = Field(default=True)
    isolate_origins: list[str] = Field(default_factory=list)

    # CORS and CSP
    disable_web_security: bool = Field(default=False)
    disable_csp: bool = Field(default=False)

    # Permissions
    allow_geolocation: bool = Field(default=False)
    allow_notifications: bool = Field(default=False)
    allow_media_devices: bool = Field(default=False)

    @classmethod
    def from_level(cls, level: SecurityLevel) -> "SecurityConfig":
        """Create security config from a preset level."""
        if level == SecurityLevel.STRICT:
            return cls(
                level=level,
                ignore_certificate_errors=False,
                allow_insecure_localhost=False,
                accept_insecure_certs=False,
                min_tls_version=TLSVersion.TLS_1_2,
                allow_running_insecure_content=False,
                safe_browsing_enabled=True,
                safe_browsing_enhanced=True,
                download_protection_enabled=True,
                site_isolation_enabled=True,
                disable_web_security=False,
            )
        if level == SecurityLevel.RELAXED:
            return cls(
                level=level,
                ignore_certificate_errors=True,
                allow_insecure_localhost=True,
                accept_insecure_certs=True,
                min_tls_version=TLSVersion.TLS_1_0,
                allow_running_insecure_content=False,
                safe_browsing_enabled=True,
                download_protection_enabled=True,
                site_isolation_enabled=True,
                disable_web_security=False,
            )
        if level == SecurityLevel.PERMISSIVE:
            return cls(
                level=level,
                ignore_certificate_errors=True,
                allow_insecure_localhost=True,
                accept_insecure_certs=True,
                min_tls_version=TLSVersion.ANY,
                allow_running_insecure_content=True,
                allow_mixed_content=True,
                safe_browsing_enabled=False,
                download_protection_enabled=False,
                site_isolation_enabled=False,
                disable_web_security=True,
                disable_csp=True,
            )
        # STANDARD
        return cls(level=level)

    def to_chrome_args(self) -> list[str]:
        """Convert security config to Chrome command-line arguments."""
        args = []

        if self.ignore_certificate_errors:
            args.append("--ignore-certificate-errors")
            args.append("--ignore-certificate-errors-spki-list")

        if self.allow_insecure_localhost:
            args.append("--allow-insecure-localhost")

        if self.accept_insecure_certs:
            args.append("--accept-insecure-certs")

        if self.allow_running_insecure_content:
            args.append("--allow-running-insecure-content")

        if self.disable_web_security:
            args.append("--disable-web-security")
            args.append("--disable-features=IsolateOrigins,site-per-process")
        elif self.site_isolation_enabled and self.isolate_origins:
            origins = ",".join(self.isolate_origins)
            args.append(f"--isolate-origins={origins}")

        if not self.site_isolation_enabled:
            args.append("--disable-site-isolation-trials")

        # TLS version settings
        if self.min_tls_version != TLSVersion.ANY:
            args.append(f"--ssl-version-min=tls{self.min_tls_version.replace('.', '')}")

        return args

    def to_chrome_prefs(self) -> dict[str, Any]:
        """Convert security config to Chrome preferences."""
        prefs: dict[str, Any] = {}

        # Safe browsing settings
        prefs["safebrowsing.enabled"] = self.safe_browsing_enabled
        prefs["safebrowsing.enhanced"] = self.safe_browsing_enhanced
        prefs[
            "safebrowsing.disable_download_protection"
        ] = not self.download_protection_enabled

        # Download settings
        prefs["download.prompt_for_download"] = False
        prefs["download.directory_upgrade"] = True

        # Permission settings - Chrome expects integer values for content settings
        if not self.allow_notifications:
            prefs.setdefault("profile.default_content_setting_values", {})[
                "notifications"
            ] = 2

        if not self.allow_geolocation:
            prefs.setdefault("profile.default_content_setting_values", {})[
                "geolocation"
            ] = 2

        if not self.allow_media_devices:
            prefs.setdefault("profile.default_content_setting_values", {})[
                "media_stream_camera"
            ] = 2
            prefs.setdefault("profile.default_content_setting_values", {})[
                "media_stream_mic"
            ] = 2

        return prefs

    def to_capabilities(self) -> dict[str, Any]:
        """Convert to WebDriver capabilities."""
        caps = {}

        if self.accept_insecure_certs:
            caps["acceptInsecureCerts"] = True

        return caps
