"""Common fixtures and utilities for unit tests."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


@pytest.fixture
def mock_browser_instance() -> Any:
    """Create a mock browser instance for unit testing."""
    instance = MagicMock()
    instance.id = "test-instance-123"
    instance.is_alive = True
    instance.driver = MagicMock()
    instance.navigate = AsyncMock()
    instance.screenshot = AsyncMock(return_value=b"fake_image_data")
    instance.execute_script = AsyncMock(return_value={"result": "success"})
    instance.get_cookies = AsyncMock(return_value=[])
    instance.terminate = AsyncMock()
    return instance


@pytest.fixture
def mock_chrome_manager() -> Any:
    """Create a mock ChromeManager for unit testing."""
    manager = MagicMock()
    manager.create_instance = AsyncMock()
    manager.get_instance = AsyncMock()
    manager.terminate_instance = AsyncMock()
    manager.list_instances = Mock(return_value=[])
    manager.pool = MagicMock()
    manager.pool.min_instances = 1
    manager.pool.max_instances = 3
    return manager


@pytest.fixture
def mock_websocket() -> Any:
    """Create a mock WebSocket connection for unit testing."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws


@pytest.fixture
def mock_mcp_request() -> Any:
    """Create a mock MCP request."""

    def _make_request(
        method: str, params: dict[str, Any] | None = None, request_id: int = 1
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id,
        }

    return _make_request


@pytest.fixture
def mock_mcp_response() -> Any:
    """Create a mock MCP response."""

    def _make_response(
        result: Any, response_id: int = 1, error: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if error:
            return {"jsonrpc": "2.0", "error": error, "id": response_id}
        return {"jsonrpc": "2.0", "result": result, "id": response_id}

    return _make_response


@pytest.fixture
def mock_session_manager() -> Any:
    """Create a mock SessionManager for unit testing."""
    manager = MagicMock()
    manager.create_session = AsyncMock(return_value="session-123")
    manager.get_session = AsyncMock()
    manager.save_session = AsyncMock()
    manager.delete_session = AsyncMock()
    manager.list_sessions = Mock(return_value=[])
    return manager


@pytest.fixture
def mock_profile_manager() -> Any:
    """Create a mock ProfileManager for unit testing."""
    manager = MagicMock()
    manager.create_profile = AsyncMock(return_value="profile-123")
    manager.get_profile = AsyncMock()
    manager.delete_profile = AsyncMock()
    manager.list_profiles = Mock(return_value=[])
    return manager


@pytest.fixture
def sample_html_content() -> str:
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <form id="login-form">
            <input type="text" name="username" />
            <input type="password" name="password" />
            <button type="submit">Login</button>
        </form>
        <a href="/page1">Link 1</a>
        <a href="/page2">Link 2</a>
    </body>
    </html>
    """


@pytest.fixture
def sample_cookies() -> list[dict[str, Any]]:
    """Sample cookies for testing."""
    return [
        {
            "name": "session_id",
            "value": "abc123",
            "domain": ".example.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
        },
        {
            "name": "user_pref",
            "value": "dark_mode",
            "domain": ".example.com",
            "path": "/",
            "secure": False,
            "httpOnly": False,
        },
    ]


@pytest.fixture
def sample_network_logs() -> list[dict[str, Any]]:
    """Sample network logs for testing."""
    return [
        {
            "url": "https://example.com/api/data",
            "method": "GET",
            "status_code": 200,
            "response_time": 150,
            "size": 2048,
        },
        {
            "url": "https://example.com/api/user",
            "method": "POST",
            "status_code": 201,
            "response_time": 200,
            "size": 512,
        },
    ]


class MockTransport:
    """Mock transport for testing MCP communication."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []
        self.closed = False

    async def send(self, message: str) -> Any:
        """Mock send method."""
        self.messages.append(json.loads(message))
        if self.responses:
            return self.responses.pop(0)
        return None

    async def receive(self) -> str | None:
        """Mock receive method."""
        if self.responses:
            return json.dumps(self.responses.pop(0))
        return None

    def add_response(self, response: dict[str, Any]) -> None:
        """Add a response to be returned."""
        self.responses.append(response)

    async def close(self) -> None:
        """Mock close method."""
        self.closed = True


@pytest.fixture
def mock_transport() -> MockTransport:
    """Create a mock transport for unit testing."""
    return MockTransport()
