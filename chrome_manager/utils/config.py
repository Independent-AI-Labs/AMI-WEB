import json
import os
import platform
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class Config:
    def __init__(self, data: dict[str, Any] | None = None):
        self._data = data or self._get_defaults()

    @classmethod
    def load(cls, config_file: str) -> "Config":
        config_path = Path(config_file)

        if not config_path.exists():
            logger.warning(f"Config file {config_file} not found, using defaults")
            return cls()

        try:
            with config_path.open() as f:
                if config_path.suffix in {".yaml", ".yml"}:
                    data = yaml.safe_load(f)
                elif config_path.suffix == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config format: {config_path.suffix}")

            return cls(data)
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
            return cls()

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return self._get_env_override(key, default)
            else:
                return self._get_env_override(key, default)

        result = self._get_env_override(key, value if value is not None else default)

        # Convert relative paths to absolute for key browser paths
        if result and isinstance(result, str) and key in ["chrome_manager.browser.chrome_binary_path", "chrome_manager.browser.chromedriver_path"]:
            path = Path(result)
            if not path.is_absolute():
                # Make relative paths relative to project root
                project_root = Path(__file__).parent.parent.parent
                result = str(project_root / path)

        return result

    def _get_env_override(self, key: str, default: Any) -> Any:
        env_key = f"CHROME_MANAGER_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)

        if env_value is not None:
            try:
                return json.loads(env_value)
            except (json.JSONDecodeError, ValueError):
                return env_value

        return default

    def _get_platform_paths(self) -> tuple[str | None, str | None]:
        """Get platform-specific default paths for Chrome and ChromeDriver."""
        system = platform.system()

        # Look for local project binaries first
        project_root = Path(__file__).parent.parent.parent

        if system == "Windows":
            chrome_path = project_root / "build" / "chromium-win" / "chrome.exe"
            driver_path = project_root / "build" / "chromedriver.exe"
        elif system == "Darwin":  # macOS
            chrome_path = project_root / "chromium-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
            driver_path = project_root / "build" / "chromedriver"
        else:  # Linux
            chrome_path = project_root / "chromium-linux" / "chrome"
            driver_path = project_root / "build" / "chromedriver"

        # Return paths if they exist, otherwise None for auto-detection
        chrome = str(chrome_path) if chrome_path.exists() else None
        driver = str(driver_path) if driver_path.exists() else None

        return chrome, driver

    def _get_defaults(self) -> dict[str, Any]:
        chrome_path, driver_path = self._get_platform_paths()

        return {
            "chrome_manager": {
                "browser": {
                    "chrome_binary_path": chrome_path,  # Platform-specific or None
                    "chromedriver_path": driver_path,  # Platform-specific or None
                    "default_headless": True,
                    "default_window_size": [1920, 1080],
                    "user_agent": None,
                },
                "pool": {
                    "min_instances": 1,
                    "max_instances": 10,
                    "warm_instances": 2,
                    "instance_ttl": 3600,
                    "health_check_interval": 30,
                },
                "performance": {
                    "max_memory_per_instance": 512,
                    "max_cpu_per_instance": 25,
                    "page_load_timeout": 30,
                    "script_timeout": 10,
                },
                "storage": {
                    "session_dir": "./data/sessions",
                    "screenshot_dir": "./data/screenshots",
                    "video_dir": "./data/videos",
                    "log_dir": "./data/logs",
                    "profiles_dir": "./data/browser_profiles",
                    "download_dir": "./data/downloads",
                    # Test-specific paths
                    "test_profiles_dir": "./data/test_profiles",
                    "test_download_dir": "./data/test_downloads",
                },
                "mcp": {
                    "server_host": "127.0.0.1",  # Secure: Only bind to localhost
                    "server_port": 8765,
                    "max_connections": 100,
                    "auth_required": False,
                    "tls_enabled": False,
                    "ping_interval": 30,
                    "ping_timeout": 10,
                },
                "chrome_options": {
                    "arguments": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        # SECURITY: Removed dangerous flags that disable security
                        # Only add these for specific test scenarios, not as defaults
                    ],
                    "experimental_options": {
                        "excludeSwitches": ["enable-automation"],
                        "useAutomationExtension": False,
                    },
                    "prefs": {
                        "credentials_enable_service": False,
                        "profile.password_manager_enabled": False,
                        "profile.default_content_setting_values.notifications": 2,
                    },
                },
            }
        }
