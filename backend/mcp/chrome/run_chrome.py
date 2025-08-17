#!/usr/bin/env python
"""Run Browser MCP server."""

import sys
from pathlib import Path

# Bootstrap path discovery - find ORCHESTRATOR ROOT (parent with base/ submodule)
current = Path(__file__).resolve().parent
orchestrator_root = None
while current != current.parent:
    if (current / ".git").exists() and (current / "base").exists():
        # Found the main orchestrator root
        orchestrator_root = current
        break
    current = current.parent

if not orchestrator_root:
    raise RuntimeError("Could not find orchestrator root")

# Add orchestrator root to path FIRST so we can import both base and local modules properly
sys.path.insert(0, str(orchestrator_root))

# Now import from base using proper namespace
from base.backend.utils.path_finder import setup_base_import  # noqa: E402

setup_base_import(Path(__file__))

from base.backend.mcp.run_server import setup_environment  # noqa: E402

if __name__ == "__main__":
    # Setup environment first (will re-exec if needed)
    module_root, python = setup_environment(Path(__file__))

    # Add browser module root to sys.path
    sys.path.insert(0, str(module_root))

    # NOW import after environment is set up
    import asyncio

    from base.backend.mcp.run_server import run_server
    from browser.backend.core.management.manager import ChromeManager
    from browser.backend.mcp.chrome.server import BrowserMCPServer

    # Parse transport from args
    transport = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] in ["websocket", "ws"]:
        transport = "websocket"

    # Get config file if exists
    config_file = None
    for name in ["config.yaml", "config.test.yaml"]:
        path = module_root / name
        if path.exists():
            config_file = str(path)
            break

    # Create manager
    async def create_manager():
        manager = ChromeManager(config_file=config_file) if config_file else ChromeManager()
        await manager.initialize()
        manager.pool.min_instances = 0
        manager.pool.warm_instances = 0
        return manager

    # Create manager synchronously
    manager = asyncio.run(create_manager())

    # Custom server that handles cleanup
    class ManagedBrowserServer(BrowserMCPServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, manager=manager, **kwargs)

        async def __aexit__(self, *args):
            await manager.shutdown()
            return await super().__aexit__(*args) if hasattr(super(), "__aexit__") else None

    run_server(
        server_class=ManagedBrowserServer,
        transport=transport,
        port=8765,  # Browser uses 8765
    )
