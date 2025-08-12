"""Browser options builder - handles Chrome options configuration."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger
from selenium.webdriver.chrome.options import Options

from ...models.browser import ChromeOptions
from ...models.browser_properties import BrowserProperties
from ...models.security import SecurityConfig
from ...utils.config import Config

if TYPE_CHECKING:
    from ..management.profile_manager import ProfileManager


class BrowserOptionsBuilder:
    """Builds Chrome options for different configurations."""

    def __init__(self, config: Config | None = None, profile_manager: "ProfileManager | None" = None):
        self._config = config or Config()
        self._profile_manager = profile_manager

    def build(
        self,
        headless: bool = True,
        profile: str | None = None,
        extensions: list[str] | None = None,
        options: ChromeOptions | None = None,
        anti_detect: bool = False,
        browser_properties: BrowserProperties | None = None,
        download_dir: Path | None = None,
        security_config: SecurityConfig | None = None,
    ) -> Options:
        """Build Chrome options based on configuration."""
        chrome_options = Options()

        # Add basic options
        self._add_basic_options(chrome_options, headless)

        # Add profile if specified
        if profile and self._profile_manager:
            profile_dir = self._profile_manager.get_profile_dir(profile)
            if profile_dir:
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")

        # Configure based on mode
        if anti_detect:
            self._configure_anti_detect_mode(chrome_options, headless)
        else:
            self._configure_standard_mode(chrome_options, headless)

        # Apply custom options
        if options:
            self._apply_custom_options(chrome_options, options, extensions or [])

        # Add extensions
        if extensions:
            for ext_path in extensions:
                if Path(ext_path).exists():
                    chrome_options.add_extension(ext_path)

        # Apply preferences
        prefs = self._build_preferences(download_dir, browser_properties, security_config)
        if prefs:
            chrome_options.add_experimental_option("prefs", prefs)

        # Set logging preferences
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})

        return chrome_options

    def _add_basic_options(self, chrome_options: Options, headless: bool) -> None:
        """Add basic Chrome options."""
        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")

    def _add_conditional_options(self, chrome_options: Options) -> None:
        """Add conditional options based on configuration."""
        # Window size
        window_size = self._config.get("chrome_manager.browser.window_size", "1920,1080")
        chrome_options.add_argument(f"--window-size={window_size}")

        # User agent
        user_agent = self._config.get("chrome_manager.browser.user_agent")
        if user_agent:
            chrome_options.add_argument(f"--user-agent={user_agent}")

    def _configure_anti_detect_mode(self, chrome_options: Options, headless: bool) -> None:
        """Configure options for anti-detection mode."""
        from ..security.antidetect import get_anti_detection_arguments

        # Get anti-detection arguments
        anti_args = get_anti_detection_arguments()
        for arg in anti_args:
            chrome_options.add_argument(arg)

        # Add anti-detect extension if not headless
        if not headless:
            self._add_antidetect_extension(chrome_options)

        # Exclude automation switches
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Additional anti-detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    def _configure_standard_mode(self, chrome_options: Options, headless: bool) -> None:
        """Configure options for standard mode."""
        self._add_common_arguments(chrome_options)

        # Headless-specific options
        if headless:
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")

    def _add_common_arguments(self, chrome_options: Options) -> None:
        """Add common Chrome arguments."""
        common_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
            "--disable-extensions-file-access-check",
            "--disable-web-security" if self._config.get("chrome_manager.browser.disable_web_security", False) else None,
            "--disable-features=VizDisplayCompositor",
            "--disable-breakpad",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
        ]

        for arg in common_args:
            if arg:
                chrome_options.add_argument(arg)

    def _add_antidetect_extension(self, chrome_options: Options) -> None:
        """Add the anti-detection extension."""
        ext_path = Path(__file__).parent.parent / "extensions" / "antidetect"
        if ext_path.exists():
            chrome_options.add_argument(f"--load-extension={ext_path}")
            logger.debug(f"Added anti-detect extension from {ext_path}")

    def _apply_custom_options(self, chrome_options: Options, custom: ChromeOptions, extensions: list[str]) -> None:
        """Apply custom Chrome options."""
        # Apply arguments
        if hasattr(custom, "arguments"):
            for arg in custom.arguments:
                chrome_options.add_argument(arg)

        # Apply extensions
        for ext in extensions:
            if Path(ext).exists():
                chrome_options.add_extension(ext)

        # Apply experimental options
        if hasattr(custom, "experimental_options"):
            for key, value in custom.experimental_options.items():
                chrome_options.add_experimental_option(key, value)

    def _build_preferences(
        self, download_dir: Path | None, browser_properties: BrowserProperties | None, security_config: SecurityConfig | None
    ) -> dict[str, Any]:
        """Build Chrome preferences."""
        prefs: dict[str, Any] = {}

        # Download directory
        if download_dir:
            prefs.update(
                {
                    "download.default_directory": str(download_dir),
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True,
                }
            )

        # Security preferences from SecurityConfig
        if security_config:
            # SecurityConfig.to_chrome_prefs() returns security-related preferences
            security_prefs = security_config.to_chrome_prefs()
            prefs.update(security_prefs)

        # Anti-detection preferences
        if browser_properties:
            from ..security.antidetect import get_anti_detection_prefs

            anti_prefs = get_anti_detection_prefs()
            prefs.update(anti_prefs)

        # Additional preferences
        prefs.update(
            {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.media_stream": 2,
            }
        )

        return prefs
