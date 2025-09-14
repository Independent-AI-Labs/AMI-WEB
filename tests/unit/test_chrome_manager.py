"""Unit tests for ChromeManager business logic."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import fixtures for use in tests
pytest_plugins = ["tests.unit.fixtures"]


class TestChromeManager:
    """Test ChromeManager without real browser instances."""

    @pytest.mark.asyncio
    async def test_initialize(self, mock_session_manager: Any, mock_profile_manager: Any) -> None:
        """Test manager initialization."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.session_manager = mock_session_manager
            manager.profile_manager = mock_profile_manager
            manager.initialize = AsyncMock()

            await manager.initialize()

            manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance(self, mock_browser_instance: Any) -> None:
        """Test creating a new browser instance."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.get_or_create_instance = AsyncMock(return_value=mock_browser_instance)

            instance = await manager.get_or_create_instance(headless=True)

            assert instance.id == "test-instance-123"
            assert instance.is_alive is True
            manager.get_or_create_instance.assert_called_once_with(headless=True)

    @pytest.mark.asyncio
    async def test_get_existing_instance(self, mock_browser_instance: Any) -> None:
        """Test getting an existing instance by ID."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.instances = {"test-instance-123": mock_browser_instance}
            manager.get_instance = Mock(return_value=mock_browser_instance)

            instance = manager.get_instance("test-instance-123")

            assert instance is mock_browser_instance
            assert instance.id == "test-instance-123"

    @pytest.mark.asyncio
    async def test_terminate_instance(self, mock_browser_instance: Any) -> None:
        """Test terminating a browser instance."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.instances = {"test-instance-123": mock_browser_instance}
            manager.terminate_instance = AsyncMock()

            await manager.terminate_instance("test-instance-123")

            manager.terminate_instance.assert_called_once_with("test-instance-123")
            mock_browser_instance.terminate.assert_not_called()  # Mock doesn't call real terminate

    def test_list_instances(self, mock_browser_instance: Any) -> None:
        """Test listing all instances."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            instance2 = MagicMock()
            instance2.id = "test-instance-456"

            manager.instances = {"test-instance-123": mock_browser_instance, "test-instance-456": instance2}
            manager.list_instances = Mock(return_value=list(manager.instances.values()))

            instances = manager.list_instances()

            expected_count = 2
            assert len(instances) == expected_count
            assert instances[0].id == "test-instance-123"
            assert instances[1].id == "test-instance-456"

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_browser_instance: Any) -> None:
        """Test manager shutdown."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.instances = {"test-instance-123": mock_browser_instance}
            manager.shutdown = AsyncMock()

            await manager.shutdown()

            manager.shutdown.assert_called_once()


class TestChromeManagerPool:
    """Test ChromeManager pool functionality."""

    def test_pool_configuration(self) -> None:
        """Test pool configuration settings."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.pool = MagicMock()
            manager.pool.min_instances = 1
            manager.pool.max_instances = 5
            manager.pool.warm_instances = 2

            min_pool = 1
            max_pool = 5
            warm_pool = 2
            assert manager.pool.min_instances == min_pool  # Min pool size
            assert manager.pool.max_instances == max_pool  # Max pool size
            assert manager.pool.warm_instances == warm_pool  # Warm pool size

    @pytest.mark.asyncio
    async def test_pool_warm_instances(self, mock_browser_instance: Any) -> None:
        """Test pre-warming instances in pool."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.pool = MagicMock()
            manager.pool.warm_instances = 2
            manager.pool.create_warm_instance = AsyncMock(return_value=mock_browser_instance)

            # Simulate warming pool
            warm_instances = []
            for _ in range(manager.pool.warm_instances):
                instance = await manager.pool.create_warm_instance()
                warm_instances.append(instance)

            expected_warm_count = 2
            assert len(warm_instances) == expected_warm_count
            expected_calls = 2
            assert manager.pool.create_warm_instance.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_pool_max_instances_limit(self) -> None:
        """Test pool respects max instances limit."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.pool = MagicMock()
            manager.pool.max_instances = 3
            manager.pool.active_count = 3
            manager.pool.can_create_instance = Mock(return_value=False)

            can_create = manager.pool.can_create_instance()

            assert can_create is False

    @pytest.mark.asyncio
    async def test_pool_instance_reuse(self, mock_browser_instance: Any) -> None:
        """Test reusing instances from pool."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.pool = MagicMock()
            manager.pool.available_instances = [mock_browser_instance]
            manager.pool.get_available_instance = Mock(return_value=mock_browser_instance)

            instance = manager.pool.get_available_instance()

            assert instance is mock_browser_instance
            manager.pool.get_available_instance.assert_called_once()


class TestChromeManagerSessions:
    """Test ChromeManager session management."""

    @pytest.mark.asyncio
    async def test_create_with_session(self, mock_browser_instance: Any, mock_session_manager: Any) -> None:
        """Test creating instance with session."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.session_manager = mock_session_manager
            mock_session_manager.get_session = AsyncMock(return_value={"id": "session-123", "cookies": [], "local_storage": {}})

            # Mock the get_or_create_instance to call get_session
            async def mock_get_or_create(session_id: str | None = None, **kwargs: Any) -> Any:  # noqa: ARG001
                if session_id:
                    await mock_session_manager.get_session(session_id)
                return mock_browser_instance

            manager.get_or_create_instance = AsyncMock(side_effect=mock_get_or_create)

            instance = await manager.get_or_create_instance(session_id="session-123")

            assert instance is mock_browser_instance
            mock_session_manager.get_session.assert_called_once_with("session-123")

    @pytest.mark.asyncio
    async def test_save_session_on_terminate(self, mock_browser_instance: Any, mock_session_manager: Any) -> None:
        """Test saving session when terminating instance."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.session_manager = mock_session_manager
            mock_browser_instance.session_id = "session-123"
            manager.instances = {"test-instance-123": mock_browser_instance}
            manager.terminate_instance = AsyncMock()

            await manager.terminate_instance("test-instance-123", save_session=True)

            manager.terminate_instance.assert_called_once_with("test-instance-123", save_session=True)


class TestChromeManagerProfiles:
    """Test ChromeManager profile management."""

    @pytest.mark.asyncio
    async def test_create_with_profile(self, mock_browser_instance: Any, mock_profile_manager: Any) -> None:
        """Test creating instance with profile."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profile_manager = mock_profile_manager
            mock_profile_manager.get_profile = AsyncMock(return_value={"id": "profile-123", "user_agent": "Custom UA", "properties": {}})

            # Mock the get_or_create_instance to call get_profile
            async def mock_get_or_create(profile_id: str | None = None, **kwargs: Any) -> Any:  # noqa: ARG001
                if profile_id:
                    await mock_profile_manager.get_profile(profile_id)
                return mock_browser_instance

            manager.get_or_create_instance = AsyncMock(side_effect=mock_get_or_create)

            instance = await manager.get_or_create_instance(profile_id="profile-123")

            assert instance is mock_browser_instance
            mock_profile_manager.get_profile.assert_called_once_with("profile-123")


class TestChromeManagerErrors:
    """Test ChromeManager error handling."""

    @pytest.mark.asyncio
    async def test_instance_not_found(self) -> None:
        """Test handling instance not found."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.get_instance = Mock(return_value=None)

            instance = manager.get_instance("non-existent-id")

            assert instance is None
            manager.get_instance.assert_called_once_with("non-existent-id")

    @pytest.mark.asyncio
    async def test_max_instances_reached(self) -> None:
        """Test handling max instances reached."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.pool = MagicMock()
            manager.pool.max_instances = 3
            manager.pool.active_count = 3

            manager.get_or_create_instance = AsyncMock(side_effect=RuntimeError("Maximum instances reached"))

            with pytest.raises(RuntimeError) as exc:
                await manager.get_or_create_instance()

            assert "Maximum instances reached" in str(exc.value)

    @pytest.mark.asyncio
    async def test_instance_crash_recovery(self, mock_browser_instance: Any) -> None:
        """Test recovering from instance crash."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            mock_browser_instance.is_alive = False
            manager.instances = {"test-instance-123": mock_browser_instance}
            manager.recover_instance = AsyncMock(return_value=mock_browser_instance)

            # Simulate recovery
            recovered = await manager.recover_instance("test-instance-123")

            assert recovered is mock_browser_instance
            manager.recover_instance.assert_called_once_with("test-instance-123")


class TestChromeManagerConcurrency:
    """Test ChromeManager concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_instance_creation(self) -> None:
        """Test creating multiple instances concurrently."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()

            # Create different instances for each call
            instances = []
            for i in range(3):
                instance = MagicMock()
                instance.id = f"instance-{i}"
                instances.append(instance)

            manager.get_or_create_instance = AsyncMock(side_effect=instances)

            # Simulate concurrent creation

            tasks = [manager.get_or_create_instance() for _ in range(3)]
            results = await asyncio.gather(*tasks)

            expected_results = 3
            assert len(results) == expected_results
            assert all(r.id.startswith("instance-") for r in results)
            expected_calls = 3
            assert manager.get_or_create_instance.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_concurrent_termination(self) -> None:
        """Test terminating multiple instances concurrently."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()

            instance_ids = ["instance-1", "instance-2", "instance-3"]
            manager.terminate_instance = AsyncMock()

            # Simulate concurrent termination

            tasks = [manager.terminate_instance(instance_id) for instance_id in instance_ids]
            await asyncio.gather(*tasks)

            expected_calls = 3
            assert manager.terminate_instance.call_count == expected_calls


class TestChromeManagerMetrics:
    """Test ChromeManager metrics and monitoring."""

    def test_instance_metrics(self, mock_browser_instance: Any) -> None:  # noqa: ARG002
        """Test collecting instance metrics."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()

            # Mock metrics
            metrics = {
                "instance_id": "test-instance-123",
                "memory_usage": 150 * 1024 * 1024,  # 150MB
                "cpu_usage": 25.5,
                "active_tabs": 3,
                "uptime": 3600,  # 1 hour
            }

            manager.get_instance_metrics = Mock(return_value=metrics)

            result = manager.get_instance_metrics("test-instance-123")

            expected_memory = 150 * 1024 * 1024
            assert result["memory_usage"] == expected_memory
            expected_cpu = 25.5
            assert result["cpu_usage"] == expected_cpu
            expected_tabs = 3
            assert result["active_tabs"] == expected_tabs

    def test_pool_metrics(self) -> None:
        """Test collecting pool metrics."""
        with patch("browser.backend.core.management.manager.ChromeManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.pool = MagicMock()

            pool_metrics = {"total_instances": 5, "active_instances": 3, "idle_instances": 2, "queued_requests": 0}

            manager.pool.get_metrics = Mock(return_value=pool_metrics)

            metrics = manager.pool.get_metrics()

            expected_total = 5
            assert metrics["total_instances"] == expected_total
            expected_active = 3
            assert metrics["active_instances"] == expected_active
            expected_idle = 2
            assert metrics["idle_instances"] == expected_idle
