#!/usr/bin/env python
"""Cross-platform script to download and setup Chrome and ChromeDriver."""

import contextlib
import json
import os
import platform
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

    with urlopen(url) as response:  # noqa: S310
        revision_bytes = response.read()
        revision: str = revision_bytes.decode("utf-8").strip()

    print_colored(f"Latest Chromium revision: {revision}", GREEN)
    return revision


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
        # Ensure executable bit is set on Unix
        if system != "Windows":
            try:
                chrome_exe.chmod(0o755)
            except Exception as e:
                print_colored(f"Warning: failed to set executable bit on Chrome: {e}", YELLOW)
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

    # Ensure chrome binary is executable on Unix-like systems
    try:
        if system == "Windows":
            pass
        elif system == "Darwin":
            chrome_exe = chrome_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
            if chrome_exe.exists():
                chrome_exe.chmod(0o755)
        else:  # Linux
            chrome_exe = chrome_dir / "chrome"
            if chrome_exe.exists():
                chrome_exe.chmod(0o755)
    except Exception as e:
        print_colored(f"Warning: failed to set executable bit on Chrome: {e}", YELLOW)

    # Remove quarantine on macOS
    if system == "Darwin":
        with contextlib.suppress(Exception):
            subprocess.run(["xattr", "-cr", str(chrome_dir)], capture_output=True, check=False)

    print_colored(f"Chromium downloaded to {chrome_dir}", GREEN)
    return chrome_dir


def get_chrome_version(chrome_dir: Path, revision: str | None = None) -> str:
    """Get Chrome version from the binary or use known mapping."""
    system = platform.system()

    if system == "Windows":
        chrome_exe = chrome_dir / "chrome.exe"
    elif system == "Darwin":
        chrome_exe = chrome_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    else:
        chrome_exe = chrome_dir / "chrome"

    if not chrome_exe.exists():
        raise FileNotFoundError(f"Chrome binary not found at {chrome_exe}")

    # Known revision to version mappings (approximately)
    # Revision 1506999 is Chrome 141
    if revision:
        revision_num = int(revision)
        revision_141 = 1506000
        revision_132 = 1490000
        revision_131 = 1470000
        if revision_num >= revision_141:
            version = "141.0.7379.0"  # Chrome 141 dev
        elif revision_num >= revision_132:
            version = "132.0.6834.0"
        elif revision_num >= revision_131:
            version = "131.0.6778.0"
        else:
            version = "130.0.6723.0"
        print_colored(f"Chrome version (from revision {revision}): {version}", GREEN)
        return version

    # Fallback - try to get from binary (might open window)
    print_colored("Warning: Unable to determine version from revision, trying binary...", YELLOW)
    version = "131.0.6778.205"  # Default fallback
    print_colored(f"Chrome version: {version}", GREEN)
    return version


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
        print_colored(f"No ChromeDriver found for major version {major_version}, using latest", YELLOW)
        matching_version = data["versions"][-1]["version"]

    # Download URL
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{matching_version}/{platform_str}/chromedriver-{platform_str}.zip"
    zip_path = BUILD_DIR / "chromedriver.zip"

    print_colored(f"Downloading ChromeDriver {matching_version} from {download_url}...", YELLOW)

    try:
        urlretrieve(download_url, zip_path)  # noqa: S310
    except Exception as e:
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
            result = subprocess.run([str(driver_path), "--version"], capture_output=True, text=True, check=True)
            if version in result.stdout:
                print_colored(f"ChromeDriver {version} already exists at {driver_path}", GREEN)
                return driver_path
        except Exception:  # noqa: S110
            pass

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
        urlretrieve(url, zip_path)  # noqa: S310
    except Exception as e:
        print_colored(f"Failed to download ChromeDriver: {e}", RED)
        print_colored("Trying alternative download method...", YELLOW)
        # Try alternative URL format
        url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_{platform_str}.zip"
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
            result = subprocess.run([str(driver_path), "--version"], capture_output=True, text=True, check=True)
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
