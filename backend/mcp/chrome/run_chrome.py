#!/usr/bin/env python
"""Run Browser MCP server."""

import asyncio
import sys
from pathlib import Path

# STANDARD IMPORT SETUP - DO NOT MODIFY
current_file = Path(__file__).resolve()
orchestrator_root = current_file
while orchestrator_root != orchestrator_root.parent:
    if (orchestrator_root / ".git").exists() and (orchestrator_root / "base").exists():
        break
    orchestrator_root = orchestrator_root.parent
else:
    raise RuntimeError(f"Could not find orchestrator root from {current_file}")

if str(orchestrator_root) not in sys.path:
    sys.path.insert(0, str(orchestrator_root))

module_names = {"base", "browser", "files", "compliance", "domains", "streams"}
module_root = current_file.parent
while module_root != orchestrator_root:
    if module_root.name in module_names:
        if str(module_root) not in sys.path:
            sys.path.insert(0, str(module_root))
        break
    module_root = module_root.parent

from base.backend.utils.module_setup import ModuleSetup  # noqa: E402

ModuleSetup.ensure_running_in_venv(Path(__file__))

# Now import the server components
from base.scripts.run_mcp_server import run_stdio  # noqa: E402
from browser.backend.core.management.manager import ChromeManager  # noqa: E402
from browser.backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402


async def main():
    """Run the Browser MCP server."""
    # Get config file if exists
    config_file = None
    for name in ["config.yaml", "config.test.yaml"]:
        path = module_root / name
        if path.exists():
            config_file = str(path)
            break

    # Create manager
    manager = ChromeManager(config_file=config_file) if config_file else ChromeManager()
    await manager.initialize()
    manager.pool.min_instances = 0
    manager.pool.warm_instances = 0

    # Custom server that handles cleanup
    class ManagedBrowserServer(BrowserMCPServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, manager=manager, **kwargs)

        async def __aexit__(self, *args):
            await manager.shutdown()
            return await super().__aexit__(*args) if hasattr(super(), "__aexit__") else None

    # Run the server
    await run_stdio(ManagedBrowserServer, {})


if __name__ == "__main__":
    asyncio.run(main())
