#!/usr/bin/env python
"""Run fast unit tests only (skip slow integration tests)."""

import subprocess
import sys


def main():
    """Run fast tests only."""
    print("=" * 60)
    print("Running FAST unit tests only (skipping slow integration tests)")
    print("=" * 60)

    # Run pytest with markers to exclude slow tests
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "not slow",  # Exclude slow tests
        "--tb=short",
        "-q",  # Quiet mode for faster output
        "--disable-warnings",
        "tests/unit/",  # Only run unit tests
        *sys.argv[1:],  # Pass any additional arguments
    ]

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
