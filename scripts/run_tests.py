#!/usr/bin/env python
"""Test runner for browser module."""

import sys
from pathlib import Path

# Path setup FIRST
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from ami_path import setup_ami_paths  # noqa: E402, I001

ORCHESTRATOR_ROOT, MODULE_ROOT, MODULE_NAME = setup_ami_paths()

# NOW other imports
from base.scripts.run_tests import main  # noqa: E402

if __name__ == "__main__":
    # Run tests using base test runner with browser module root
    sys.exit(main(project_root=MODULE_ROOT, project_name="Browser"))
