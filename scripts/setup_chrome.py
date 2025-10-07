#!/usr/bin/env python
"""Cross-platform script to download and setup Chrome and ChromeDriver."""

import contextlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen, urlretrieve

from loguru import logger

# Script directory
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BUILD_DIR = PROJECT_ROOT / "build"

# Revision thresholds used when the binary cannot reveal its version.
REVISION_VERSION_HEURISTICS: list[tuple[int, str]] = [
    (1518000, "142.0.0.0"),
    (1506000, "141.0.7379.0"),
    (1490000, "132.0.6834.0"),
    (1470000, "131.0.6778.0"),
    (0, "130.0.6723.0"),
]

# Colors for output (cross-platform)
if platform.system() == "Windows":
    RED = GREEN = YELLOW = NC = ""
else:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color


def print_colored(message: str, color: str = "") -> None:
    """Print colored message."""
    logger.info(f"{color}{message}{NC}")


def _validate_google_url(url: str) -> None:
    """Validate that URL is from trusted Google domains."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    allowed_hosts = {
        "www.googleapis.com",
        "storage.googleapis.com",
        "googlechromelabs.github.io",
        "edgedl.me.gvt1.com",
        "chromedriver.storage.googleapis.com",
    }

    if parsed.hostname not in allowed_hosts:
        msg = f"Untrusted download URL: {url}"
        raise ValueError(msg)


def _invalidate_patched_driver(driver_path: Path) -> None:
    """Remove any stale patched driver so the next launch re-patches a fresh binary."""
    patched_name = f"{driver_path.stem}_patched{driver_path.suffix}"
    patched_path = driver_path.with_name(patched_name)

    if patched_path.exists():
        try:
            patched_path.unlink()
            print_colored(f"Removed stale patched ChromeDriver at {patched_path}", YELLOW)
        except OSError as exc:
            print_colored(f"Warning: failed to remove {patched_path}: {exc}", YELLOW)


def get_platform_info() -> tuple[str, str]:
    """Get platform and architecture information for Chromium snapshots and drivers.

    Returns a tuple of (snapshot_platform, arch_label)
    where snapshot_platform matches the Google Chromium snapshot folder naming.
    """
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        is_64 = ("64" in machine) or ("amd64" in machine) or ("x86_64" in machine)
        plat = "Win_x64" if is_64 else "Win"
        arch = "x64" if is_64 else "x32"
    elif system == "Darwin":
        is_arm = machine in {"arm64", "aarch64"}
        plat = "Mac_Arm" if is_arm else "Mac"
        arch = "arm64" if is_arm else "x64"
    elif system == "Linux":
        is_64 = ("64" in machine) or ("x86_64" in machine)
        plat = "Linux_x64" if is_64 else "Linux"
        arch = "x64" if is_64 else "x32"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    return plat, arch


def get_latest_chromium_revision() -> str:
    """Get the latest Chromium revision from Google API."""
    plat, _ = get_platform_info()

    # Get latest revision
    url = f"https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/{plat}%2FLAST_CHANGE?alt=media"
    print_colored(f"Fetching latest Chromium revision from {url}...", YELLOW)

    _validate_google_url(url)
    with urlopen(url) as response:  # noqa: S310
        revision_bytes = response.read()
        revision: str = revision_bytes.decode("utf-8").strip()

    print_colored(f"Latest Chromium revision: {revision}", GREEN)
    return revision


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
                        YELLOW,
                    )
    except OSError as e:
        print_colored(f"Warning: failed to adjust Chromium binary permissions: {e}", YELLOW)


def download_chromium(revision: str) -> Path:  # noqa: C901
    """Download Chromium for the current platform."""
    plat, _ = get_platform_info()
    system = platform.system()

    # Create build directory
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Determine download URL and filename
    if system == "Windows":
        filename = "chrome-win.zip"
        chrome_dir = BUILD_DIR / "chromium-win"
    elif system == "Darwin":
        filename = "chrome-mac.zip"
        chrome_dir = BUILD_DIR / "chromium-mac"
    elif system == "Linux":
        filename = "chrome-linux.zip"
        chrome_dir = BUILD_DIR / "chromium-linux"

    # Check if already downloaded
    chrome_exe = chrome_dir / ("chrome.exe" if system == "Windows" else "chrome")
    if system == "Darwin":
        chrome_exe = chrome_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"

    if chrome_exe.exists():
        _ensure_chromium_permissions(chrome_dir, system)
        print_colored(f"Chrome already exists at {chrome_dir}", GREEN)
        return chrome_dir

    # Download URL
    url = f"https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/{plat}%2F{revision}%2F{filename}?alt=media"
    zip_path = BUILD_DIR / filename

    print_colored(f"Downloading Chromium from {url}...", YELLOW)
    print_colored("This may take a few minutes...", YELLOW)

    # Download with progress
    def download_with_progress(url: str, dest: Path) -> None:
        """Download file with progress indicator."""
        _validate_google_url(url)
        response = urlopen(url)  # noqa: S310
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        block_size = 8192

        with dest.open("wb") as f:
            while True:
                block = response.read(block_size)
                if not block:
                    break
                f.write(block)
                downloaded += len(block)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    logger.info(f"\rDownloading: {percent:.1f}% ({downloaded}/{total_size} bytes)")
        logger.info("")  # New line after download

    download_with_progress(url, zip_path)

    print_colored("Extracting Chromium...", YELLOW)

    # Extract archive
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(BUILD_DIR)

    # Rename extracted folder if needed
    extracted_name = filename.replace(".zip", "")
    extracted_path = BUILD_DIR / extracted_name
    if extracted_path.exists() and extracted_path != chrome_dir:
        if chrome_dir.exists():
            shutil.rmtree(chrome_dir)
        extracted_path.rename(chrome_dir)

    # Clean up zip file
    zip_path.unlink()

    _ensure_chromium_permissions(chrome_dir, system)

    # Remove quarantine on macOS
    if system == "Darwin":
        with contextlib.suppress(Exception):
            subprocess.run(["xattr", "-cr", str(chrome_dir)], capture_output=True, check=False)

    print_colored(f"Chromium downloaded to {chrome_dir}", GREEN)
    return chrome_dir


def _find_chrome_executable(chrome_dir: Path, system: str) -> Path:
    if system == "Windows":
        return chrome_dir / "chrome.exe"
    if system == "Darwin":
        return chrome_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    return chrome_dir / "chrome"


def _version_from_binary(chrome_exe: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(chrome_exe), "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print_colored(
            f"Warning: Failed to query Chrome binary for version ({exc}); falling back to revision heuristic",
            YELLOW,
        )
        return None

    output = (result.stdout or result.stderr or "").strip()
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output)
    if match:
        return match.group(1)

    print_colored(
        f"Warning: Unexpected --version output '{output}', will fall back to revision heuristic",
        YELLOW,
    )
    return None


def _version_from_revision(revision: str | None) -> str | None:
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
        print_colored(f"Chrome version (from binary): {version}", GREEN)
        return version

    version = _version_from_revision(revision)
    if version:
        print_colored(f"Chrome version (from revision heuristic {revision}): {version}", GREEN)
        return version

    raise RuntimeError("Unable to determine Chrome version from binary or revision")


def download_chromedriver_from_testing(major_version: str) -> Path:  # noqa: C901
    """Download ChromeDriver from Chrome for Testing matching the major version."""
    system = platform.system()
    _, arch = get_platform_info()

    # ChromeDriver path
    if system == "Windows":
        driver_name = "chromedriver.exe"
        platform_str = "win64"  # Always use 64-bit for Windows
    elif system == "Darwin":
        driver_name = "chromedriver"
        platform_str = f"mac-{arch}"
    else:
        driver_name = "chromedriver"
        platform_str = f"linux{arch.replace('x', '')}"

    driver_path = BUILD_DIR / driver_name

    # Get the latest version for this major version
    print_colored(f"Finding latest ChromeDriver for major version {major_version}...", YELLOW)

    # Get available versions from Chrome for Testing
    url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
    _validate_google_url(url)
    with urlopen(url) as response:  # noqa: S310
        data = json.loads(response.read().decode("utf-8"))

    # Find the latest version matching our major version
    matching_version = None
    for version_info in reversed(data["versions"]):  # Start from newest
        version = version_info["version"]
        if version.startswith(f"{major_version}."):
            matching_version = version
            print_colored(f"Found ChromeDriver version: {matching_version}", GREEN)
            break

    if not matching_version:
        print_colored(
            f"No ChromeDriver found for major version {major_version}, using latest",
            YELLOW,
        )
        matching_version = data["versions"][-1]["version"]

    # Download URL
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{matching_version}/{platform_str}/chromedriver-{platform_str}.zip"
    zip_path = BUILD_DIR / "chromedriver.zip"

    print_colored(f"Downloading ChromeDriver {matching_version} from {download_url}...", YELLOW)

    try:
        _validate_google_url(download_url)
        urlretrieve(download_url, zip_path)  # noqa: S310
    except (OSError, ValueError) as e:
        print_colored(f"Failed to download ChromeDriver: {e}", RED)
        raise

    print_colored("Extracting ChromeDriver...", YELLOW)

    # Extract to temp directory first
    temp_dir = BUILD_DIR / "temp_chromedriver"
    temp_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find chromedriver in extracted files
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.startswith("chromedriver"):
                src = Path(root) / file
                if driver_path.exists():
                    driver_path.unlink()
                src.rename(driver_path)
                break

    # Clean up
    shutil.rmtree(temp_dir)
    zip_path.unlink()

    # Make executable on Unix
    if system != "Windows":
        driver_path.chmod(0o755)

    # Remove quarantine on macOS
    if system == "Darwin":
        with contextlib.suppress(Exception):
            subprocess.run(["xattr", "-cr", str(driver_path)], capture_output=True, check=False)

    print_colored(f"ChromeDriver downloaded to {driver_path}", GREEN)
    _invalidate_patched_driver(driver_path)
    return driver_path


def download_chromedriver(version: str) -> Path:  # noqa: C901
    """Download ChromeDriver matching the Chrome version."""
    system = platform.system()
    _, arch = get_platform_info()

    # ChromeDriver path
    driver_name = "chromedriver.exe" if system == "Windows" else "chromedriver"

    driver_path = BUILD_DIR / driver_name

    # Check if already exists and matches version
    if driver_path.exists():
        try:
            result = subprocess.run(
                [str(driver_path), "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            if version in result.stdout:
                print_colored(f"ChromeDriver {version} already exists at {driver_path}", GREEN)
                return driver_path
        except Exception:
            ...

    print_colored(f"Downloading ChromeDriver {version}...", YELLOW)

    # Determine platform string for ChromeDriver
    if system == "Windows":
        platform_str = f"win{arch.replace('x', '')}"
    elif system == "Darwin":
        platform_str = f"mac-{arch}"
    else:
        platform_str = f"linux{arch.replace('x', '')}"

    # Download URL
    url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/{platform_str}/chromedriver-{platform_str}.zip"
    zip_path = BUILD_DIR / "chromedriver.zip"

    print_colored(f"Downloading from {url}...", YELLOW)

    try:
        _validate_google_url(url)
        urlretrieve(url, zip_path)  # noqa: S310
    except (OSError, ValueError) as e:
        print_colored(f"Failed to download ChromeDriver: {e}", RED)
        print_colored("Trying alternative download method...", YELLOW)
        # Try alternative URL format
        url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_{platform_str}.zip"
        _validate_google_url(url)
        urlretrieve(url, zip_path)  # noqa: S310

    print_colored("Extracting ChromeDriver...", YELLOW)

    # Extract to temp directory first
    temp_dir = BUILD_DIR / "temp_chromedriver"
    temp_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find chromedriver in extracted files
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.startswith("chromedriver"):
                src = Path(root) / file
                src.rename(driver_path)
                break

    # Clean up
    shutil.rmtree(temp_dir)
    zip_path.unlink()

    # Make executable on Unix
    if system != "Windows":
        driver_path.chmod(0o755)

    # Remove quarantine on macOS
    if system == "Darwin":
        with contextlib.suppress(Exception):
            subprocess.run(["xattr", "-cr", str(driver_path)], capture_output=True, check=False)

    print_colored(f"ChromeDriver downloaded to {driver_path}", GREEN)
    _invalidate_patched_driver(driver_path)
    return driver_path


def update_config(chrome_dir: Path, driver_path: Path) -> None:
    """Update config.yaml and config.test.yaml with Chrome paths."""
    system = platform.system()

    # Determine Chrome executable path
    if system == "Windows":
        chrome_exe = chrome_dir / "chrome.exe"
    elif system == "Darwin":
        chrome_exe = chrome_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    else:
        chrome_exe = chrome_dir / "chrome"

    # Make paths relative to project root
    chrome_rel = os.path.relpath(chrome_exe, PROJECT_ROOT).replace("\\", "/")
    driver_rel = os.path.relpath(driver_path, PROJECT_ROOT).replace("\\", "/")

    # Update config files
    for config_name in ["config.yaml", "config.test.yaml"]:
        config_file = PROJECT_ROOT / config_name

        if not config_file.exists():
            continue

        print_colored(f"Updating {config_name}...", YELLOW)

        # Read config
        with config_file.open() as f:
            lines = f.readlines()

        # Update lines
        updated = False
        for i, line in enumerate(lines):
            if "chrome_binary_path:" in line:
                lines[i] = f'    chrome_binary_path: "./{chrome_rel}"\n'
                updated = True
            elif "chromedriver_path:" in line:
                lines[i] = f'    chromedriver_path: "./{driver_rel}"\n'
                updated = True

        # Write back
        if updated:
            with config_file.open("w") as f:
                f.writelines(lines)
            print_colored(f"Updated {config_name}", GREEN)


def verify_installation(chrome_dir: Path, driver_path: Path) -> None:
    """Verify Chrome and ChromeDriver installation."""
    system = platform.system()

    print_colored("\nVerification:", GREEN)

    # Check Chrome
    if system == "Windows":
        chrome_exe = chrome_dir / "chrome.exe"
    elif system == "Darwin":
        chrome_exe = chrome_dir / "Chromium.app"
    else:
        chrome_exe = chrome_dir / "chrome"

    if chrome_exe.exists():
        print_colored(f"[OK] Chrome installed at {chrome_exe}", GREEN)
    else:
        print_colored(f"[ERROR] Chrome not found at {chrome_exe}", RED)

    # Check ChromeDriver
    if driver_path.exists():
        try:
            result = subprocess.run(
                [str(driver_path), "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version = result.stdout.strip()
            print_colored(f"[OK] ChromeDriver installed: {version}", GREEN)
        except Exception as e:
            print_colored(f"[ERROR] ChromeDriver error: {e}", RED)
    else:
        print_colored(f"[ERROR] ChromeDriver not found at {driver_path}", RED)


def main() -> None:
    """Main function."""
    print_colored("Chrome and ChromeDriver Setup", GREEN)
    print_colored(f"Platform: {platform.system()} {platform.machine()}", YELLOW)
    print_colored(f"Project root: {PROJECT_ROOT}", YELLOW)
    print_colored(f"Build directory: {BUILD_DIR}\n", YELLOW)

    try:
        # Get latest Chromium revision
        revision = get_latest_chromium_revision()

        # Download Chromium
        chrome_dir = download_chromium(revision)

        # Get Chrome version
        version = get_chrome_version(chrome_dir, revision)

        # Extract major version
        major_version = version.split(".")[0]

        # Download ChromeDriver from Chrome for Testing (has win64 binaries)
        driver_path = download_chromedriver_from_testing(major_version)

        # Update config files
        update_config(chrome_dir, driver_path)

        # Verify installation
        verify_installation(chrome_dir, driver_path)

        print_colored("\nSetup complete!", GREEN)

    except Exception as e:
        print_colored(f"\nError: {e}", RED)
        sys.exit(1)


if __name__ == "__main__":
    main()
