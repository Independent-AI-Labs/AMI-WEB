"""Chrome-specific setup functionality."""

import json
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import urlparse
from urllib.request import urlopen, urlretrieve
import zipfile

from browser.scripts.setup.utils import GREEN, YELLOW, _validate_google_url, get_platform_info, print_colored


def get_latest_chromium_revision() -> str:
    """Get the latest Chromium revision for the current platform."""
    system, arch = get_platform_info()

    # Get latest revision using the testing interface
    latest_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    print_colored(f"Fetching latest revision info from: {latest_url}", GREEN)

    try:
        # Validate the URL before opening
        parsed = urlparse(latest_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        if parsed.netloc != "googlechromelabs.github.io":
            raise ValueError(f"Invalid domain: {parsed.netloc}")

        response = urlopen(latest_url, timeout=30)
        data = json.loads(response.read().decode("utf-8"))
        revision = data["channels"]["Stable"]["version"]

        # Ensure revision is a string
        if not isinstance(revision, str):
            raise TypeError(f"Expected string for revision, got {type(revision)}")

        # For testing endpoint, we need to derive the revision from the version
        # This is approximate - in real use, you'd call the testing API to get exact revision
        print_colored(f"Latest stable revision: {revision}", GREEN)
        return revision
    except Exception as e:
        raise RuntimeError(f"Failed to get latest Chromium revision: {e}") from e


def _ensure_chromium_permissions(chrome_dir: Path, system: str) -> None:
    """Ensure proper permissions for Chromium executable."""
    chrome_exe = _find_chrome_executable(chrome_dir, system)
    if chrome_exe.exists():
        # Make executable
        current_mode = chrome_exe.stat().st_mode
        chrome_exe.chmod(current_mode | stat.S_IEXEC)
        print_colored(f"Set executable permissions for {chrome_exe}", GREEN)


def download_chromium(revision: str) -> Path:
    """Download Chromium for the current platform."""
    system, arch = get_platform_info()

    # Map platform to Chromium build
    platform_map = {
        "linux-x64": "linux64",
        "linux-arm64": "linux64",  # Use x64 build for now, ARM64 support varies
        "darwin-x64": "mac-x64",
        "darwin-arm64": "mac-arm64",
        "windows-x64": "win64",
    }

    platform_key = f"{system}-{arch}"
    if platform_key not in platform_map:
        raise ValueError(f"Unsupported platform: {platform_key}")

    build_name = platform_map[platform_key]

    # Download from chrome-for-testing
    chrome_url = f"https://storage.googleapis.com/chrome-for-testing-public/{revision}/{build_name}/chrome-{build_name}.zip"
    print_colored(f"Downloading Chromium from: {chrome_url}", GREEN)

    # Validate URL
    _validate_google_url(chrome_url)

    # Create downloads directory
    download_dir = Path.home() / ".local" / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    # Download with progress
    chrome_zip = download_dir / f"chrome-{build_name}-{revision}.zip"

    try:
        print_colored("Downloading...", YELLOW)
        urlretrieve(chrome_url, str(chrome_zip))
        print_colored(f"Downloaded to: {chrome_zip}", GREEN)
    except Exception as e:
        raise RuntimeError(f"Failed to download Chromium: {e}") from e

    # Extract to install location
    install_dir = Path.home() / ".local" / "chrome"
    install_dir.mkdir(parents=True, exist_ok=True)

    print_colored(f"Extracting to: {install_dir}", YELLOW)
    with zipfile.ZipFile(chrome_zip, "r") as zip_ref:
        zip_ref.extractall(str(install_dir))

    # Clean up zip file
    chrome_zip.unlink()

    # Set permissions
    _ensure_chromium_permissions(install_dir, system)

    print_colored(f"Chromium installed to: {install_dir}", GREEN)
    return install_dir


def _find_chrome_executable(chrome_dir: Path, system: str) -> Path:
    """Find the Chrome executable in the given directory."""
    if system == "linux":
        return chrome_dir / "chrome-linux64" / "chrome"
    if system == "darwin":
        return chrome_dir / "chrome-mac-arm64" / "Chrome.app" / "Contents" / "MacOS" / "Chrome"
    if system == "windows":
        return chrome_dir / "chrome-win64" / "chrome.exe"
    raise ValueError(f"Unsupported system: {system}")


def _version_from_binary(chrome_exe: Path) -> str | None:
    """Extract version from Chrome binary."""

    if not chrome_exe.exists():
        return None

    try:
        # Validate that this is a safe, local file path
        if not chrome_exe.exists():
            raise FileNotFoundError(f"Chrome executable does not exist: {chrome_exe}")

        # Sanitize the executable path to ensure it's a local path
        safe_path = str(chrome_exe.resolve())
        if ".." in safe_path or safe_path.startswith("/") and not safe_path.startswith(str(Path.home())):
            raise ValueError(f"Unsafe path detected: {chrome_exe}")

        result = subprocess.run([safe_path, "--version"], check=False, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extract version from output
            output = result.stdout.strip()
            # Look for version pattern after "Chrome" or "Chromium"
            match = re.search(r"(?:Chrome|Chromium)[/\s]+([0-9.]+)", output)
            if match:
                return match.group(1)
    except Exception as e:
        print_colored(f"Failed to get version from binary {chrome_exe}: {e}", YELLOW)

    return None


def _version_from_revision(revision: str | None) -> str | None:
    """Get version from revision if available."""
    if not revision:
        return None

    try:
        # Try to get version info from revision
        url = f"https://chromiumdash.appspot.com/fetch_releases_with_changes?start={revision}&rows=1"

        # Validate URL before opening
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        if parsed.netloc != "chromiumdash.appspot.com":
            raise ValueError(f"Invalid domain: {parsed.netloc}")

        response = urlopen(url, timeout=30)
        data = json.loads(response.read().decode("utf-8"))

        if data and len(data) > 0:
            version = data[0].get("version")
            return str(version) if version else None
    except Exception as e:
        # Log the exception but continue gracefully
        print_colored(f"Warning: Failed to get version from revision {revision}: {e}", YELLOW)
        # Silently fail, revision-based lookup is best effort

    return None


def get_chrome_version(chrome_dir: Path, revision: str | None = None) -> str:
    """Get Chrome version from installation or revision."""

    # First, try to extract from actual binary
    system, _ = get_platform_info()
    chrome_exe = _find_chrome_executable(chrome_dir, system)
    version = _version_from_binary(chrome_exe)

    if version:
        return version

    # Alternative to revision-based version
    if revision:
        revision_version = _version_from_revision(revision)
        if revision_version:
            return revision_version

    # Default value
    return "unknown"
