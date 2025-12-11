"""Unit test configuration and shared fixtures."""

# Import all fixtures from fixtures.py
from browser.tests.unit.fixtures import (
    mock_browser_instance,
    mock_chrome_manager,
    mock_mcp_request,
    mock_mcp_response,
    mock_profile_manager,
    mock_session_manager,
    mock_transport,
    mock_websocket,
    sample_cookies,
    sample_html_content,
    sample_network_logs,
)


__all__ = [
    "mock_browser_instance",
    "mock_chrome_manager",
    "mock_mcp_request",
    "mock_mcp_response",
    "mock_profile_manager",
    "mock_session_manager",
    "mock_transport",
    "mock_websocket",
    "sample_cookies",
    "sample_html_content",
    "sample_network_logs",
]
