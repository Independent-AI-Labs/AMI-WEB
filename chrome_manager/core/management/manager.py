import asyncio
from typing import Any

from loguru import logger

from ...facade.media import ScreenshotController
from ...facade.navigation import NavigationController
from ...models.browser import ChromeOptions, InstanceInfo
from ...models.browser_properties import BrowserProperties
from ...models.security import SecurityConfig
from ...utils.config import Config
from ..browser.instance import BrowserInstance
from ..browser.properties_manager import PropertiesManager
from .pool import BrowserPool
from .profile_manager import ProfileManager
from .session_manager import SessionManager


class ChromeManager:
    def __init__(self, config_file: str | None = None):
        self.config = Config.load(config_file) if config_file else Config()
        self.properties_manager = PropertiesManager(self.config)
        self.profile_manager = ProfileManager(base_dir=self.config.get("chrome_manager.storage.profiles_dir", "./browser_profiles"))
        self.pool = BrowserPool(
            min_instances=self.config.get("chrome_manager.pool.min_instances", 1),
            max_instances=self.config.get("chrome_manager.pool.max_instances", 10),
            warm_instances=self.config.get("chrome_manager.pool.warm_instances", 2),
            instance_ttl=self.config.get("chrome_manager.pool.instance_ttl", 3600),
            health_check_interval=self.config.get("chrome_manager.pool.health_check_interval", 30),
            config=self.config,
            properties_manager=self.properties_manager,
            profile_manager=self.profile_manager,
        )
        self.session_manager = SessionManager(session_dir=self.config.get("chrome_manager.storage.session_dir", "./sessions"))
        self._instances: dict[str, BrowserInstance] = {}
        self._initialized = False
        self._next_security_config: "SecurityConfig | None" = None  # For MCP security configuration

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
        anti_detect: bool = True,  # Enable anti-detect by default for MCP
        security_config: "SecurityConfig | None" = None,
        download_dir: str | None = None,
    ) -> BrowserInstance:
        if not self._initialized:
            await self.initialize()

        # Use _next_security_config if set via MCP and no security_config provided
        if not security_config and self._next_security_config:
            security_config = self._next_security_config
            self._next_security_config = None  # Reset after use

        if use_pool:
            opts = options or ChromeOptions(headless=headless, extensions=extensions or [])
            instance = await self.pool.acquire(opts)
        else:
            instance = BrowserInstance(
                config=self.config,
                properties_manager=self.properties_manager,
                profile_manager=self.profile_manager,
            )
            await instance.launch(
                headless=headless,
                profile=profile,
                extensions=extensions,
                options=options,
                anti_detect=anti_detect,
                security_config=security_config,
                download_dir=download_dir,
            )

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

        # Don't remove from _instances, just release to pool for reuse
        if instance.id in self.pool.all_instances:
            await self.pool.release(instance_id)
            logger.info(f"Returned instance {instance_id} to pool for reuse")
            return True
        # Not a pool instance, just terminate it
        await instance.terminate()
        self._instances.pop(instance_id, None)
        logger.info(f"Terminated non-pool instance {instance_id}")
        return True

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
        # Get session metadata
        sessions = await self.session_manager.list_sessions()
        session_data = next((s for s in sessions if s["id"] == session_id), None)

        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        # Create new instance with the saved profile
        instance = await self.get_or_create_instance(
            headless=False,  # Sessions typically restored in visible mode
            profile=session_data.get("profile"),
            use_pool=False,  # Don't use pool for restored sessions
            anti_detect=True,
        )

        # Navigate to saved URL
        if session_data.get("url"):
            instance.driver.get(session_data["url"])

        # Load saved cookies if profile has them
        instance.load_cookies()

        logger.info(f"Restored session {session_id} as instance {instance.id}")
        return instance

    async def get_pool_stats(self) -> dict:
        return self.pool.get_stats()

    # Browser Properties Management
    async def set_browser_properties(  # noqa: C901, PLR0912
        self, instance_id: str | None = None, tab_id: str | None = None, properties: BrowserProperties | dict[str, Any] | None = None, preset: str | None = None
    ) -> bool:
        """Set browser properties for an instance or tab."""
        # Create properties from preset if specified
        if preset:
            from ..models.browser_properties import BrowserPropertiesPreset, get_preset_properties

            try:
                preset_enum = BrowserPropertiesPreset(preset.lower())
                properties = get_preset_properties(preset_enum)
            except ValueError:
                logger.error(f"Invalid preset: {preset}")
                return False

        if not properties:
            logger.error("No properties or preset specified")
            return False

        # Set default properties if no instance specified
        if not instance_id:
            self.properties_manager.set_default_properties(properties)
            return True

        # Set instance or tab properties
        instance = await self.get_instance(instance_id)
        if not instance:
            logger.error(f"Instance {instance_id} not found")
            return False

        if tab_id:
            # Set tab-specific properties
            self.properties_manager.set_tab_properties(instance_id, tab_id, properties)
            # Inject into the specific tab if it exists
            if instance.driver:
                current_handle = instance.driver.current_window_handle
                try:
                    # Switch to target tab
                    for handle in instance.driver.window_handles:
                        instance.driver.switch_to.window(handle)
                        # Check if this is the target tab (would need tab ID mapping)
                        # For now, inject into current tab
                        if handle == tab_id or not tab_id:
                            props = self.properties_manager.get_tab_properties(instance_id, handle)
                            self.properties_manager.inject_properties(instance.driver, props, handle)
                            break
                finally:
                    # Switch back
                    instance.driver.switch_to.window(current_handle)
        else:
            # Set instance-wide properties
            self.properties_manager.set_instance_properties(instance_id, properties)
            # Inject into all tabs
            if instance.driver:
                props = self.properties_manager.get_instance_properties(instance_id)
                self.properties_manager.inject_properties(instance.driver, props)

        return True

    async def get_browser_properties(self, instance_id: str | None = None, tab_id: str | None = None) -> dict[str, Any]:
        """Get current browser properties."""
        if not instance_id:
            return self.properties_manager.export_properties()

        props = self.properties_manager.get_tab_properties(instance_id, tab_id) if tab_id else self.properties_manager.get_instance_properties(instance_id)

        return self.properties_manager.export_properties(props)

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
