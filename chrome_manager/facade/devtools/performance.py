"""Performance monitoring and metrics collection."""

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from ...models.browser import PerformanceMetrics
from ...utils.exceptions import ChromeManagerError
from ..base import BaseController


class PerformanceController(BaseController):
    """Controller for performance monitoring and metrics."""

    async def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.

        Returns:
            PerformanceMetrics object with current values
        """
        try:
            # Get navigation timing
            navigation_timing = await self._execute_js(
                """
                const timing = performance.timing;
                return {
                    navigationStart: timing.navigationStart,
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart,
                    firstPaint: 0,
                    firstContentfulPaint: 0
                };
            """
            )

            # Get paint timing
            paint_timing = await self._execute_js(
                """
                const entries = performance.getEntriesByType('paint');
                const result = {};
                for (const entry of entries) {
                    if (entry.name === 'first-paint') {
                        result.firstPaint = entry.startTime;
                    } else if (entry.name === 'first-contentful-paint') {
                        result.firstContentfulPaint = entry.startTime;
                    }
                }
                return result;
            """
            )

            # Get memory info (if available)
            memory_info = await self._execute_js(
                """
                if (performance.memory) {
                    return {
                        usedJSHeapSize: performance.memory.usedJSHeapSize,
                        totalJSHeapSize: performance.memory.totalJSHeapSize,
                        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                    };
                }
                return null;
            """
            )

            # Combine metrics
            return PerformanceMetrics(  # type: ignore[call-arg]
                timestamp=datetime.now(),
                dom_content_loaded=navigation_timing.get("domContentLoaded", 0),
                load_complete=navigation_timing.get("loadComplete", 0),
                first_paint=paint_timing.get("firstPaint", 0),
                first_contentful_paint=paint_timing.get("firstContentfulPaint", 0),
                js_heap_used=memory_info.get("usedJSHeapSize", 0) if memory_info else 0,
                js_heap_total=memory_info.get("totalJSHeapSize", 0) if memory_info else 0,
            )

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            # Return minimal valid metrics on error
            return PerformanceMetrics(timestamp=datetime.now(), dom_content_loaded=0, load_complete=0)

    async def get_resource_timing(self) -> list[dict[str, Any]]:
        """Get resource loading timing information.

        Returns:
            List of resource timing entries
        """
        try:
            resources = await self._execute_js(
                """
                const entries = performance.getEntriesByType('resource');
                return entries.map(entry => ({
                    name: entry.name,
                    entryType: entry.entryType,
                    startTime: entry.startTime,
                    duration: entry.duration,
                    transferSize: entry.transferSize || 0,
                    encodedBodySize: entry.encodedBodySize || 0,
                    decodedBodySize: entry.decodedBodySize || 0,
                    initiatorType: entry.initiatorType
                }));
            """
            )
            return resources or []
        except Exception as e:
            logger.error(f"Failed to get resource timing: {e}")
            return []

    async def get_long_tasks(self) -> list[dict[str, Any]]:
        """Get long task timing information.

        Returns:
            List of long task entries
        """
        try:
            tasks = await self._execute_js(
                """
                const entries = performance.getEntriesByType('longtask');
                return entries.map(entry => ({
                    name: entry.name,
                    startTime: entry.startTime,
                    duration: entry.duration,
                    attribution: entry.attribution ? entry.attribution[0].name : null
                }));
            """
            )
            return tasks or []
        except Exception as e:
            logger.error(f"Failed to get long tasks: {e}")
            return []

    async def mark(self, name: str) -> None:
        """Create a performance mark.

        Args:
            name: Name of the mark
        """
        await self._execute_js(f"performance.mark('{name}')")
        logger.debug(f"Created performance mark: {name}")

    async def measure(self, name: str, start_mark: str, end_mark: str | None = None) -> float:
        """Create a performance measure between marks.

        Args:
            name: Name of the measure
            start_mark: Start mark name
            end_mark: End mark name (or None for current time)

        Returns:
            Duration of the measure in milliseconds
        """
        script = f"performance.measure('{name}', '{start_mark}', '{end_mark}')" if end_mark else f"performance.measure('{name}', '{start_mark}')"

        await self._execute_js(script)

        # Get the measure duration
        duration = await self._execute_js(
            f"""
            const entries = performance.getEntriesByName('{name}', 'measure');
            return entries.length > 0 ? entries[entries.length - 1].duration : 0;
        """
        )

        logger.debug(f"Measured '{name}': {duration}ms")
        return duration

    async def clear_marks(self, name: str | None = None) -> None:
        """Clear performance marks.

        Args:
            name: Specific mark to clear, or None to clear all
        """
        if name:
            await self._execute_js(f"performance.clearMarks('{name}')")
            logger.debug(f"Cleared mark: {name}")
        else:
            await self._execute_js("performance.clearMarks()")
            logger.debug("Cleared all marks")

    async def clear_measures(self, name: str | None = None) -> None:
        """Clear performance measures.

        Args:
            name: Specific measure to clear, or None to clear all
        """
        if name:
            await self._execute_js(f"performance.clearMeasures('{name}')")
            logger.debug(f"Cleared measure: {name}")
        else:
            await self._execute_js("performance.clearMeasures()")
            logger.debug("Cleared all measures")

    async def start_profiling(self) -> None:
        """Start CPU profiling."""
        await self._execute_cdp("Profiler.enable")
        await self._execute_cdp("Profiler.start")
        logger.info("CPU profiling started")

    async def stop_profiling(self) -> dict[str, Any]:
        """Stop CPU profiling and get results.

        Returns:
            Profiling data
        """
        result = await self._execute_cdp("Profiler.stop")
        await self._execute_cdp("Profiler.disable")
        logger.info("CPU profiling stopped")
        return result

    async def _execute_js(self, script: str) -> Any:
        """Execute JavaScript and return result.

        Args:
            script: JavaScript code to execute

        Returns:
            Script execution result
        """
        if not self.driver:
            raise ChromeManagerError("Browser not initialized")

        if self._is_in_thread_context():
            return self.driver.execute_script(script)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.driver.execute_script, script)

    async def _execute_cdp(self, command: str, params: dict | None = None) -> Any:
        """Execute CDP command.

        Args:
            command: CDP command name
            params: Command parameters

        Returns:
            Command result
        """
        if not self.driver:
            raise ChromeManagerError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                return self.driver.execute_cdp_cmd(command, params or {})  # type: ignore[attr-defined]
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.driver.execute_cdp_cmd, command, params or {})  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f"CDP command failed: {command}: {e}")
            raise ChromeManagerError(f"Failed to execute CDP command {command}: {e}") from e
