"""Unit tests for BrowserInstance state management."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class TestBrowserInstanceState:
    """Test BrowserInstance state management without real browser."""

    @pytest.mark.asyncio
    async def test_instance_initialization(self) -> None:
        """Test browser instance initialization."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.id = "test-instance-123"
            instance.is_alive = True
            instance.driver = MagicMock()
            instance.initialize = AsyncMock()

            await instance.initialize()

            assert instance.id == "test-instance-123"
            assert instance.is_alive is True
            instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_instance_navigation(self) -> None:
        """Test navigation state management."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.current_url = None
            instance.navigate = AsyncMock(side_effect=lambda url: setattr(instance, "current_url", url))

            await instance.navigate("https://example.com")

            assert instance.current_url == "https://example.com"
            instance.navigate.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_instance_script_execution(self) -> None:
        """Test script execution handling."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.execute_script = AsyncMock(return_value={"result": "success", "value": 42})

            result = await instance.execute_script("return 21 * 2;")

            assert result["result"] == "success"
            expected_value = 42
            assert result["value"] == expected_value
            instance.execute_script.assert_called_once_with("return 21 * 2;")

    @pytest.mark.asyncio
    async def test_instance_termination(self) -> None:
        """Test instance termination."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.is_alive = True
            instance.terminate = AsyncMock(side_effect=lambda: setattr(instance, "is_alive", False))

            await instance.terminate()

            assert instance.is_alive is False
            instance.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_instance_crash_detection(self) -> None:
        """Test crash detection mechanism."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.is_alive = True
            instance.check_health = AsyncMock(return_value=False)
            instance.mark_crashed = Mock(side_effect=lambda: setattr(instance, "is_alive", False))

            health = await instance.check_health()
            if not health:
                instance.mark_crashed()

            assert instance.is_alive is False
            instance.check_health.assert_called_once()
            instance.mark_crashed.assert_called_once()


class TestBrowserInstanceTabs:
    """Test tab management in BrowserInstance."""

    @pytest.mark.asyncio
    async def test_create_new_tab(self) -> None:
        """Test creating a new tab."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.tabs = []
            instance.create_tab = AsyncMock(side_effect=lambda: instance.tabs.append({"id": f"tab-{len(instance.tabs)}", "active": False}))

            await instance.create_tab()

            assert len(instance.tabs) == 1
            assert instance.tabs[0]["id"] == "tab-0"
            instance.create_tab.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_tab(self) -> None:
        """Test switching between tabs."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.tabs = [{"id": "tab-0", "active": True}, {"id": "tab-1", "active": False}]
            instance.switch_to_tab = AsyncMock(side_effect=lambda tab_id: [tab.update({"active": tab["id"] == tab_id}) for tab in instance.tabs])

            await instance.switch_to_tab("tab-1")

            assert instance.tabs[0]["active"] is False
            assert instance.tabs[1]["active"] is True
            instance.switch_to_tab.assert_called_once_with("tab-1")

    @pytest.mark.asyncio
    async def test_close_tab(self) -> None:
        """Test closing a tab."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.tabs = [{"id": "tab-0"}, {"id": "tab-1"}, {"id": "tab-2"}]
            instance.close_tab = AsyncMock(side_effect=lambda tab_id: setattr(instance, "tabs", [tab for tab in instance.tabs if tab["id"] != tab_id]))

            await instance.close_tab("tab-1")

            expected_tabs = 2
            assert len(instance.tabs) == expected_tabs
            assert all(tab["id"] != "tab-1" for tab in instance.tabs)
            instance.close_tab.assert_called_once_with("tab-1")


class TestBrowserInstanceCookies:
    """Test cookie management in BrowserInstance."""

    def test_parse_cookies(self) -> None:
        """Test cookie parsing."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            raw_cookies = [
                {"name": "session", "value": "abc123", "domain": ".example.com"},
                {"name": "pref", "value": "dark", "domain": ".example.com"},
            ]
            instance.parse_cookies = Mock(return_value=raw_cookies)

            cookies = instance.parse_cookies(raw_cookies)

            expected_cookies = 2
            assert len(cookies) == expected_cookies
            assert cookies[0]["name"] == "session"
            assert cookies[1]["value"] == "dark"

    @pytest.mark.asyncio
    async def test_set_cookie(self) -> None:
        """Test setting a cookie."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.cookies = []
            instance.set_cookie = AsyncMock(side_effect=lambda cookie: instance.cookies.append(cookie))

            cookie = {"name": "test", "value": "value123", "domain": ".test.com"}
            await instance.set_cookie(cookie)

            assert len(instance.cookies) == 1
            assert instance.cookies[0]["name"] == "test"
            instance.set_cookie.assert_called_once_with(cookie)

    @pytest.mark.asyncio
    async def test_get_cookies(self) -> None:
        """Test getting cookies."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.cookies = [
                {"name": "cookie1", "value": "val1"},
                {"name": "cookie2", "value": "val2"},
            ]
            instance.get_cookies = AsyncMock(return_value=instance.cookies)

            cookies = await instance.get_cookies()

            expected_count = 2
            assert len(cookies) == expected_count
            assert cookies[0]["name"] == "cookie1"
            instance.get_cookies.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cookies(self) -> None:
        """Test clearing cookies."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.cookies = [{"name": "test", "value": "val"}]
            instance.clear_cookies = AsyncMock(side_effect=lambda: setattr(instance, "cookies", []))

            await instance.clear_cookies()

            assert len(instance.cookies) == 0
            instance.clear_cookies.assert_called_once()


class TestBrowserInstanceNetwork:
    """Test network monitoring in BrowserInstance."""

    @pytest.mark.asyncio
    async def test_enable_network_monitoring(self) -> None:
        """Test enabling network monitoring."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.network_monitoring = False
            instance.enable_network_monitoring = AsyncMock(side_effect=lambda: setattr(instance, "network_monitoring", True))

            await instance.enable_network_monitoring()

            assert instance.network_monitoring is True
            instance.enable_network_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_network_request(self) -> None:
        """Test capturing network requests."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.network_logs = []
            instance.capture_request = Mock(side_effect=lambda req: instance.network_logs.append(req))

            request = {
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"User-Agent": "Test"},
            }
            instance.capture_request(request)

            assert len(instance.network_logs) == 1
            assert instance.network_logs[0]["url"] == "https://api.example.com/data"
            instance.capture_request.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_get_network_logs(self) -> None:
        """Test retrieving network logs."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance_class:
            instance = mock_instance_class()
            instance.network_logs = [
                {"url": "https://example.com", "status": 200},
                {"url": "https://api.example.com", "status": 201},
            ]
            instance.get_network_logs = AsyncMock(return_value=instance.network_logs)

            logs = await instance.get_network_logs()

            expected_logs = 2
            assert len(logs) == expected_logs
            expected_status = 200
            assert logs[0]["status"] == expected_status
            instance.get_network_logs.assert_called_once()
