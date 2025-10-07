"""Integration tests for pre-commit hooks infrastructure.

These tests validate that the CI/CD pipeline hooks (ruff, mypy, pre-commit, pre-push)
are configured correctly and execute as expected.
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root(browser_root: Path) -> Path:
    """Get the repository root directory."""
    return browser_root.parent


class TestRuffLinting:
    """Test suite for Ruff linting hook."""

    def test_ruff_executable_exists(self, browser_root: Path) -> None:
        """Verify Ruff is installed and accessible."""
        result = subprocess.run(
            [str(browser_root / ".venv" / "bin" / "ruff"), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Ruff not found or failed: {result.stderr}"
        assert (
            "ruff" in result.stdout.lower()
        ), f"Unexpected ruff version output: {result.stdout}"

    def test_ruff_check_runs_successfully(self, browser_root: Path) -> None:
        """Verify Ruff can run check on the module."""
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "ruff"),
                "check",
                str(browser_root),
                "--config",
                str(browser_root / "pyproject.toml"),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # Should either pass (0) or find fixable issues (1)
        assert result.returncode in (
            0,
            1,
        ), f"Ruff check failed unexpectedly: {result.stderr}"

    def test_ruff_format_check_runs_successfully(self, browser_root: Path) -> None:
        """Verify Ruff format checker runs."""
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "ruff"),
                "format",
                "--check",
                str(browser_root),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # Should either pass (0) or find formatting issues (1)
        assert result.returncode in (
            0,
            1,
        ), f"Ruff format check failed unexpectedly: {result.stderr}"


class TestMypyTypeChecking:
    """Test suite for Mypy type checking hook."""

    def test_mypy_executable_exists(self, browser_root: Path) -> None:
        """Verify Mypy is installed and accessible."""
        result = subprocess.run(
            [str(browser_root / ".venv" / "bin" / "mypy"), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Mypy not found or failed: {result.stderr}"
        assert (
            "mypy" in result.stdout.lower()
        ), f"Unexpected mypy version output: {result.stdout}"

    def test_mypy_config_exists(self, browser_root: Path) -> None:
        """Verify mypy.ini configuration file exists."""
        mypy_ini = browser_root / "mypy.ini"
        assert mypy_ini.exists(), f"mypy.ini not found at {mypy_ini}"

    def test_mypy_runs_successfully(self, browser_root: Path) -> None:
        """Verify Mypy can run type checking on the module."""
        module_name = browser_root.name
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "mypy"),
                "-p",
                module_name,
                "--config-file",
                str(browser_root / "mypy.ini"),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root.parent),  # Run from repo root
        )
        # Mypy may find errors (non-zero) but should not crash
        assert (
            "error: " not in result.stderr.lower() or "found" in result.stdout.lower()
        ), f"Mypy execution failed: {result.stderr}"


class TestPreCommitHooks:
    """Test suite for pre-commit hooks configuration."""

    def test_precommit_config_exists(self, browser_root: Path) -> None:
        """Verify .pre-commit-config.yaml exists."""
        precommit_config = browser_root / ".pre-commit-config.yaml"
        assert (
            precommit_config.exists()
        ), f".pre-commit-config.yaml not found at {precommit_config}"

    def test_precommit_executable_exists(self, browser_root: Path) -> None:
        """Verify pre-commit is installed."""
        result = subprocess.run(
            [str(browser_root / ".venv" / "bin" / "pre-commit"), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"pre-commit not found: {result.stderr}"
        assert "pre-commit" in result.stdout.lower()

    def test_all_hooks_have_require_serial(self, browser_root: Path) -> None:
        """Verify all hooks in .pre-commit-config.yaml have require_serial: true."""
        precommit_config = browser_root / ".pre-commit-config.yaml"
        content = precommit_config.read_text()

        # Find all hook definitions
        import re

        hook_blocks = re.split(r"^\s*- id:", content, flags=re.MULTILINE)[
            1:
        ]  # Split by hook ID

        for i, hook_block in enumerate(hook_blocks, 1):
            # Extract hook ID
            id_match = re.search(r"^(\S+)", hook_block.strip())
            if not id_match:
                continue
            hook_id = id_match.group(1)

            # Check if require_serial is present
            has_require_serial = (
                "require_serial:" in hook_block or "require_serial: true" in hook_block
            )

            assert has_require_serial, (
                f"Hook '{hook_id}' is missing 'require_serial: true' in .pre-commit-config.yaml. "
                f"All hooks MUST have require_serial to prevent race conditions."
            )

    def test_precommit_hooks_can_be_installed(self, browser_root: Path) -> None:
        """Verify pre-commit hooks can be installed."""
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "pre-commit"),
                "install",
                "--install-hooks",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # May already be installed (exit code 0) or install fresh
        assert (
            result.returncode == 0
        ), f"Failed to install pre-commit hooks: {result.stderr}"


class TestPreCommitHookExecution:
    """Test suite for actual execution of pre-commit hooks."""

    @pytest.mark.slow
    def test_ruff_hook_executes(self, browser_root: Path) -> None:
        """Verify ruff hook can execute via pre-commit."""
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "pre-commit"),
                "run",
                "ruff",
                "--all-files",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # Hook may pass (0) or fail with linting errors
        assert result.returncode in (
            0,
            1,
        ), f"Ruff hook failed to execute: {result.stderr}"

    @pytest.mark.slow
    def test_ruff_format_hook_executes(self, browser_root: Path) -> None:
        """Verify ruff-format hook can execute via pre-commit."""
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "pre-commit"),
                "run",
                "ruff-format",
                "--all-files",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        assert result.returncode in (
            0,
            1,
        ), f"Ruff-format hook failed to execute: {result.stderr}"

    @pytest.mark.slow
    def test_mypy_hook_executes(self, browser_root: Path) -> None:
        """Verify mypy hook can execute via pre-commit."""
        result = subprocess.run(
            [
                str(browser_root / ".venv" / "bin" / "pre-commit"),
                "run",
                "mypy",
                "--all-files",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # Mypy may pass or fail with type errors
        assert result.returncode in (
            0,
            1,
        ), f"Mypy hook failed to execute: {result.stderr}"


class TestHookSerialization:
    """Test that hooks run serially as configured."""

    def test_hooks_run_one_at_a_time(self, browser_root: Path) -> None:
        """Verify that require_serial prevents parallel execution."""
        # This is more of a configuration test - actual concurrency testing
        # would require hooking into pre-commit internals

        precommit_config = browser_root / ".pre-commit-config.yaml"
        content = precommit_config.read_text()

        # Count hooks with require_serial
        import re

        serial_count = len(re.findall(r"require_serial:\s*true", content))

        # Count total hooks (excluding commented-out ones)
        total_hooks = len(re.findall(r"^\s*- id:\s*\w+", content, flags=re.MULTILINE))

        assert serial_count == total_hooks, (
            f"Not all hooks have require_serial: true. "
            f"Found {serial_count} with require_serial out of {total_hooks} total hooks. "
            f"ALL hooks must have require_serial to prevent race conditions."
        )
