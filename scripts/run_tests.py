#!/usr/bin/env python
"""Test runner for browser module."""

from __future__ import annotations

import sys
from pathlib import Path

from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: E402
from base.scripts.run_tests import TestRunner  # noqa: E402


def main() -> int:
    ensure_module_venv(Path(__file__))

    browser_root = ORCHESTRATOR_ROOT / "browser"
    args = sys.argv[1:]
    if "--timeout" not in " ".join(args):
        args = [*args, "--timeout", "600"]

    runner = TestRunner(project_root=browser_root, project_name="Browser")
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())
