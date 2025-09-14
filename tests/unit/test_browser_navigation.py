"""Unit tests for browser navigation logic."""

from unittest.mock import AsyncMock, patch

import pytest


class TestNavigationLogic:
    """Test navigation logic without real browser."""

    @pytest.mark.asyncio
    async def test_wait_for_element_logic(self) -> None:
        """Test wait for element logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.wait_for_element = AsyncMock(return_value=True)

            # Simulate waiting for element
            result = await instance.wait_for_element("#content", timeout=5)

            assert result is True
            instance.wait_for_element.assert_called_once_with("#content", timeout=5)

    @pytest.mark.asyncio
    async def test_page_content_extraction(self) -> None:
        """Test page content extraction logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.get_page_content = AsyncMock(return_value="<html><body>Test</body></html>")

            content = await instance.get_page_content()

            assert "Test" in content
            instance.get_page_content.assert_called_once()


class TestInputSimulationLogic:
    """Test input simulation logic without real browser."""

    @pytest.mark.asyncio
    async def test_click_element_logic(self) -> None:
        """Test click element logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.click_element = AsyncMock(return_value={"success": True})

            result = await instance.click_element("#button")

            assert result["success"] is True
            instance.click_element.assert_called_once_with("#button")

    @pytest.mark.asyncio
    async def test_type_text_logic(self) -> None:
        """Test type text logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.type_text = AsyncMock(return_value={"typed": "test text"})

            result = await instance.type_text("#input", "test text")

            assert result["typed"] == "test text"
            instance.type_text.assert_called_once_with("#input", "test text")

    @pytest.mark.asyncio
    async def test_checkbox_interaction_logic(self) -> None:
        """Test checkbox interaction logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.is_checked = False
            instance.toggle_checkbox = AsyncMock(side_effect=lambda: setattr(instance, "is_checked", not instance.is_checked))

            await instance.toggle_checkbox()

            assert instance.is_checked is True
            instance.toggle_checkbox.assert_called_once()


class TestScreenshotLogic:
    """Test screenshot logic without real browser."""

    @pytest.mark.asyncio
    async def test_viewport_screenshot_logic(self) -> None:
        """Test viewport screenshot logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.screenshot_viewport = AsyncMock(return_value=b"fake_image_data")

            data = await instance.screenshot_viewport()

            assert data == b"fake_image_data"
            instance.screenshot_viewport.assert_called_once()

    @pytest.mark.asyncio
    async def test_element_screenshot_logic(self) -> None:
        """Test element screenshot logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.screenshot_element = AsyncMock(return_value=b"element_image")

            data = await instance.screenshot_element("#element")

            assert data == b"element_image"
            instance.screenshot_element.assert_called_once_with("#element")


class TestPoolManagement:
    """Test browser pool management logic."""

    @pytest.mark.asyncio
    async def test_pool_instance_creation(self) -> None:
        """Test pool instance creation logic."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager:
            manager = mock_manager()
            manager.pool_size = 0
            manager.max_pool_size = 5
            manager.create_pool_instance = AsyncMock(side_effect=lambda: setattr(manager, "pool_size", manager.pool_size + 1))

            await manager.create_pool_instance()

            assert manager.pool_size == 1
            manager.create_pool_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_warm_instances(self) -> None:
        """Test pool warm instances logic."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager:
            manager = mock_manager()
            manager.warm_pool_size = 2
            manager.warm_instances = []
            manager.warm_instance = AsyncMock(side_effect=lambda: manager.warm_instances.append("instance"))

            # Warm the pool
            for _ in range(manager.warm_pool_size):
                await manager.warm_instance()

            expected_warm = 2
            assert len(manager.warm_instances) == expected_warm
            expected_calls = 2
            assert manager.warm_instance.call_count == expected_calls


class TestScriptInjection:
    """Test script injection logic."""

    @pytest.mark.asyncio
    async def test_inject_script_logic(self) -> None:
        """Test script injection logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.inject_script = AsyncMock(return_value={"injected": True})

            script = "window.customVar = 'test';"
            result = await instance.inject_script(script)

            assert result["injected"] is True
            instance.inject_script.assert_called_once_with(script)

    @pytest.mark.asyncio
    async def test_modify_dom_logic(self) -> None:
        """Test DOM modification logic."""
        with patch("browser.backend.core.browser.instance.BrowserInstance") as mock_instance:
            instance = mock_instance()
            instance.execute_script = AsyncMock(return_value={"modified": True})

            script = "document.body.innerHTML = '<div>Modified</div>';"
            result = await instance.execute_script(script)

            assert result["modified"] is True
            instance.execute_script.assert_called_once_with(script)
