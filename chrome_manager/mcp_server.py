#!/usr/bin/env python3
import argparse
import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from chrome_manager.core.manager import ChromeManager
from chrome_manager.mcp.server import MCPServer
from chrome_manager.utils.config import Config


def setup_logging(log_level: str = "INFO"):
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(log_dir / "chrome_manager_{time}.log", rotation="1 day", retention="7 days", level="DEBUG")


async def main():
    parser = argparse.ArgumentParser(description="Chrome Manager MCP Server")
    parser.add_argument("--config", type=str, help="Configuration file path (YAML or JSON)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)")  # noqa: S104
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--headless", action="store_true", help="Run browsers in headless mode by default")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Logging level")
    parser.add_argument("--max-instances", type=int, default=10, help="Maximum number of browser instances")

    args = parser.parse_args()

    setup_logging(args.log_level)

    logger.info("Starting Chrome Manager MCP Server")

    config = Config.load(args.config) if args.config else Config()

    if args.host:
        config._data.setdefault("chrome_manager", {}).setdefault("mcp", {})["server_host"] = args.host
    if args.port:
        config._data.setdefault("chrome_manager", {}).setdefault("mcp", {})["server_port"] = args.port
    if args.headless:
        config._data.setdefault("chrome_manager", {}).setdefault("browser", {})["default_headless"] = True
    if args.max_instances:
        config._data.setdefault("chrome_manager", {}).setdefault("pool", {})["max_instances"] = args.max_instances

    manager = ChromeManager(config_file=args.config)
    await manager.initialize()

    mcp_config = config._data.get("chrome_manager", {}).get("mcp", {})
    server = MCPServer(manager, mcp_config)

    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):  # noqa: ARG001
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.start()

        logger.info(f"MCP Server running on {mcp_config.get('server_host', '0.0.0.0')}:{mcp_config.get('server_port', 8765)}")  # noqa: S104
        logger.info("Press Ctrl+C to stop")

        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Shutting down server...")
        await server.stop()
        await manager.shutdown()
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
