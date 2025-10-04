"""Tests for data_root enforcement in browser MCP server."""

import contextlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from browser.scripts.run_chrome import main


def test_run_chrome_default_data_root() -> None:
    """Verify run_chrome.py defaults to browser/data."""
    # Mock sys.argv and server.run()
    mock_server_class = MagicMock()
    mock_server_instance = MagicMock()
    mock_server_class.return_value = mock_server_instance

    with (
        patch.object(sys, "argv", ["run_chrome.py"]),
        patch("browser.backend.mcp.chrome.chrome_server.ChromeFastMCPServer", mock_server_class),
        contextlib.suppress(SystemExit),
    ):
        main()

    # Verify data_root was passed to ChromeFastMCPServer constructor
    assert mock_server_class.called
    call_args = mock_server_class.call_args
    # call_args is a tuple of (args, kwargs)
    if call_args.kwargs:
        assert "data_root" in call_args.kwargs
        data_root = call_args.kwargs["data_root"]
    else:
        assert len(call_args.args) > 0
        data_root = call_args.args[0]

    assert isinstance(data_root, Path)
    assert data_root.name == "data"
    assert data_root.parent.name == "browser"


def test_chrome_manager_absolute_paths(tmp_path: Path) -> None:
    """Verify ChromeManager uses absolute paths from config_overrides."""
    from browser.backend.core.management.manager import ChromeManager

    data_root = tmp_path / "browser_data"
    config_overrides = {
        "backend.storage.session_dir": str(data_root / "sessions"),
        "backend.storage.profiles_dir": str(data_root / "profiles"),
        "backend.storage.downloads_dir": str(data_root / "downloads"),
        "backend.storage.screenshots_dir": str(data_root / "screenshots"),
    }

    manager = ChromeManager(config_overrides=config_overrides)

    # Verify absolute paths are set in config (using get() method which handles nested keys)
    assert manager.config.get("backend.storage.session_dir") == str(data_root / "sessions")
    assert manager.config.get("backend.storage.profiles_dir") == str(data_root / "profiles")
    assert manager.config.get("backend.storage.downloads_dir") == str(data_root / "downloads")
    assert manager.config.get("backend.storage.screenshots_dir") == str(data_root / "screenshots")

    # Most importantly, verify SessionManager got the right path
    assert str(manager.session_manager.session_dir) == str(data_root / "sessions")


def test_session_manager_absolute_path(tmp_path: Path) -> None:
    """Verify SessionManager uses absolute path and creates directory."""
    from browser.backend.core.management.session_manager import SessionManager

    session_dir = tmp_path / "test_sessions"

    manager = SessionManager(session_dir=str(session_dir))

    # Verify absolute path
    assert manager.session_dir == session_dir
    assert manager.metadata_file == session_dir / "sessions.json"
