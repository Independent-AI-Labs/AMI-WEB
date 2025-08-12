import asyncio
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from ..models.browser import ChromeOptions
from ..utils.config import Config
from .instance import BrowserInstance

if TYPE_CHECKING:
    from .profile_manager import ProfileManager
    from .properties_manager import PropertiesManager

# Constants for pool management
DEFAULT_ACQUIRE_TIMEOUT = 30  # seconds
WARMUP_CHECK_INTERVAL = 10  # seconds


class InstancePool:
    def __init__(
        self,
        min_instances: int = 1,
        max_instances: int = 10,
        warm_instances: int = 2,
        instance_ttl: int = 3600,
        health_check_interval: int = 30,
        config: Config | None = None,
        properties_manager: "PropertiesManager | None" = None,
        profile_manager: "ProfileManager | None" = None,
    ):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.warm_instances = warm_instances
        self.instance_ttl = instance_ttl
        self.health_check_interval = health_check_interval
        self._config = config or Config()
        self._properties_manager = properties_manager
        self._profile_manager = profile_manager

        self.available: deque[BrowserInstance] = deque()
        self.in_use: dict[str, BrowserInstance] = {}
        self.all_instances: dict[str, BrowserInstance] = {}

        self._lock = asyncio.Lock()
        self._health_check_task: asyncio.Task | None = None
        self._warmup_task: asyncio.Task | None = None

    async def initialize(self):
        logger.info("Initializing instance pool")
        await self._ensure_min_instances()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._warmup_task = asyncio.create_task(self._warmup_loop())

    async def shutdown(self):
        logger.info("Shutting down instance pool")

        # Cancel background tasks properly
        tasks_to_cancel = []

        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            tasks_to_cancel.append(self._health_check_task)

        if self._warmup_task and not self._warmup_task.done():
            self._warmup_task.cancel()
            tasks_to_cancel.append(self._warmup_task)

        # Wait for all tasks to actually cancel
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        self._health_check_task = None
        self._warmup_task = None

        # Terminate all instances
        for instance in self.all_instances.values():
            await instance.terminate()

        self.available.clear()
        self.in_use.clear()
        self.all_instances.clear()

    async def acquire(self, options: ChromeOptions | None = None, timeout: int = DEFAULT_ACQUIRE_TIMEOUT) -> BrowserInstance:
        async with self._lock:
            instance = await self._get_available_instance(options)
            if instance:
                self.in_use[instance.id] = instance
                instance.last_activity = datetime.now()
                logger.debug(f"Acquired instance {instance.id} from pool")
                return instance

        if len(self.all_instances) >= self.max_instances:
            logger.warning("Max instances reached, waiting for available instance")
            return await self._wait_for_instance(timeout, options)

        instance = await self._create_instance(options)
        async with self._lock:
            self.in_use[instance.id] = instance
            self.all_instances[instance.id] = instance

        logger.info(f"Created new instance {instance.id}")
        return instance

    async def release(self, instance_id: str):
        async with self._lock:
            instance = self.in_use.pop(instance_id, None)
            if not instance:
                # Try to find in all_instances if not in use
                instance = self.all_instances.get(instance_id)
                if not instance:
                    logger.warning(f"Instance {instance_id} not found in pool")
                    return

            if await self._is_healthy(instance):
                # Reset browser state before returning to pool
                await self._reset_instance(instance)
                self.available.append(instance)
                logger.debug(f"Released instance {instance_id} back to pool")
            else:
                await self._remove_instance(instance)
                logger.info(f"Removed unhealthy instance {instance_id}")

    async def _get_available_instance(self, options: ChromeOptions | None) -> BrowserInstance | None:
        while self.available:
            instance = self.available.popleft()
            if await self._is_healthy(instance):
                if not options or self._matches_options(instance, options):
                    return instance
            else:
                await self._remove_instance(instance)
        return None

    async def _create_instance(self, options: ChromeOptions | None = None) -> BrowserInstance:
        instance = BrowserInstance(
            config=self._config,
            properties_manager=self._properties_manager,
            profile_manager=self._profile_manager,
        )
        opts = options or ChromeOptions()
        # Use anti_detect from options if provided, default to True for pooled instances
        anti_detect = getattr(opts, "anti_detect", True)
        await instance.launch(headless=opts.headless, extensions=opts.extensions, options=opts, anti_detect=anti_detect)
        return instance

    async def _wait_for_instance(self, timeout: int, options: ChromeOptions | None) -> BrowserInstance:
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            async with self._lock:
                instance = await self._get_available_instance(options)
                if instance:
                    self.in_use[instance.id] = instance
                    return instance
            await asyncio.sleep(0.1)  # Reduced from 0.5s for better responsiveness

        raise TimeoutError(f"Failed to acquire instance within {timeout} seconds")

    async def _is_healthy(self, instance: BrowserInstance) -> bool:
        try:
            health = await instance.health_check()
            return health["healthy"]
        except Exception:
            return False

    async def _reset_instance(self, instance: BrowserInstance):
        """Reset browser instance to clean state for reuse."""
        try:
            # Navigate to blank page
            instance.driver.get("about:blank")
            # Clear cookies
            instance.driver.delete_all_cookies()
            # Close any extra tabs
            handles = instance.driver.window_handles
            if len(handles) > 1:
                for handle in handles[1:]:
                    instance.driver.switch_to.window(handle)
                    instance.driver.close()
                instance.driver.switch_to.window(handles[0])
            logger.debug(f"Reset instance {instance.id} to clean state")
        except Exception as e:
            logger.warning(f"Failed to reset instance {instance.id}: {e}")

    async def _remove_instance(self, instance: BrowserInstance):
        try:
            await instance.terminate()
        except Exception as e:
            logger.warning(f"Error terminating instance {instance.id}: {e}")

        self.all_instances.pop(instance.id, None)
        if instance in self.available:
            self.available.remove(instance)

    def _matches_options(self, instance: BrowserInstance, options: ChromeOptions) -> bool:
        if not instance._options:
            return False
        return instance._options.headless == options.headless and set(instance._options.extensions) == set(options.extensions)

    async def _ensure_min_instances(self):
        current_count = len(self.all_instances)
        needed = max(0, self.min_instances - current_count)

        for _ in range(needed):
            try:
                instance = await self._create_instance()
                async with self._lock:
                    self.available.append(instance)
                    self.all_instances[instance.id] = instance
            except Exception as e:
                logger.error(f"Failed to create instance: {e}")

    async def _health_check_loop(self):
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_instances()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_all_instances(self):
        async with self._lock:
            to_remove = []

            for _instance_id, instance in list(self.all_instances.items()):
                age = (datetime.now() - instance.created_at).total_seconds()
                if age > self.instance_ttl:
                    to_remove.append(instance)
                    continue

                if not await self._is_healthy(instance):
                    to_remove.append(instance)

            for instance in to_remove:
                await self._remove_instance(instance)
                self.in_use.pop(instance.id, None)

        await self._ensure_min_instances()

    async def _warmup_loop(self):
        while True:
            try:
                await asyncio.sleep(WARMUP_CHECK_INTERVAL)
                await self._ensure_warm_instances()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Warmup error: {e}")

    async def _ensure_warm_instances(self):
        async with self._lock:
            available_count = len(self.available)
            needed = max(0, self.warm_instances - available_count)

        for _ in range(needed):
            if len(self.all_instances) >= self.max_instances:
                break

            try:
                instance = await self._create_instance()
                async with self._lock:
                    self.available.append(instance)
                    self.all_instances[instance.id] = instance
            except Exception as e:
                logger.error(f"Failed to create warm instance: {e}")

    def get_stats(self) -> dict:
        return {
            "total_instances": len(self.all_instances),
            "available": len(self.available),
            "in_use": len(self.in_use),
            "max_instances": self.max_instances,
            "min_instances": self.min_instances,
            "warm_instances": self.warm_instances,
        }
