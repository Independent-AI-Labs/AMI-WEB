"""Chrome Manager v2 - using the new base worker pool system."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

# Add base to path for imports
base_path = Path(__file__).parent.parent.parent.parent.parent / "base"
if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

from workers.types import PoolConfig, PoolType

from ...facade.media.screenshot import ScreenshotController
from ...facade.navigation.navigator import Navigator
from ...models.browser import BrowserStatus, ChromeOptions, InstanceInfo
from ...models.browser_properties import BrowserProperties
from ...models.security import SecurityConfig
from ...utils.config import Config
from ..browser.instance import BrowserInstance
from ..browser.properties_manager import PropertiesManager
from .browser_worker_pool import BrowserWorkerPool
from .profile_manager import ProfileManager
from .session_manager import SessionManager


class ChromeManagerV2:
    """Chrome Manager using the new base worker pool system."""

    def __init__(self, config_file: str | None = None):
        self.config = Config.load(config_file) if config_file else Config()
        self.properties_manager = PropertiesManager(self.config)
        self.profile_manager = ProfileManager(
            base_dir=self.config.get("backend.storage.profiles_dir", "./data/browser_profiles")
        )
        
        # Create pool configuration
        pool_config = PoolConfig(
            name="browser_pool",
            pool_type=PoolType.THREAD,  # Browsers run in threads
            min_workers=self.config.get("backend.pool.min_instances", 1),
            max_workers=self.config.get("backend.pool.max_instances", 10),
            warm_workers=self.config.get("backend.pool.warm_instances", 2),
            worker_ttl=self.config.get("backend.pool.instance_ttl", 3600),
            health_check_interval=self.config.get("backend.pool.health_check_interval", 30),
            enable_hibernation=True,
            hibernation_delay=60,  # Hibernate after 60 seconds of inactivity
        )
        
        # Create the browser worker pool
        self.pool = BrowserWorkerPool(
            config=pool_config,
            browser_config=self.config,
            properties_manager=self.properties_manager,
            profile_manager=self.profile_manager,
        )
        
        self.session_manager = SessionManager(
            session_dir=self.config.get("backend.storage.session_dir", "./data/sessions")
        )
        
        # Track instances created outside the pool
        self._standalone_instances: dict[str, BrowserInstance] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the Chrome Manager."""
        if self._initialized:
            return

        logger.info("Initializing Chrome Manager V2")
        await self.pool.initialize()
        await self.session_manager.initialize()
        self._initialized = True
        logger.info("Chrome Manager V2 initialized successfully")

    async def start(self):
        """Alias for initialize() for backward compatibility."""
        await self.initialize()

    async def shutdown(self):
        """Shutdown the Chrome Manager."""
        logger.info("Shutting down Chrome Manager V2")
        
        # Shutdown the pool
        await self.pool.shutdown()
        
        # Shutdown session manager
        await self.session_manager.shutdown()

        # Terminate standalone instances
        for instance in self._standalone_instances.values():
            await instance.terminate()

        self._standalone_instances.clear()
        self._initialized = False
        logger.info("Chrome Manager V2 shutdown complete")

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
        anti_detect: bool = True,
        security_config: "SecurityConfig | None" = None,
        download_dir: str | None = None,
    ) -> BrowserInstance:
        """Get or create a browser instance.
        
        Args:
            headless: Run in headless mode
            profile: Browser profile to use
            extensions: List of extension paths
            options: Chrome options
            use_pool: Whether to use the pool (default True)
            anti_detect: Enable anti-detection features
            security_config: Security configuration
            download_dir: Download directory
            
        Returns:
            A browser instance
        """
        if not self._initialized:
            await self.initialize()

        if use_pool:
            # Get instance from pool
            opts = options or ChromeOptions(headless=headless, extensions=extensions or [])
            # Pass anti_detect through kwargs instead of modifying the options object
            
            # Acquire a browser from the pool
            instance = await self.pool.acquire_browser(opts)
            logger.info(f"Got browser instance {instance.id} from pool")
            return instance
        else:
            # Create standalone instance
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
            
            self._standalone_instances[instance.id] = instance
            logger.info(f"Created standalone browser instance {instance.id}")
            return instance

    async def get_instance(self, instance_id: str) -> BrowserInstance | None:
        """Get an instance by ID.
        
        Args:
            instance_id: The instance ID
            
        Returns:
            The browser instance or None if not found
        """
        # Check pool first
        for worker in self.pool._workers.values():
            if worker.instance.id == instance_id:
                return worker.instance
        
        # Check standalone instances
        return self._standalone_instances.get(instance_id)

    async def return_to_pool(self, instance_id: str) -> bool:
        """Return an instance to the pool for reuse.
        
        Args:
            instance_id: The instance ID
            
        Returns:
            True if successful, False otherwise
        """
        # Check if it's a pool instance
        for worker in self.pool._workers.values():
            if worker.instance.id == instance_id:
                await self.pool.release_browser(instance_id)
                logger.info(f"Returned instance {instance_id} to pool for reuse")
                return True
        
        # Check standalone instances
        instance = self._standalone_instances.get(instance_id)
        if instance:
            # Can't return standalone to pool, just terminate
            await instance.terminate()
            self._standalone_instances.pop(instance_id, None)
            logger.info(f"Terminated standalone instance {instance_id}")
            return True
            
        logger.warning(f"Instance {instance_id} not found")
        return False

    async def terminate_instance(self, instance_id: str, return_to_pool: bool = False) -> bool:
        """Terminate a browser instance.
        
        Args:
            instance_id: ID of instance to terminate
            return_to_pool: If True, return to pool for reuse. If False, fully terminate.
                          Default is False to ensure proper cleanup.
                          
        Returns:
            True if successful, False otherwise
        """
        if return_to_pool:
            return await self.return_to_pool(instance_id)
        
        # Check pool instances
        workers_dict = getattr(self.pool, 'workers', {})
        for worker in workers_dict.values():
            if worker.instance.id == instance_id:
                # Remove from pool and terminate
                await worker.cleanup()
                # Remove worker from pool
                if worker.id in self.pool._workers:
                    del self.pool._workers[worker.id]
                logger.info(f"Terminated pool instance {instance_id}")
                return True
        
        # Check standalone instances
        instance = self._standalone_instances.pop(instance_id, None)
        if instance:
            await instance.terminate()
            logger.info(f"Terminated standalone instance {instance_id}")
            return True
            
        logger.warning(f"Instance {instance_id} not found")
        return False

    async def list_instances(self) -> list[InstanceInfo]:
        """List all browser instances.
        
        Returns:
            List of instance information
        """
        instances = []
        
        # Get pool instances
        for worker in self.pool._workers.values():
            instance = worker.instance
            instances.append(
                InstanceInfo(
                    id=instance.id,
                    status=BrowserStatus.READY if worker.state.value == "idle" else BrowserStatus.BUSY,
                    created_at=instance.created_at,
                    last_activity=worker.last_used,
                    memory_usage=0,  # Not tracked currently
                    cpu_usage=0.0,  # Not tracked currently
                    active_tabs=len(instance.driver.window_handles) if instance.driver else 1,
                    profile=None,
                    headless=True,
                )
            )
        
        # Get standalone instances
        for instance in self._standalone_instances.values():
            instances.append(
                InstanceInfo(
                    id=instance.id,
                    status=BrowserStatus.READY,
                    created_at=instance.created_at,
                    last_activity=datetime.now(),
                    memory_usage=0,  # Not tracked currently
                    cpu_usage=0.0,  # Not tracked currently
                    active_tabs=len(instance.driver.window_handles) if instance.driver else 1,
                    profile=None,
                    headless=True,
                )
            )
        
        return instances

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get pool statistics.
        
        Returns:
            Pool statistics dictionary
        """
        stats = self.pool.get_stats()
        return {
            "name": stats.name,
            "pool_type": stats.pool_type.value,
            "total_instances": stats.total_workers,
            "available": stats.idle_workers,
            "in_use": stats.busy_workers,
            "hibernating": stats.hibernating_workers,
            "pending_tasks": stats.pending_tasks,
            "completed_tasks": stats.completed_tasks,
            "failed_tasks": stats.failed_tasks,
            "average_task_time": stats.average_task_time,
            "uptime_seconds": stats.uptime_seconds,
            "standalone_instances": len(self._standalone_instances),
        }

    async def save_session(self, instance_id: str, name: str | None = None) -> str:
        """Save browser session.
        
        Args:
            instance_id: Instance ID
            name: Optional session name
            
        Returns:
            Session ID
        """
        instance = await self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        cookies = instance.driver.get_cookies()
        local_storage = instance.driver.execute_script("return window.localStorage")
        session_storage = instance.driver.execute_script("return window.sessionStorage")

        session_id = await self.session_manager.save_session(
            instance_id=instance_id,
            cookies=cookies,
            local_storage=local_storage,
            session_storage=session_storage,
            url=instance.driver.current_url,
            name=name,
        )

        logger.info(f"Saved session {session_id} for instance {instance_id}")
        return session_id

    async def restore_session(self, session_id: str, instance_id: str | None = None) -> BrowserInstance:
        """Restore browser session.
        
        Args:
            session_id: Session ID to restore
            instance_id: Optional instance ID to restore into
            
        Returns:
            Browser instance with restored session
        """
        session_data = await self.session_manager.load_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        if instance_id:
            instance = await self.get_instance(instance_id)
            if not instance:
                raise ValueError(f"Instance {instance_id} not found")
        else:
            instance = await self.get_or_create_instance()

        # Navigate to the saved URL
        instance.driver.get(session_data["url"])

        # Restore cookies
        for cookie in session_data["cookies"]:
            instance.driver.add_cookie(cookie)

        # Restore local storage
        for key, value in session_data.get("local_storage", {}).items():
            instance.driver.execute_script(f"window.localStorage.setItem('{key}', '{value}')")

        # Restore session storage
        for key, value in session_data.get("session_storage", {}).items():
            instance.driver.execute_script(f"window.sessionStorage.setItem('{key}', '{value}')")

        # Refresh to apply cookies
        instance.driver.refresh()

        logger.info(f"Restored session {session_id} to instance {instance.id}")
        return instance

    async def navigate(self, instance_id: str, url: str) -> dict:
        """Navigate to URL.
        
        Args:
            instance_id: Instance ID
            url: URL to navigate to
            
        Returns:
            Navigation result
        """
        instance = await self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        nav = Navigator(instance)
        return await nav.navigate(url)

    async def screenshot(self, instance_id: str, full_page: bool = False) -> bytes:
        """Take screenshot.
        
        Args:
            instance_id: Instance ID
            full_page: Whether to capture full page
            
        Returns:
            Screenshot bytes
        """
        instance = await self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        screenshot_ctrl = ScreenshotController(instance)
        if full_page:
            return await screenshot_ctrl.capture_full_page()
        return await screenshot_ctrl.capture_viewport()

    async def execute_script(self, instance_id: str, script: str, *args) -> Any:
        """Execute JavaScript.
        
        Args:
            instance_id: Instance ID
            script: JavaScript to execute
            args: Script arguments
            
        Returns:
            Script result
        """
        instance = await self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        return instance.driver.execute_script(script, *args)