"""Utility functions for Chrome setup."""

import contextlib
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from loguru import logger

# Colors for output (cross-platform)
if platform.system() == "Windows":
    RED = GREEN = YELLOW = NC = ""
else:
    RED = "\033[1;31m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color


def _invalidate_patched_driver(driver_path: Path) -> None:
    """Remove any stale patched driver so the next launch re-patches a fresh binary."""
    patched_name = f"{driver_path.stem}_patched{driver_path.suffix}"
    patched_path = driver_path.with_name(patched_name)

    if patched_path.exists():
        try:
            patched_path.unlink()
            print_colored(f"Removed stale patched ChromeDriver at {patched_path}", "\033[1;33m")  # YELLOW
        except OSError as exc:
            print_colored(f"Warning: failed to remove {patched_path}: {exc}", "\033[1;33m")  # YELLOW


def _ensure_chromium_permissions(chrome_dir: Path, system: str) -> None:
    """Ensure Chromium runtime binaries have the right permissions."""
    if system == "Windows":
        return

    try:
        if system == "Darwin":
            app_contents = chrome_dir / "Chromium.app" / "Contents"
            helpers_dir = app_contents / "Frameworks" / "Chromium Framework.framework" / "Versions" / "Current" / "Helpers"

            chrome_exe = app_contents / "MacOS" / "Chromium"
            crashpad = helpers_dir / "Chrome Crashpad Handler.app" / "Contents" / "MacOS" / "Chrome Crashpad Handler"
            sandbox = helpers_dir / "chrome_crashpad_handler"
        else:  # Linux and other Unix
            chrome_exe = chrome_dir / "chrome"
            crashpad = chrome_dir / "chrome_crashpad_handler"
            sandbox = chrome_dir / "chrome_sandbox"

        for binary in (chrome_exe, crashpad, sandbox):
            if binary and binary.exists():
                try:
                    binary.chmod(0o755)
                except OSError as exc:
                    print_colored(
                        f"Warning: failed to set executable bit on {binary.name}: {exc}",
                        "\033[1;33m",  # YELLOW
                    )
    except OSError as e:
        print_colored(f"Warning: failed to adjust Chromium binary permissions: {e}", "\033[1;33m")  # YELLOW


def _find_chrome_executable(chrome_dir: Path, system: str) -> Path:
    """Find the Chrome executable path based on the system."""
    if system == "Windows":
        return chrome_dir / "chrome.exe"
    if system == "Darwin":
        return chrome_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    return chrome_dir / "chrome"


def remove_quarantine_macos(chrome_dir: Path) -> None:
    """Remove quarantine on macOS."""
    system = platform.system()
    if system == "Darwin":
        with contextlib.suppress(Exception):
            subprocess.run(["xattr", "-cr", str(chrome_dir)], capture_output=True, check=False)


def remove_quarantine_chromedriver(driver_path: Path) -> None:
    """Remove quarantine on ChromeDriver for macOS."""
    system = platform.system()
    if system == "Darwin":
        with contextlib.suppress(Exception):
            subprocess.run(["xattr", "-cr", str(driver_path)], capture_output=True, check=False)


def get_platform_info() -> tuple[str, str]:
    """Get platform info in format used by chrome-for-testing API."""
    system = platform.system().lower()
    if system == "linux":
        return "linux", "x64"
    if system == "darwin":
        return "mac", "arm64" if platform.machine().lower() == "arm64" else "x64"
    if system == "windows":
        return "win", "x64"
    raise ValueError(f"Unsupported system: {system}")


def _validate_google_url(url: str) -> bool:
    """Validate that URL is from trusted Google domains."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and parsed.netloc in ("dl.google.com", "chromedriver.storage.googleapis.com", "edgedl.me.gvt1.com")


def print_colored(message: str, color: str = "") -> None:
    """Print colored message."""
    # Determine the color to use based on platform
    nc = "" if platform.system() == "Windows" else "\033[0m"  # No Color

    logger.info(f"{color}{message}{nc}")
