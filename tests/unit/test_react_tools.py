"""Unit tests for React-specific browser tools."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.tools.react_tools import (
    browser_react_find_component_tool,
    browser_react_get_fiber_tree_tool,
    browser_react_get_props_tool,
    browser_react_get_state_tool,
    browser_react_trigger_handler_tool,
)


def _create_mock_manager(execute_script_return: Any = None) -> Any:
    """Create a mock ChromeManager with a mock browser instance."""
    mock_driver = MagicMock()
    mock_driver.execute_script = MagicMock(return_value=execute_script_return)

    mock_instance = SimpleNamespace(driver=mock_driver, id="test-instance")

    mock_instance_info = SimpleNamespace(id="test-instance")

    manager = SimpleNamespace()
    manager.list_instances = AsyncMock(return_value=[mock_instance_info])
    manager.get_instance = AsyncMock(return_value=mock_instance)
    manager.get_instance_or_current = AsyncMock(return_value=mock_instance)

    return manager


@pytest.mark.asyncio
async def test_trigger_handler_success() -> None:
    """Test successfully triggering a React handler."""
    mock_manager = _create_mock_manager({"success": True, "message": "Handler triggered successfully"})

    response = await browser_react_trigger_handler_tool(mock_manager, ".test-element", "onClick")

    assert response.success is True
    assert response.result == "Handler triggered successfully"


@pytest.mark.asyncio
async def test_trigger_handler_with_event_data() -> None:
    """Test triggering a React handler with event data."""
    mock_manager = _create_mock_manager({"success": True, "message": "Handler triggered"})

    event_data = {"target": {"value": "test"}}
    response = await browser_react_trigger_handler_tool(mock_manager, ".test-input", "onChange", event_data)

    assert response.success is True
    # Verify the script was called with event data
    mock_driver = mock_manager.get_instance.return_value.driver
    assert mock_driver.execute_script.call_args[0][1] == ".test-input"
    assert mock_driver.execute_script.call_args[0][2] == "onChange"
    assert mock_driver.execute_script.call_args[0][3] == event_data


@pytest.mark.asyncio
async def test_trigger_handler_element_not_found() -> None:
    """Test triggering handler when element is not found."""
    mock_manager = _create_mock_manager({"success": False, "error": "Element not found"})

    response = await browser_react_trigger_handler_tool(mock_manager, ".nonexistent", "onClick")

    assert response.success is False
    assert "Element not found" in (response.error or "")


@pytest.mark.asyncio
async def test_trigger_handler_no_fiber() -> None:
    """Test triggering handler when React fiber is not found."""
    mock_manager = _create_mock_manager(
        {
            "success": False,
            "error": "React fiber not found - element may not be a React component",
        }
    )

    response = await browser_react_trigger_handler_tool(mock_manager, ".non-react-element", "onClick")

    assert response.success is False
    assert "React fiber not found" in (response.error or "")


@pytest.mark.asyncio
async def test_trigger_handler_handler_not_found() -> None:
    """Test triggering handler when handler is not found."""
    mock_manager = _create_mock_manager({"success": False, "error": "Handler not found: onMissingHandler"})

    response = await browser_react_trigger_handler_tool(mock_manager, ".test-element", "onMissingHandler")

    assert response.success is False
    assert "Handler not found" in (response.error or "")


@pytest.mark.asyncio
async def test_get_props_success() -> None:
    """Test successfully getting React component props."""
    props_data = {"className": "test-class", "id": "test-id", "data-value": "123"}
    mock_manager = _create_mock_manager({"success": True, "props": props_data})

    response = await browser_react_get_props_tool(mock_manager, ".test-element")

    assert response.success is True
    assert response.result == props_data


@pytest.mark.asyncio
async def test_get_props_with_max_depth() -> None:
    """Test getting props with custom max depth."""
    mock_manager = _create_mock_manager({"success": True, "props": {"test": "value"}})

    response = await browser_react_get_props_tool(mock_manager, ".test-element", max_depth=5)

    assert response.success is True
    # Verify max_depth was passed to the script
    mock_driver = mock_manager.get_instance.return_value.driver
    assert mock_driver.execute_script.call_args[0][2] == 5


@pytest.mark.asyncio
async def test_get_props_no_props_found() -> None:
    """Test getting props when no props are found."""
    mock_manager = _create_mock_manager({"success": False, "error": "No props found"})

    response = await browser_react_get_props_tool(mock_manager, ".test-element")

    assert response.success is False
    assert "No props found" in (response.error or "")


@pytest.mark.asyncio
async def test_get_state_success() -> None:
    """Test successfully getting React component state."""
    state_data = {"count": 5, "isOpen": True}
    mock_manager = _create_mock_manager({"success": True, "state": state_data})

    response = await browser_react_get_state_tool(mock_manager, ".test-element")

    assert response.success is True
    assert response.result == state_data


@pytest.mark.asyncio
async def test_get_state_stateless_component() -> None:
    """Test getting state from a stateless component."""
    mock_manager = _create_mock_manager({"success": False, "error": "No state found - component may be stateless"})

    response = await browser_react_get_state_tool(mock_manager, ".test-element")

    assert response.success is False
    assert "stateless" in (response.error or "").lower()


@pytest.mark.asyncio
async def test_find_component_success() -> None:
    """Test successfully finding a React component."""
    found_components = [
        {
            "selector": "#test-component",
            "componentName": "TestComponent",
            "props": ["onClick", "className"],
        },
        {
            "selector": ".another-test",
            "componentName": "TestComponent",
            "props": ["id", "value"],
        },
    ]
    mock_manager = _create_mock_manager({"success": True, "components": found_components})

    response = await browser_react_find_component_tool(mock_manager, "TestComponent")

    assert response.success is True
    assert isinstance(response.result, list)
    assert len(response.result) == 2
    assert response.result[0]["componentName"] == "TestComponent"


@pytest.mark.asyncio
async def test_find_component_not_found() -> None:
    """Test finding a component that doesn't exist."""
    mock_manager = _create_mock_manager({"success": False, "error": "Component not found: MissingComponent"})

    response = await browser_react_find_component_tool(mock_manager, "MissingComponent")

    assert response.success is False
    assert "Component not found" in (response.error or "")


@pytest.mark.asyncio
async def test_get_fiber_tree_success() -> None:
    """Test successfully getting React fiber tree."""
    tree_data = {
        "type": "div",
        "props": ["className", "onClick"],
        "hasState": False,
        "parent": {
            "type": "TestComponent",
            "props": ["children"],
            "hasState": True,
            "parent": None,
        },
    }
    mock_manager = _create_mock_manager({"success": True, "tree": tree_data})

    response = await browser_react_get_fiber_tree_tool(mock_manager, ".test-element")

    assert response.success is True
    assert response.result == tree_data
    assert response.result["type"] == "div"
    assert response.result["parent"]["type"] == "TestComponent"


@pytest.mark.asyncio
async def test_get_fiber_tree_custom_depth() -> None:
    """Test getting fiber tree with custom depth."""
    mock_manager = _create_mock_manager(
        {
            "success": True,
            "tree": {"type": "div", "props": [], "hasState": False, "parent": None},
        }
    )

    response = await browser_react_get_fiber_tree_tool(mock_manager, ".test-element", max_depth=3)

    assert response.success is True
    # Verify max_depth was passed to the script
    mock_driver = mock_manager.get_instance.return_value.driver
    assert mock_driver.execute_script.call_args[0][2] == 3


@pytest.mark.asyncio
async def test_no_browser_instance_available() -> None:
    """Test all tools when no browser instance is available."""
    manager = SimpleNamespace()
    manager.list_instances = AsyncMock(return_value=[])
    manager.get_instance_or_current = AsyncMock(return_value=None)

    # Cast to ChromeManager for type checking - this is a duck-typed test mock
    mock_manager = cast(ChromeManager, manager)

    # Test trigger_handler
    response = await browser_react_trigger_handler_tool(mock_manager, ".test", "onClick")
    assert response.success is False
    assert "Browser instance not available" in (response.error or "")

    # Test get_props
    response = await browser_react_get_props_tool(mock_manager, ".test")
    assert response.success is False
    assert "Browser instance not available" in (response.error or "")

    # Test get_state
    response = await browser_react_get_state_tool(mock_manager, ".test")
    assert response.success is False
    assert "Browser instance not available" in (response.error or "")

    # Test find_component
    response = await browser_react_find_component_tool(mock_manager, "TestComponent")
    assert response.success is False
    assert "Browser instance not available" in (response.error or "")

    # Test get_fiber_tree
    response = await browser_react_get_fiber_tree_tool(mock_manager, ".test")
    assert response.success is False
    assert "Browser instance not available" in (response.error or "")
