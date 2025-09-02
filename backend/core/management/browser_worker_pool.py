"""Browser-specific worker pool implementation using base worker system."""

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from datetime import datetime  # noqa: E402
from typing import TYPE_CHECKING, Any  # noqa: E402

from base.backend.workers.base import WorkerPool  # noqa: E402
from base.backend.workers.types import PoolConfig, WorkerInfo, WorkerState  # noqa: E402
from browser.backend.core.browser.instance import BrowserInstance  # noqa: E402
from browser.backend.core.browser.properties_manager import PropertiesManager  # noqa: E402
from browser.backend.core.management.profile_manager import ProfileManager  # noqa: E402
from browser.backend.models.browser import ChromeOptions  # noqa: E402
from browser.backend.utils.config import Config  # noqa: E402
from loguru import logger  # noqa: E402

if TYPE_CHECKING:
    pass


class BrowserWorker:
    """Wrapper for BrowserInstance to work with the worker pool system."""

    def __init__(
        self,
        _worker_id: str,
        instance: BrowserInstance,
        created_at: datetime | None = None,
    ):
        # Use the browser instance ID as the worker ID for consistency
        self.id = instance.id
        self.instance = instance
        self.state = WorkerState.IDLE
        self.created_at = created_at or datetime.now()
        self.last_used = datetime.now()
        self.task_count = 0
        self.error_count = 0

    async def execute(self, func: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a function on the browser instance."""
        self.last_used = datetime.now()
        self.task_count += 1

        try:
            # If func is a string, try to get the method from the instance
            if isinstance(func, str):
                method = getattr(self.instance, func, None)
                if method:
                    result = await method(*args, **kwargs)
                else:
                    raise AttributeError(f"BrowserInstance has no method '{func}'")
                return result
        except Exception as e:
            self.error_count += 1
            raise e

    async def health_check(self) -> bool:
        """Check if the browser instance is healthy."""
        try:
            health = await self.instance.health_check()
            return bool(health.get("alive", False) and health.get("responsive", False))
        except Exception as e:
            logger.debug(f"Health check failed for worker {self.id}: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up the browser instance."""
        try:
            await self.instance.terminate()
        except Exception as e:
            logger.warning(f"Error cleaning up browser worker {self.id}: {e}")


class BrowserWorkerPool(WorkerPool[BrowserWorker, Any]):
    """Browser-specific worker pool implementation."""

    def __init__(
        self,
        config: PoolConfig,
        browser_config: Config | None = None,
        properties_manager: "PropertiesManager | None" = None,
        profile_manager: "ProfileManager | None" = None,
    ):
        """Initialize the browser worker pool.

        Args:
            config: Pool configuration
            browser_config: Browser-specific configuration
            properties_manager: Browser properties manager
            profile_manager: Browser profile manager
        """
        super().__init__(config)
        self._browser_config = browser_config or Config()
        self._properties_manager = properties_manager
        self._profile_manager = profile_manager
        self._default_options = ChromeOptions()
        self._workers: dict[str, BrowserWorker] = {}  # Track workers

    async def _create_worker(self, **kwargs: Any) -> BrowserWorker:
        """Create a new browser worker instance."""
        # Extract browser-specific options
        options = kwargs.get("options", self._default_options)
        if not isinstance(options, ChromeOptions):
            options = self._default_options

        # Create browser instance
        instance = BrowserInstance(
            config=self._browser_config,
            properties_manager=self._properties_manager,
            profile_manager=self._profile_manager,
        )

        # Launch the browser
        anti_detect = self._browser_config.get("backend.pool.anti_detect_default", True)
        await instance.launch(
            headless=options.headless,
            extensions=options.extensions,
            options=options,
            anti_detect=getattr(options, "anti_detect", anti_detect),
        )

        # Create worker wrapper
        worker_id = instance.id
        worker = BrowserWorker(worker_id, instance)

        logger.info(f"Created browser worker {worker_id}")
        return worker

    async def _cleanup_worker(self, worker: BrowserWorker) -> None:
        """Clean up a browser worker."""
        await worker.cleanup()

    async def _check_worker_health(self, worker: BrowserWorker) -> bool:
        """Check if a browser worker is healthy."""
        return await worker.health_check()

    async def _hibernate_worker(self, worker: BrowserWorker) -> None:
        """Hibernate a browser worker to save resources."""
        try:
            # Check if driver is available
            if worker.instance.driver is None:
                logger.warning(f"Cannot hibernate worker {worker.id}: driver is None")
                return

            # Navigate to blank page and clear state
            worker.instance.driver.get("about:blank")
            worker.instance.driver.delete_all_cookies()

            # Close extra tabs
            handles = worker.instance.driver.window_handles
            if len(handles) > 1:
                for handle in handles[1:]:
                    worker.instance.driver.switch_to.window(handle)
                    worker.instance.driver.close()
                worker.instance.driver.switch_to.window(handles[0])

            worker.state = WorkerState.HIBERNATING
            logger.debug(f"Hibernated browser worker {worker.id}")
        except Exception as e:
            logger.warning(f"Failed to hibernate browser worker {worker.id}: {e}")

    async def _wake_worker(self, worker: BrowserWorker) -> None:
        """Wake a hibernated browser worker."""
        if worker.state == WorkerState.HIBERNATING:
            # Just change state, browser is already at blank page
            worker.state = WorkerState.IDLE
            worker.last_used = datetime.now()
            logger.debug(f"Woke browser worker {worker.id}")

    async def _execute_task(self, worker: BrowserWorker, task: Any) -> Any:
        """Execute a task on a browser worker."""
        # Task should contain the function/method and arguments
        if hasattr(task, "func"):
            return await worker.execute(task.func, *task.args, **task.kwargs)
        # Direct execution
        return await worker.execute(task)

    def _get_worker_info(self, worker: BrowserWorker) -> WorkerInfo:
        """Get information about a browser worker."""
        return WorkerInfo(
            id=worker.id,
            state=worker.state,
            created_at=worker.created_at,
            last_activity=worker.last_used,
            task_count=worker.task_count,
            error_count=worker.error_count,
            memory_usage=None,  # Could get from browser if needed
            cpu_percent=None,  # Could get from browser if needed
        )

    async def _get_worker_instance(self, worker_id: str) -> BrowserWorker | None:
        """Get a worker instance by ID."""
        return self._workers.get(worker_id)

    def _remove_worker_instance(self, worker_id: str) -> None:
        """Remove a worker instance from storage."""
        if worker_id in self._workers:
            del self._workers[worker_id]

    def _store_worker_instance(self, worker_id: str, worker: BrowserWorker) -> None:
        """Store a worker instance."""
        self._workers[worker_id] = worker
        logger.debug(f"Stored worker {worker_id} in pool, total workers: {len(self._workers)}")

    async def _reset_worker(self, worker: BrowserWorker) -> None:
        """Reset a worker to clean state."""
        await self._hibernate_worker(worker)
        await self._wake_worker(worker)

    async def _destroy_worker(self, worker: BrowserWorker) -> None:
        """Destroy a worker."""
        await self._cleanup_worker(worker)

    async def acquire_browser(self, _options: ChromeOptions | None = None) -> BrowserInstance:
        """Acquire a browser instance from the pool (convenience method).

        Args:
            options: Chrome options for the browser

        Returns:
            A browser instance from the pool
        """
        # Get a worker from the pool
        worker_id = await self.acquire_worker(timeout=30)
        worker = await self._get_worker_instance(worker_id)

        if not worker:
            raise RuntimeError(f"Failed to get worker {worker_id}")

        return worker.instance

    async def release_browser(self, instance_id: str) -> None:
        """Release a browser instance back to the pool (convenience method).

        Args:
            instance_id: The browser instance ID
        """
        # Find the worker with this instance
        worker = None
        for w in self._workers.values():
            if w.instance.id == instance_id:
                worker = w
                break

        if worker:
            logger.debug(f"Found worker {worker.id} for instance {instance_id}, releasing...")
            await self.release_worker(worker.id)
            logger.debug(f"Released worker {worker.id}")
        else:
            logger.warning(f"Browser instance {instance_id} not found in pool")
