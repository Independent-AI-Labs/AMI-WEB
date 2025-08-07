#!/usr/bin/env python
"""Run integration tests with proper setup and teardown."""

import argparse
import asyncio
import sys
from pathlib import Path

import pytest
from loguru import logger

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.fixtures.test_server import HTMLTestServer


async def run_tests_with_server(args):
    """Run tests with test server."""
    server = None
    exit_code = 1

    try:
        # Start test HTML server
        logger.info("Starting test HTML server...")
        server = HTMLTestServer(port=8888)
        server_url = await server.start()
        logger.info(f"Test server running at {server_url}")

        # Prepare pytest arguments
        pytest_args = [
            "tests/integration",
            "-v",
            "--tb=short",
        ]

        if args.markers:
            pytest_args.extend(["-m", args.markers])

        if args.coverage:
            pytest_args.extend(["--cov=chrome_manager", "--cov-report=term-missing", "--cov-report=html:htmlcov"])

        if args.verbose:
            pytest_args.append("-vv")

        if args.specific_test:
            pytest_args.append(f"-k={args.specific_test}")

        if args.stop_on_failure:
            pytest_args.append("-x")

        # Run pytest
        logger.info(f"Running pytest with args: {pytest_args}")
        exit_code = pytest.main(pytest_args)

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        exit_code = 1

    finally:
        # Stop test server
        if server:
            logger.info("Stopping test server...")
            await server.stop()

    return exit_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Chrome Manager integration tests")
    parser.add_argument("--markers", "-m", help="Run tests matching given mark expression (e.g., 'mcp', 'browser', 'not slow')")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--specific-test", "-k", help="Run specific test by name pattern")
    parser.add_argument("--stop-on-failure", "-x", action="store_true", help="Stop on first failure")
    parser.add_argument("--no-server", action="store_true", help="Don't start test server (use existing one)")

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.add(sys.stderr, level=log_level)

    if args.no_server:
        # Run tests without starting server
        pytest_args = ["tests/integration", "-v"]
        if args.markers:
            pytest_args.extend(["-m", args.markers])
        exit_code = pytest.main(pytest_args)
    else:
        # Run tests with server
        exit_code = asyncio.run(run_tests_with_server(args))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
