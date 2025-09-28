#!/usr/bin/env python
"""Test runner for browser module."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return
        current = current.parent


def main() -> int:
    _ensure_repo_on_path()

    from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: PLC0415
    from base.scripts.run_tests import TestRunner  # noqa: PLC0415

    ensure_module_venv(Path(__file__))

    module_root = Path(__file__).resolve().parent.parent
    args = sys.argv[1:]
    if "--timeout" not in " ".join(args):
        args = [*args, "--timeout", "600"]

    runner = TestRunner(project_root=module_root, project_name="Browser")
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())
