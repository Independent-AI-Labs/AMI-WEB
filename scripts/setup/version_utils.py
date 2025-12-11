"""Version handling functions for Chrome setup."""

from pathlib import Path
import platform
import re

from base.backend.workers.file_subprocess import FileSubprocessSync
from browser.scripts.setup.utils import _find_chrome_executable, print_colored


# Revision thresholds used when the binary cannot reveal its version.
REVISION_VERSION_HEURISTICS: list[tuple[int, str]] = [
    (1518000, "142.0.0.0"),
    (1506000, "141.0.7379.0"),
    (1490000, "132.0.6834.0"),
    (1470000, "131.0.6778.0"),
    (0, "130.0.6723.0"),
]


def _version_from_binary(chrome_exe: Path) -> str | None:
    """Get the version from the Chrome binary."""
    # Validate the chrome_exe path before using it
    safe_path = chrome_exe.resolve().absolute()

    # Security check: ensure the path is within expected directories and doesn't contain unsafe elements
    expected_base = chrome_exe.parent  # This should be the build directory
    if ".." in str(safe_path) or not str(safe_path).startswith(str(expected_base)):
        raise ValueError(f"Unsafe path detected: {chrome_exe}")

    # Additional validation to ensure this is a legitimate Chrome executable
    if safe_path.name.lower().replace(".exe", "") not in ["chrome", "chromium", "google-chrome"]:
        raise ValueError(f"Not a Chrome executable: {safe_path}")

    # Final validation - ensure the executable path is safe to run
    final_safe_path = safe_path.resolve().absolute()
    if not final_safe_path.exists():
        raise FileNotFoundError(f"Chrome executable does not exist: {final_safe_path}")

    # Confirm this is a safe executable by checking it contains expected chrome text
    if not any(keyword in str(final_safe_path).lower() for keyword in ["chrome", "chromium"]):
        raise ValueError(f"Not a Chrome executable: {final_safe_path}")

    # Security: validate that this is a real executable file
    if not final_safe_path.is_file():
        raise ValueError(f"Path is not a file: {final_safe_path}")

    # Execute with FileSubprocessSync for secure subprocess execution
    # This is safe because we've validated that final_safe_path is a legitimate Chrome executable
    try:
        executor = FileSubprocessSync(work_dir=final_safe_path.parent)
        result = executor.run(
            [str(final_safe_path), "--version"],
            timeout=30,  # Add timeout for security
        )

        if not result["success"]:
            print_colored(
                f"Warning: Failed to query Chrome binary for version (exit code: {result['returncode']}); using revision heuristic instead",
                "\033[1;33m",  # YELLOW
            )
            return None
    except Exception as exc:
        print_colored(
            f"Warning: Failed to query Chrome binary for version ({exc}); using revision heuristic instead",
            "\033[1;33m",  # YELLOW
        )
        return None

    output = (result["stdout"] or result["stderr"] or "").strip()
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output)
    if match:
        return match.group(1)

    print_colored(
        f"Warning: Unexpected --version output '{output}', will fall back to revision heuristic",
        "\033[1;33m",  # YELLOW
    )
    return None


def _version_from_revision(revision: str | None) -> str | None:
    """Get the version from the revision number."""
    if not revision:
        return None

    try:
        revision_num = int(revision)
    except ValueError:
        return None

    for threshold, version in REVISION_VERSION_HEURISTICS:
        if revision_num >= threshold:
            return version
    return None


def get_chrome_version(chrome_dir: Path, revision: str | None = None) -> str:
    """Resolve the installed Chromium build version."""

    system = platform.system()
    chrome_exe = _find_chrome_executable(chrome_dir, system)

    if not chrome_exe.exists():
        raise FileNotFoundError(f"Chrome binary not found at {chrome_exe}")

    version = _version_from_binary(chrome_exe)
    if version:
        print_colored(f"Chrome version (from binary): {version}", "\033[0;32m")  # GREEN
        return version

    version = _version_from_revision(revision)
    if version:
        print_colored(f"Chrome version (from revision heuristic {revision}): {version}", "\033[0;32m")  # GREEN
        return version

    raise RuntimeError("Unable to determine Chrome version from binary or revision")
