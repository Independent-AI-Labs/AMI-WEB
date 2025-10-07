import json
import os
import platform
from pathlib import Path
from typing import Any

from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

import yaml  # noqa: E402
from loguru import logger  # noqa: E402


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
        value: Any = self._data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return self._get_env_override(key, default)
            else:
                return self._get_env_override(key, default)

        result = self._get_env_override(key, value if value is not None else default)

        # Convert relative paths to absolute for key browser paths
        if (
            result
            and isinstance(result, str)
            and key
            in [
                "backend.browser.chrome_binary_path",
                "backend.browser.chromedriver_path",
            ]
        ):
            path = Path(result)
            if not path.is_absolute():
                # Make relative paths relative to module root
                result = str(MODULE_ROOT / path)

        return result

    def _get_env_override(self, key: str, default: Any) -> Any:
        env_key = f"backend_{key.upper().replace('.', '_')}"
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

        # Look for local project binaries first (in module root)

        chrome = None
        driver = None

        if system == "Windows":
            # Check for Chrome in multiple locations
            chrome_paths = [
                MODULE_ROOT / "build" / "chromium-win" / "chrome.exe",
                MODULE_ROOT / "build" / "chrome-win64" / "chrome.exe",
            ]
            driver_paths = [
                MODULE_ROOT / "build" / "chromedriver.exe",
                MODULE_ROOT / "build" / "chromedriver-win64" / "chromedriver.exe",
            ]
        elif system == "Darwin":  # macOS
            # Check for Chrome in multiple locations (including our downloaded Chrome 141)
            chrome_paths = []
            # Look for any chrome-mac-* directories in build/
            build_dir = MODULE_ROOT / "build"
            if build_dir.exists():
                for chrome_dir in build_dir.glob("chrome-mac-*"):
                    chrome_paths.append(chrome_dir / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing")
            # Also check alternative install paths
            chrome_paths.extend(
                [
                    MODULE_ROOT / "chromium-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                    MODULE_ROOT / "build" / "chromium-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                ],
            )
            driver_paths = [
                MODULE_ROOT / "build" / "chromedriver",
                MODULE_ROOT / "chromedriver",
            ]
        else:  # Linux
            chrome_paths = [
                MODULE_ROOT / "build" / "chromium-linux" / "chrome",
                MODULE_ROOT / "build" / "chrome-linux64" / "chrome",
                MODULE_ROOT / "chromium-linux" / "chrome",
            ]
            driver_paths = [
                MODULE_ROOT / "build" / "chromedriver",
                MODULE_ROOT / "build" / "chromedriver-linux64" / "chromedriver",
            ]

        # Find first existing Chrome path
        for path in chrome_paths:
            if path.exists():
                chrome = str(path)
                break

        # Find first existing ChromeDriver path
        for path in driver_paths:
            if path.exists():
                driver = str(path)
                break

        return chrome, driver

    def _get_defaults(self) -> dict[str, Any]:
        chrome_path, driver_path = self._get_platform_paths()

        return {
            "backend": {
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
                    "tool_limits": {
                        "global_max_bytes": 256_000,
                        "defaults": {
                            "response_bytes": 64_000,
                        },
                        "browser_get_text": {
                            "response_bytes": 64_000,
                            "chunk_bytes": 16_000,
                        },
                        "browser_execute": {
                            "response_bytes": 32_000,
                            "chunk_bytes": 12_000,
                        },
                        "browser_evaluate": {
                            "response_bytes": 32_000,
                            "chunk_bytes": 12_000,
                        },
                        "chunks": {
                            "default_chunk_size_bytes": 16_000,
                            "max_chunk_bytes": 128_000,
                        },
                    },
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
                "tools": {
                    "web_search": {
                        "primary_url": "http://127.0.0.1:8888/search?q={query}&format=json",
                        "timeout_seconds": 10,
                        "max_results": 10,
                        "user_agent": None,
                    },
                },
            },
        }
