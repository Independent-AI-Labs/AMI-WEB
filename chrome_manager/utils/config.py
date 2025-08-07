import json
import os
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

        return self._get_env_override(key, value if value is not None else default)

    def _get_env_override(self, key: str, default: Any) -> Any:
        env_key = f"CHROME_MANAGER_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)

        if env_value is not None:
            try:
                return json.loads(env_value)
            except (json.JSONDecodeError, ValueError):
                return env_value

        return default

    def _get_defaults(self) -> dict[str, Any]:
        return {
            "chrome_manager": {
                "browser": {
                    "chrome_binary_path": "./chromium-win/chrome.exe",
                    "chromedriver_path": "./chromedriver.exe",
                    "executable_path": None,
                    "default_headless": True,
                    "default_window_size": [1920, 1080],
                    "user_agent": None
                },
                "pool": {"min_instances": 1, "max_instances": 10, "warm_instances": 2, "instance_ttl": 3600, "health_check_interval": 30},
                "performance": {"max_memory_per_instance": 512, "max_cpu_per_instance": 25, "page_load_timeout": 30, "script_timeout": 10},
                "storage": {"session_dir": "./sessions", "screenshot_dir": "./screenshots", "video_dir": "./videos", "log_dir": "./logs"},
                "mcp": {"server_host": "localhost", "server_port": 8765, "max_connections": 100, "auth_required": False, "tls_enabled": False},
            }
        }
