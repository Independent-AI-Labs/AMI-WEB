#!/usr/bin/env python
"""Browser module setup - uses base AMIModuleSetup."""

import subprocess
import sys
from pathlib import Path

# Get this module's root
MODULE_ROOT = Path(__file__).resolve().parent


def main():
    """Run setup for browser module by calling base setup.py directly."""
    # Find base setup.py
    base_setup = MODULE_ROOT.parent / "base" / "setup.py"
    if not base_setup.exists():
        print("ERROR: Cannot find base/setup.py")
        sys.exit(1)

    # Call base setup.py with appropriate arguments
    cmd = [sys.executable, str(base_setup), "--project-dir", str(MODULE_ROOT), "--project-name", "Browser Module"]

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
