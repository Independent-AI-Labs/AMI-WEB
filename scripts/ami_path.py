#!/usr/bin/env python
"""AMI Path Setup - Standalone, zero-dependency path configuration for AMI modules.

This file should be copied to every module's /scripts/ directory.
It sets up Python paths for cross-module imports without any dependencies.
"""

import sys
from pathlib import Path


def setup_ami_paths() -> tuple[Path | None, Path, str]:
    """Automatically configure Python paths for AMI module imports.

    Works from any location within an AMI module structure.
    Adds both orchestrator root and module root to sys.path.

    Returns:
        tuple: (orchestrator_root, module_root, module_name)

    Raises:
        RuntimeError: If module structure cannot be determined
    """
    # Get absolute path of current file
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent

    # Find module root (contains backend/ or scripts/)
    module_root = current_dir
    if current_dir.name in ("scripts", "tests"):
        module_root = current_dir.parent

    # Traverse up to find module root
    original_path = module_root
    while module_root.parent != module_root:
        # Check for module indicators
        if ((module_root / "backend").exists() or (module_root / "scripts").exists()) and (
            (module_root / "requirements.txt").exists() or (module_root / ".venv").exists()
        ):
            break
        module_root = module_root.parent
    else:
        # Couldn't find module root
        raise RuntimeError(f"Could not find module root from {original_path}")

    # Find orchestrator root (contains .git and base/)
    orchestrator_root: Path | None = module_root
    while orchestrator_root and orchestrator_root.parent != orchestrator_root:
        if (orchestrator_root / ".git").exists() and (orchestrator_root / "base").exists():
            break
        orchestrator_root = orchestrator_root.parent
    else:
        # Couldn't find orchestrator, might be running standalone
        orchestrator_root = None

    # Determine module name
    module_name = module_root.name

    # Add paths to sys.path in correct order
    paths_to_add = []

    # Add orchestrator root first (for cross-module imports)
    if orchestrator_root and str(orchestrator_root) not in sys.path:
        paths_to_add.append(str(orchestrator_root))

    # Add module root (for module-specific imports)
    if str(module_root) not in sys.path:
        paths_to_add.append(str(module_root))

    # Insert paths at beginning of sys.path
    for path in reversed(paths_to_add):
        sys.path.insert(0, path)

    return orchestrator_root, module_root, module_name


# Auto-execute on import to set up paths immediately
# Global variables with type annotations
ORCHESTRATOR_ROOT: Path | None
MODULE_ROOT: Path | None
MODULE_NAME: str | None

try:
    ORCHESTRATOR_ROOT, MODULE_ROOT, MODULE_NAME = setup_ami_paths()
except RuntimeError as e:
    # If we can't find paths, set to None but don't fail import
    print(f"Warning: Could not set up AMI paths: {e}", file=sys.stderr)
    ORCHESTRATOR_ROOT = None
    MODULE_ROOT = None
    MODULE_NAME = None


# Provide convenience function for scripts
def get_paths() -> tuple[Path | None, Path | None, str | None]:
    """Get the configured paths.

    Returns:
        tuple: (orchestrator_root, module_root, module_name)
    """
    return ORCHESTRATOR_ROOT, MODULE_ROOT, MODULE_NAME


if __name__ == "__main__":
    # Test/debug output when run directly
    print(f"Orchestrator Root: {ORCHESTRATOR_ROOT}")
    print(f"Module Root: {MODULE_ROOT}")
    print(f"Module Name: {MODULE_NAME}")
    print("\nsys.path entries added:")
    if ORCHESTRATOR_ROOT:
        print(f"  - {ORCHESTRATOR_ROOT}")
    if MODULE_ROOT:
        print(f"  - {MODULE_ROOT}")
