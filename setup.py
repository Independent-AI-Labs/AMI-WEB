#!/usr/bin/env python
"""Browser module setup - uses base GenericSetup."""

import sys
from pathlib import Path

# Get this module's root
MODULE_ROOT = Path(__file__).resolve().parent

# Find and import base setup
current = MODULE_ROOT.parent
if (current / "base").exists() and (current / ".git").exists():
    sys.path.insert(0, str(current / "base"))
else:
    print("ERROR: Cannot find base module")
    sys.exit(1)

from setup import main as base_main  # noqa: E402


def main():
    """Run setup for browser module."""
    # Pass package info to match the module
    package_info = {
        "name": "ami-web",
        "version": "0.1.0",
    }
    return base_main(project_root=MODULE_ROOT, project_name="Browser Module", package_info=package_info)


if __name__ == "__main__":
    sys.exit(main())
