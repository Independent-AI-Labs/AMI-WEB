import asyncio
from typing import Any

from loguru import logger

from ..facade.media import ScreenshotController
from ..facade.navigation import NavigationController
from ..models.browser import ChromeOptions, InstanceInfo
from ..utils.config import Config
from .instance import BrowserInstance
from .pool import InstancePool
from .session import SessionManager


class ChromeManager:
    def __init__(self, config_file: str | None = None):
        self.config = Config.load(config_file) if config_file else Config()
        self.pool = InstancePool(
            min_instances=self.config.get("pool.min_instances", 1),
            max_instances=self.config.get("pool.max_instances", 10),
            warm_instances=self.config.get("pool.warm_instances", 2),
            instance_ttl=self.config.get("pool.instance_ttl", 3600),
            health_check_interval=self.config.get("pool.health_check_interval", 30),
            config=self.config,
        )
        self.session_manager = SessionManager(session_dir=self.config.get("storage.session_dir", "./sessions"))
        self._instances: dict[str, BrowserInstance] = {}
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        logger.info("Initializing Chrome Manager")
        await self.pool.initialize()
        await self.session_manager.initialize()
        self._initialized = True
        logger.info("Chrome Manager initialized successfully")

    async def start(self):
        """Alias for initialize() for backward compatibility."""
        await self.initialize()

    async def shutdown(self):
        logger.info("Shutting down Chrome Manager")
        await self.pool.shutdown()
        await self.session_manager.shutdown()

        for instance in self._instances.values():
            await instance.terminate()

        self._instances.clear()
        self._initialized = False
        logger.info("Chrome Manager shutdown complete")

    async def stop(self):
        """Alias for shutdown() for backward compatibility."""
        await self.shutdown()

    async def get_or_create_instance(
        self,
        headless: bool = True,
        profile: str | None = None,
        extensions: list[str] | None = None,
        options: ChromeOptions | None = None,
        use_pool: bool = True,
    ) -> BrowserInstance:
        if not self._initialized:
            await self.initialize()

        if use_pool:
            opts = options or ChromeOptions(headless=headless, extensions=extensions or [])
            instance = await self.pool.acquire(opts)
        else:
            instance = BrowserInstance(config=self.config)
            await instance.launch(headless=headless, profile=profile, extensions=extensions, options=options)

        self._instances[instance.id] = instance
        logger.info(f"Got or created browser instance {instance.id}")
        return instance

    async def get_instance(self, instance_id: str) -> BrowserInstance | None:
        return self._instances.get(instance_id)

    async def return_to_pool(self, instance_id: str) -> bool:
        """Return an instance to the pool for reuse."""
        instance = self._instances.get(instance_id)
        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            return False

        if instance.id in self.pool.all_instances:
            await self.pool.release(instance_id)
            logger.info(f"Returned instance {instance_id} to pool")
            return True
        logger.warning(f"Instance {instance_id} is not a pool instance")
        return False

    async def terminate_instance(self, instance_id: str, return_to_pool: bool = False) -> bool:
        """Terminate a browser instance.
        
        Args:
            instance_id: ID of instance to terminate
            return_to_pool: If True, return to pool for reuse. If False, fully terminate.
                           Default is False to ensure proper cleanup.
        """
        instance = self._instances.pop(instance_id, None)
        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            return False

        if return_to_pool and instance.id in self.pool.all_instances:
            # Return to pool for reuse (keeps browser running)
            await self.pool.release(instance_id)
            logger.info(f"Returned instance {instance_id} to pool")
        else:
            # Actually terminate the browser
            await instance.terminate()
            # Remove from pool if it was there
            if instance.id in self.pool.all_instances:
                self.pool.all_instances.pop(instance.id, None)
                if instance in self.pool.available:
                    self.pool.available.remove(instance)
                self.pool.in_use.pop(instance.id, None)
            logger.info(f"Terminated instance {instance_id}")

        return True

    async def list_instances(self) -> list[InstanceInfo]:
        instances = []
        for instance in self._instances.values():
            instances.append(instance.get_info())
        return instances

    async def save_session(self, instance_id: str) -> str:
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        session_id = await self.session_manager.save_session(instance)
        logger.info(f"Saved session {session_id} for instance {instance_id}")
        return session_id

    async def restore_session(self, session_id: str) -> BrowserInstance:
        instance = await self.session_manager.restore_session(session_id)
        self._instances[instance.id] = instance
        logger.info(f"Restored session {session_id} as instance {instance.id}")
        return instance

    async def get_pool_stats(self) -> dict:
        return self.pool.get_stats()

    async def execute_batch(self, tasks: list[dict[str, Any]], max_concurrent: int = 5) -> list[Any]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_task(task: dict[str, Any]):
            async with semaphore:
                instance = await self.get_or_create_instance()
                try:
                    return await self._execute_task_on_instance(instance, task)
                finally:
                    await self.terminate_instance(instance.id)

        tasks_list = [execute_task(task) for task in tasks]
        return await asyncio.gather(*tasks_list, return_exceptions=True)

    async def _execute_task_on_instance(self, instance: BrowserInstance, task: dict[str, Any]) -> Any:
        task_type = task.get("type")
        params = task.get("params", {})

        if task_type == "navigate":
            nav = NavigationController(instance)
            return await nav.navigate(params.get("url"))

        if task_type == "screenshot":
            screenshot = ScreenshotController(instance)
            return await screenshot.capture_full_page()

        if task_type == "execute_script":
            return instance.driver.execute_script(params.get("script"))

        raise ValueError(f"Unknown task type: {task_type}")

    @classmethod
    async def create_with_config(cls, config_path: str) -> "ChromeManager":
        manager = cls(config_file=config_path)
        await manager.initialize()
        return manager
