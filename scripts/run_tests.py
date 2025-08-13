#!/usr/bin/env python
"""Test runner that ensures correct environment and handles all test execution."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # Go up one level from scripts/
VENV_PATH = PROJECT_ROOT / ".venv"
VENV_PYTHON = VENV_PATH / "Scripts" / "python.exe" if sys.platform == "win32" else VENV_PATH / "bin" / "python"
BASE_REPO_URL = "https://github.com/Independent-AI-Labs/AMI-BASE.git"


def ensure_base_module():
    """Ensure the base module is available either from parent or locally."""
    # Check if we're in a submodule context (parent has base)
    parent_base = PROJECT_ROOT.parent / "base"
    local_base = PROJECT_ROOT / "base"
    
    if parent_base.exists() and (parent_base / "mcp").exists():
        print(f"Using base module from parent directory: {parent_base}")
        return str(parent_base.parent)  # Return parent directory to add to PYTHONPATH
    elif local_base.exists() and (local_base / "mcp").exists():
        print(f"Using existing local base module: {local_base}")
        return str(PROJECT_ROOT)  # Return project root to add to PYTHONPATH
    else:
        # Clone the base module repository
        print(f"Base module not found. Cloning from {BASE_REPO_URL}...")
        try:
            subprocess.run(["git", "clone", BASE_REPO_URL, str(local_base)], check=True, cwd=PROJECT_ROOT)
            print(f"Successfully cloned base module to: {local_base}")
            return str(PROJECT_ROOT)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to clone base module: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("ERROR: git is not installed!")
            sys.exit(1)


def check_uv():
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: uv is not installed!")
        print("Install it with: pip install uv")
        return False


def setup_environment():
    """Set up the virtual environment if needed."""
    if not check_uv():
        sys.exit(1)

    # Create venv if it doesn't exist
    if not VENV_PATH.exists():
        print("Creating virtual environment with uv...")
        subprocess.run(["uv", "venv", str(VENV_PATH)], check=True)

    # Install dependencies from requirements.txt EXACTLY as specified
    print("Installing dependencies from requirements.txt...")
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if requirements_file.exists():
        subprocess.run(["uv", "pip", "install", "--python", str(VENV_PYTHON), "-r", str(requirements_file)], check=True, cwd=PROJECT_ROOT)
    else:
        print("ERROR: requirements.txt not found!")
        sys.exit(1)

    # Install test dependencies from requirements-test.txt
    test_requirements_file = PROJECT_ROOT / "requirements-test.txt"
    if test_requirements_file.exists():
        print("Installing test dependencies from requirements-test.txt...")
        subprocess.run(["uv", "pip", "install", "--python", str(VENV_PYTHON), "-r", str(test_requirements_file)], check=True, cwd=PROJECT_ROOT)

    # Install the package in editable mode
    subprocess.run(["uv", "pip", "install", "--python", str(VENV_PYTHON), "-e", "."], check=True, cwd=PROJECT_ROOT)

    if not VENV_PYTHON.exists():
        print(f"ERROR: Virtual environment Python not found at {VENV_PYTHON}")
        sys.exit(1)

    return VENV_PYTHON


def run_tests(test_args):
    """Run tests with the virtual environment Python."""
    venv_python = setup_environment()
    
    # Ensure base module is available
    base_path = ensure_base_module()

    # Build the test command
    cmd = [str(venv_python), "-m", "pytest"]

    # Add default args if none provided
    if not test_args:
        test_args = ["tests/", "-v", "--tb=short"]

    cmd.extend(test_args)

    # Set environment variables
    env = os.environ.copy()
    # Add both project root and base path to PYTHONPATH
    python_paths = [str(PROJECT_ROOT)]
    if base_path != str(PROJECT_ROOT):
        python_paths.append(base_path)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)

    # Run the tests
    print(f"\nRunning: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, check=False)
    return result.returncode


def main():
    """Main entry point."""
    # Get test arguments from command line
    test_args = sys.argv[1:]

    # Special commands
    if test_args and test_args[0] == "--help":
        print("Test Runner for Chrome Manager")
        print("=" * 40)
        print("\nUsage:")
        print("  python run_tests.py [pytest args]")
        print("\nExamples:")
        print("  python run_tests.py                    # Run all tests")
        print("  python run_tests.py tests/unit/        # Run unit tests")
        print("  python run_tests.py -k test_properties # Run tests matching pattern")
        print("  python run_tests.py -x                 # Stop on first failure")
        print("  python run_tests.py --lf               # Run last failed tests")
        print("\nSpecial commands:")
        print("  python run_tests.py --clean            # Clean and rebuild environment")
        print("  python run_tests.py --shell            # Open shell in test environment")
        return 0

    if test_args and test_args[0] == "--clean":
        print("Cleaning environment...")
        import shutil

        if VENV_PATH.exists():
            shutil.rmtree(VENV_PATH)
        print("Environment cleaned. Re-run to rebuild.")
        return 0

    if test_args and test_args[0] == "--shell":
        print("Opening shell in test environment...")
        venv_python = setup_environment()
        
        # Ensure base module is available
        base_path = ensure_base_module()
        
        env = os.environ.copy()
        # Add both project root and base path to PYTHONPATH
        python_paths = [str(PROJECT_ROOT)]
        if base_path != str(PROJECT_ROOT):
            python_paths.append(base_path)
        env["PYTHONPATH"] = os.pathsep.join(python_paths)

        if sys.platform == "win32":
            # On Windows, activate the venv and open cmd
            activate_script = VENV_PATH / "Scripts" / "activate.bat"
            subprocess.run(["cmd", "/k", str(activate_script)], cwd=PROJECT_ROOT, env=env, check=False)
        else:
            # On Unix, start a shell with activated venv
            subprocess.run([str(venv_python)], cwd=PROJECT_ROOT, env=env, check=False)
        return 0

    # Run the tests
    return run_tests(test_args)


if __name__ == "__main__":
    sys.exit(main())
