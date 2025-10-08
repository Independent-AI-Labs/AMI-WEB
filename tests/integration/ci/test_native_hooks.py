"""Integration tests for native git hooks infrastructure.

These tests validate that native git hooks (ruff, mypy, tests)
are configured correctly and execute as expected.
"""

import subprocess
from pathlib import Path

import pytest
from base.scripts.env.paths import find_module_root


@pytest.fixture
def browser_root() -> Path:
    """Get the browser module root directory."""
    return find_module_root(Path(__file__))


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
        assert "ruff" in result.stdout.lower(), f"Unexpected ruff version output: {result.stdout}"

    def test_ruff_check_runs_successfully(self, browser_root: Path) -> None:
        """Verify Ruff can run check on the module."""
        result = subprocess.run(
            [str(browser_root / ".venv" / "bin" / "ruff"), "check", str(browser_root), "--config", str(browser_root / "pyproject.toml")],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # Should either pass (0) or find fixable issues (1)
        assert result.returncode in (0, 1), f"Ruff check failed unexpectedly: {result.stderr}"

    def test_ruff_format_check_runs_successfully(self, browser_root: Path) -> None:
        """Verify Ruff format checker runs."""
        result = subprocess.run(
            [str(browser_root / ".venv" / "bin" / "ruff"), "format", "--check", str(browser_root)],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(browser_root),
        )
        # Should either pass (0) or find formatting issues (1)
        assert result.returncode in (0, 1), f"Ruff format check failed unexpectedly: {result.stderr}"


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
        assert "mypy" in result.stdout.lower(), f"Unexpected mypy version output: {result.stdout}"

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
        assert "error: " not in result.stderr.lower() or "found" in result.stdout.lower(), f"Mypy execution failed: {result.stderr}"


class TestNativeGitHooks:
    """Test suite for native git hooks."""

    def test_native_precommit_hook_exists(self, browser_root: Path, repo_root: Path) -> None:
        """Verify native pre-commit hook source exists in /base/scripts/hooks/."""
        hook_source = repo_root / "base" / "scripts" / "hooks" / "pre-commit"
        assert hook_source.exists(), f"Native pre-commit hook source not found at {hook_source}"
        assert hook_source.stat().st_mode & 0o111, "Hook source script is not executable"

    def test_native_prepush_hook_exists(self, browser_root: Path, repo_root: Path) -> None:
        """Verify native pre-push hook source exists in /base/scripts/hooks/."""
        hook_source = repo_root / "base" / "scripts" / "hooks" / "pre-push"
        assert hook_source.exists(), f"Native pre-push hook source not found at {hook_source}"
        assert hook_source.stat().st_mode & 0o111, "Hook source script is not executable"

    def test_git_hooks_installed(self, browser_root: Path, repo_root: Path) -> None:
        """Verify hooks are installed in git hooks directory."""
        # For submodules, hooks are in .git/modules/<name>/hooks
        if (browser_root / ".git").is_file():
            git_content = (browser_root / ".git").read_text().strip()
            if git_content.startswith("gitdir: "):
                git_dir = git_content[8:]
                git_hooks_dir = browser_root / git_dir / "hooks" if git_dir.startswith("../") else Path(git_dir) / "hooks"
            else:
                pytest.skip("Invalid .git file format")
        else:
            git_hooks_dir = browser_root / ".git" / "hooks"

        pre_commit_hook = git_hooks_dir / "pre-commit"
        pre_push_hook = git_hooks_dir / "pre-push"

        assert pre_commit_hook.exists(), f"pre-commit hook not installed at {pre_commit_hook}"
        assert pre_push_hook.exists(), f"pre-push hook not installed at {pre_push_hook}"
        assert pre_commit_hook.stat().st_mode & 0o111, "pre-commit hook is not executable"
        assert pre_push_hook.stat().st_mode & 0o111, "pre-push hook is not executable"


# Native hooks are tested by actual usage during commits/pushes
# Individual tool tests are in their respective test classes above


class TestHookSerialization:
    """Test that native hooks run serially."""

    def test_native_hooks_run_serially(self, browser_root: Path, repo_root: Path) -> None:
        """Verify native hooks execute all checks serially."""
        # Native hooks run all checks in a single bash script
        # This is inherently serial - bash executes commands sequentially
        hook_source = repo_root / "base" / "scripts" / "hooks" / "pre-commit"
        content = hook_source.read_text()

        # Verify hook uses set -euo pipefail for safety
        assert "set -euo pipefail" in content, "Hook must use 'set -euo pipefail' for safety"

        # Verify hook exits on first failure (no parallel execution)
        assert "exit 1" in content, "Hook must exit on failures"
