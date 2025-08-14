"""Chrome Manager using the base worker pool system."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

# Add base to path for imports
base_path = Path(__file__).parent.parent.parent.parent.parent / "base"
if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

from workers.types import PoolConfig, PoolType  # noqa: E402

from ...facade.media.screenshot import ScreenshotController  # noqa: E402
from ...facade.navigation.navigator import Navigator  # noqa: E402
from ...models.browser import BrowserStatus, ChromeOptions, InstanceInfo  # noqa: E402
from ...models.security import SecurityConfig  # noqa: E402
from ...utils.config import Config  # noqa: E402
from ..browser.instance import BrowserInstance  # noqa: E402
from ..browser.properties_manager import PropertiesManager  # noqa: E402
from .browser_worker_pool import BrowserWorkerPool  # noqa: E402
from .profile_manager import ProfileManager  # noqa: E402
from .session_manager import SessionManager  # noqa: E402


class ChromeManager:
    """Chrome Manager using the base worker pool system."""

    def __init__(self, config_file: str | None = None):
        self.config = Config.load(config_file) if config_file else Config()
        self.properties_manager = PropertiesManager(self.config)
        self.profile_manager = ProfileManager(base_dir=self.config.get("backend.storage.profiles_dir", "./data/browser_profiles"))

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

        self.session_manager = SessionManager(session_dir=self.config.get("backend.storage.session_dir", "./data/sessions"))

        # Track instances created outside the pool
        self._standalone_instances: dict[str, BrowserInstance] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the Chrome Manager."""
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
        """Shutdown the Chrome Manager."""
        logger.info("Shutting down Chrome Manager")

        # Shutdown the pool
        await self.pool.shutdown()

        # Shutdown session manager
        await self.session_manager.shutdown()

        # Terminate standalone instances
        for instance in self._standalone_instances.values():
            await instance.terminate()

        self._standalone_instances.clear()
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
            # Note: anti_detect is configured at pool creation time via backend.pool.anti_detect_default

            # Acquire a browser from the pool
            instance = await self.pool.acquire_browser(opts)
            logger.info(f"Got browser instance {instance.id} from pool")
            return instance
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
        workers_dict = getattr(self.pool, "workers", {})
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

        session_id = await self.session_manager.save_session(
            instance=instance,
            name=name,
        )

        logger.info(f"Saved session {session_id} for instance {instance_id}")
        return session_id

    async def restore_session(self, session_id: str, instance_id: str | None = None) -> BrowserInstance:  # noqa: ARG002
        """Restore browser session.

        Args:
            session_id: Session ID to restore
            instance_id: Optional instance ID to restore into (ignored, for compatibility)

        Returns:
            Browser instance with restored session
        """
        # SessionManager's restore_session creates a new instance
        instance = await self.session_manager.restore_session(session_id)

        # Track as standalone instance
        self._standalone_instances[instance.id] = instance

        logger.info(f"Restored session {session_id} to instance {instance.id}")
        return instance

    async def navigate(self, instance_id: str, url: str) -> dict[str, Any]:
        """Navigate to URL.

        Args:
            instance_id: Instance ID
            url: URL to navigate to

        Returns:
            Navigation result as dict
        """
        instance = await self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        nav = Navigator(instance)
        result = await nav.navigate(url)
        # Convert PageResult to dict for API compatibility
        return {
            "url": result.url,
            "title": result.title,
            "status_code": result.status_code,
            "load_time": result.load_time,
            "content_length": result.content_length,
            "html": result.html,
        }

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

    def _inject_properties_script(self, properties_json: str) -> str:
        """Generate the JavaScript to inject browser properties."""
        return f"""
            window.__browserProperties = {properties_json};

            // Handle specific properties
            if (window.__browserProperties.webgl_vendor) {{
                window.webgl_vendor = window.__browserProperties.webgl_vendor;
            }}
            if (window.__browserProperties.codec_support) {{
                window.codec_support = window.__browserProperties.codec_support;
            }}
        """

    def _apply_properties_to_tab(self, instance: Any, tab_id: str, browser_props: Any, properties_json: str) -> None:
        """Apply properties to a specific tab."""
        current_handle = instance.driver.current_window_handle
        if tab_id != current_handle:
            instance.driver.switch_to.window(tab_id)

        # Inject properties
        self.properties_manager.inject_properties(instance.driver, browser_props, tab_id)
        instance.driver.execute_script(self._inject_properties_script(properties_json))

        # Switch back if needed
        if tab_id != current_handle:
            instance.driver.switch_to.window(current_handle)

    def _apply_properties_to_all_tabs(self, instance: Any, browser_props: Any, properties_json: str) -> None:
        """Apply properties to all tabs."""
        handles = instance.driver.window_handles
        current_handle = instance.driver.current_window_handle

        for handle in handles:
            instance.driver.switch_to.window(handle)
            self.properties_manager.inject_properties(instance.driver, browser_props)
            instance.driver.execute_script(self._inject_properties_script(properties_json))

        instance.driver.switch_to.window(current_handle)

    async def set_browser_properties(
        self,
        instance_id: str,
        properties: dict[str, Any] | None = None,
        preset: str | None = None,
        tab_id: str | None = None,
    ) -> bool:
        """Set browser properties for an instance or specific tab.

        Args:
            instance_id: Instance ID
            properties: Properties dictionary to apply
            preset: Preset name to use (if properties not provided)
            tab_id: Optional tab ID for tab-specific properties

        Returns:
            True if successful, False otherwise
        """
        if not properties:
            return False

        instance = await self.get_instance(instance_id)
        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            return False

        # Convert to BrowserProperties
        from ...models.browser_properties import BrowserProperties, BrowserPropertiesPreset, get_preset_properties

        if preset:
            try:
                preset_enum = BrowserPropertiesPreset(preset)
                browser_props = get_preset_properties(preset_enum)
                # Apply overrides
                for key, value in (properties or {}).items():
                    if hasattr(browser_props, key):
                        setattr(browser_props, key, value)
            except ValueError:
                logger.warning(f"Invalid preset '{preset}', using properties only")
                browser_props = BrowserProperties(**properties) if isinstance(properties, dict) else properties
        else:
            browser_props = BrowserProperties(**properties) if isinstance(properties, dict) else properties

        # Prepare JSON for injection
        import json

        props_json = json.dumps(properties)

        # Apply to specific tab or all tabs
        if tab_id:
            self.properties_manager.set_tab_properties(instance_id, tab_id, browser_props)
            self._apply_properties_to_tab(instance, tab_id, browser_props, props_json)
        else:
            self.properties_manager.set_instance_properties(instance_id, browser_props)
            self._apply_properties_to_all_tabs(instance, browser_props, props_json)

        return True

    async def get_browser_properties(self, instance_id: str | None = None, tab_id: str | None = None) -> dict[str, Any]:
        """Get current browser properties.

        Args:
            instance_id: Instance ID (optional, returns default if not provided)
            tab_id: Optional tab ID for tab-specific properties

        Returns:
            Dictionary of browser properties
        """
        if not instance_id:
            # Return default properties
            return self.properties_manager.export_properties()

        # Get properties for specific instance
        instance = await self.get_instance(instance_id)
        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            return {}

        # If tab_id is provided, get properties from the properties manager
        if tab_id:
            # Get stored properties for this tab
            tab_props = self.properties_manager.get_tab_properties(instance_id, tab_id)
            return self.properties_manager.export_properties(tab_props)

        # Get current properties from the page
        try:
            # Get both standard and injected properties
            result = instance.driver.execute_script(
                """
                var props = {
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    language: navigator.language,
                    languages: navigator.languages,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory,
                    webdriver: navigator.webdriver,
                    vendor: navigator.vendor
                };

                // Get WebGL properties if available
                try {
                    var canvas = document.createElement('canvas');
                    var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (gl) {
                        var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                        if (debugInfo) {
                            props.webgl_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                            props.webgl_renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                        }
                    }
                } catch (e) {}

                // Get custom injected properties if they exist
                if (window.__browserProperties) {
                    Object.assign(props, window.__browserProperties);
                }

                // Get codec support if defined
                if (window.codec_support) {
                    props.codec_support = window.codec_support;
                }

                return props;
            """
            )
            return result  # noqa: RET504
        except Exception as e:
            logger.error(f"Failed to get browser properties: {e}")
            return {}
