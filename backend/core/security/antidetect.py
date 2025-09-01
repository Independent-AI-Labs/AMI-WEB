"""Anti-detection features for ChromeDriver."""

import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger


def _validate_executable_path(executable_path: str) -> bool:
    """Validate that an executable path is safe to use in subprocess calls."""
    if not executable_path:
        return False

    # Ensure the path is absolute and exists
    path_obj = Path(executable_path)
    if not path_obj.is_absolute() or not path_obj.exists():
        return False

    # Check that it's actually executable
    if not path_obj.is_file():
        return False

    # Additional safety: ensure no shell metacharacters in path
    dangerous_chars = ["&", "|", ";", "$", "`", "\\", '"', "'", " ", "\n", "\r", "\t"]
    for char in dangerous_chars:
        if char in executable_path:
            # Allow spaces in paths but validate they're properly handled
            if char == " ":
                continue
            return False

    return True


def _validate_file_path(file_path: str) -> bool:
    """Validate that a file path is safe to use in subprocess calls."""
    if not file_path:
        return False

    # Ensure the path is absolute
    path_obj = Path(file_path)
    if not path_obj.is_absolute():
        return False

    # Check for dangerous characters that could be used for injection
    dangerous_chars = ["&", "|", ";", "$", "`", '"', "'", "\n", "\r", "\t"]
    for char in dangerous_chars:
        if char in file_path:
            return False

    # Ensure the path points to our expected file type
    return file_path.endswith(("chromedriver", "chromedriver.exe")) or "_patched" in file_path


class ChromeDriverPatcher:
    """Patches ChromeDriver binary to avoid detection."""

    def __init__(self, chromedriver_path: str, drivers_dir: Path | None = None):
        self.original_path = Path(chromedriver_path)
        # Create a patched version in a writable location
        # Use the same extension as the original file (or no extension)
        suffix = self.original_path.suffix
        name_without_ext = self.original_path.stem
        patched_name = f"{name_without_ext}_patched{suffix}"

        # Use provided drivers_dir or default to project root/build
        if drivers_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            drivers_dir = project_root / "build"

        drivers_dir.mkdir(exist_ok=True, parents=True)
        self.chromedriver_path = drivers_dir / patched_name
        self.backup_path: Path | None = None

    def is_patched(self) -> bool:
        """Check if the ChromeDriver binary is already patched."""
        try:
            with self.chromedriver_path.open("rb") as f:
                content = f.read()
                # Check if the CDC injection code is present
                return not bool(re.search(rb"\{window\.cdc.*?;\}", content))
        except Exception as e:
            logger.error(f"Error checking if ChromeDriver is patched: {e}")
            return False

    def get_patched_path(self) -> Path:
        """Get the path to the patched ChromeDriver."""
        return self.chromedriver_path

    def _sign_macos_binary(self) -> None:
        """Sign the patched ChromeDriver on macOS to avoid Gatekeeper issues."""
        try:
            # Find full paths for executables to avoid S607 security warning
            xattr_path = shutil.which("xattr")
            codesign_path = shutil.which("codesign")

            if not xattr_path:
                logger.warning("xattr command not found - unable to remove extended attributes")
            else:
                # Remove any existing extended attributes
                # Validate executable and file paths to avoid S603 security warning
                driver_path_str = str(self.chromedriver_path.resolve())

                if not _validate_executable_path(xattr_path):
                    logger.error(f"Invalid or unsafe xattr executable path: {xattr_path}")
                    return

                if not _validate_file_path(driver_path_str):
                    logger.error(f"Invalid or unsafe chromedriver file path: {driver_path_str}")
                    return

                # Use validated paths in subprocess call - S603 suppressed with validation
                subprocess.run(  # noqa: S603
                    [xattr_path, "-cr", driver_path_str],
                    check=False,
                    capture_output=True,
                )

            if not codesign_path:
                logger.warning("codesign command not found - unable to sign patched driver")
            else:
                # Sign with ad-hoc signature
                # Validate executable and file paths to avoid S603 security warning
                driver_path_str = str(self.chromedriver_path.resolve())

                if not _validate_executable_path(codesign_path):
                    logger.error(f"Invalid or unsafe codesign executable path: {codesign_path}")
                    return

                if not _validate_file_path(driver_path_str):
                    logger.error(f"Invalid or unsafe chromedriver file path: {driver_path_str}")
                    return

                # Use validated paths in subprocess call - S603 suppressed with validation
                subprocess.run(  # noqa: S603
                    [codesign_path, "--force", "--deep", "--sign", "-", driver_path_str],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("Patched ChromeDriver signed successfully on macOS")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to sign patched ChromeDriver: {e}")
            logger.warning("The patched driver may be blocked by macOS Gatekeeper")
        except FileNotFoundError:
            logger.warning("codesign command not found - unable to sign patched driver")

    def patch(self) -> bool:
        """
        Patch the ChromeDriver binary to remove detection artifacts.

        This patches the ChromeDriver to remove the window.cdc property
        that websites use to detect automated browsers.
        """
        if self.is_patched():
            logger.info("ChromeDriver is already patched")
            return True

        try:
            # Copy original to create patched version
            if not self.chromedriver_path.exists():
                shutil.copy2(self.original_path, self.chromedriver_path)

            # Read the binary
            with self.chromedriver_path.open("rb") as f:
                content = f.read()

            modified = False

            # ONLY replace the exact CDC variable name - no regex patterns!
            # The specific CDC variable that ChromeDriver uses
            cdc_var = b"cdc_adoQpoasnfa76pfcZLmcfl"
            if cdc_var in content:
                # Replace with same length string to not break offsets
                wdc_var = b"wdc_adoQpoasnfa76pfcZLmcfl"
                content = content.replace(cdc_var, wdc_var)
                modified = True
                logger.debug(f"Replaced CDC variable: {cdc_var!r} -> {wdc_var!r}")

            if modified:
                # Write the patched binary
                with self.chromedriver_path.open("wb") as f:
                    f.write(content)
                logger.info("ChromeDriver patched successfully")

                # On macOS, sign the patched binary to avoid Gatekeeper issues
                if platform.system() == "Darwin":
                    self._sign_macos_binary()

                return True

            logger.warning("No CDC patterns found to patch in ChromeDriver")
            return True  # Still return True as it might be a newer version

        except Exception as e:
            logger.error(f"Error patching ChromeDriver: {e}")
            return False

    def restore(self) -> None:
        """Restore the original ChromeDriver from backup."""
        if self.backup_path and self.backup_path.exists():
            shutil.copy2(self.backup_path, self.chromedriver_path)
            logger.info("ChromeDriver restored from backup")


def get_anti_detection_arguments(user_agent: str | None = None, window_size: tuple[int, int] | None = None) -> list[str]:
    """
    Get Chrome arguments for anti-detection.

    Args:
        user_agent: Optional custom user agent string
        window_size: Optional window size as (width, height) tuple

    Returns a list of Chrome arguments that help avoid detection.
    """
    # Use defaults if not provided
    if user_agent is None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    if window_size is None:
        window_size = (1920, 1080)

    args = [
        # Disable automation features
        "--disable-blink-features=AutomationControlled",
        # Exclude switches that indicate automation
        "--exclude-switches=enable-automation",
        # Disable the automation extension
        "--disable-dev-shm-usage",
        # Set user agent to remove HeadlessChrome
        f"--user-agent={user_agent}",
        # Disable the infobar that says Chrome is being controlled
        "--disable-infobars",
        # Start maximized to look more natural
        "--start-maximized",
        # Disable default browser check
        "--no-default-browser-check",
        # Disable first run experience
        "--no-first-run",
        # Disable password saving prompts
        "--password-store=basic",
        # Disable automation-related features
        "--disable-features=ChromeWhatsNewUI,TranslateUI",
        # Use a more natural window size
        f"--window-size={window_size[0]},{window_size[1]}",
    ]

    args.extend(
        [
            # Set language
            "--lang=en-US,en;q=0.9",
            # Enable WebGL explicitly
            "--enable-webgl",
            "--enable-webgl2",
            # Use hardware acceleration when available
            "--enable-accelerated-2d-canvas",
            "--enable-accelerated-video-decode",
            # Ignore GPU blocklist to ensure WebGL works
            "--ignore-gpu-blocklist",
            # Don't use software renderer - we want real WebGL
            "--disable-software-rasterizer",
            # Use ANGLE (more compatible on Windows)
            "--use-angle=default",
            # Use GL implementation auto-selection
            "--use-gl=angle",
            # Enable GPU rasterization
            "--enable-gpu-rasterization",
            # Ensure GPU process isn't sandboxed (helps with WebGL)
            "--disable-gpu-sandbox",
            # Additional GPU flags for better WebGL support
            "--enable-gpu",
            "--enable-features=VaapiVideoDecoder",
        ],
    )

    return args


def get_anti_detection_prefs() -> dict[str, Any]:
    """
    Get Chrome preferences for anti-detection.

    Returns a dictionary of Chrome preferences that help avoid detection.
    """
    return {
        # Disable webdriver flag
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        # Disable Chrome's Save Password popup
        "profile.default_content_setting_values.notifications": 1,
        # Set download behavior
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        # Disable plugins discovery
        "plugins.always_open_pdf_externally": True,
        # Disable automation features
        "useAutomationExtension": False,
    }


def get_anti_detection_experimental_options() -> dict[str, Any]:
    """
    Get experimental Chrome options for anti-detection.

    Returns a dictionary of experimental options that help avoid detection.
    """
    return {
        # Exclude automation switches
        "excludeSwitches": ["enable-automation", "enable-logging"],
        # Disable automation extension
        "useAutomationExtension": False,
        # Disable developer mode extensions warning
        "prefs": get_anti_detection_prefs(),
    }


def setup_anti_detection_capabilities() -> dict[str, Any]:
    """
    Get Chrome capabilities for anti-detection.

    Returns a dictionary of capabilities that help avoid detection.
    """
    return {
        "browserName": "chrome",
        "version": "",
        "platform": "ANY",
        "goog:chromeOptions": {
            "excludeSwitches": ["enable-automation"],
            "useAutomationExtension": False,
        },
    }


def execute_anti_detection_scripts(driver: Any) -> None:
    """
    Execute JavaScript to further mask automation.

    This should be called after the driver is initialized.
    """
    # Load complete anti-detect script
    # Path: backend/core/security -> web/scripts
    scripts_dir = Path(__file__).parent.parent.parent.parent / "web" / "scripts"
    script_path = scripts_dir / "complete-antidetect.js"

    if not script_path.exists():
        logger.error(f"Complete anti-detect script not found at {script_path}")
        return

    try:
        with script_path.open("r", encoding="utf-8") as f:
            script_content = f.read()

        # Enable Target domain to track all new tabs/windows with better settings
        driver.execute_cdp_cmd(
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,  # Don't wait - causes timing issues
                "flatten": True,
                "filter": [{"type": "page", "exclude": False}],  # Only attach to pages
            },
        )

        # Enable Runtime and Page domains
        driver.execute_cdp_cmd("Runtime.enable", {})
        driver.execute_cdp_cmd("Page.enable", {})

        # Inject script on main page
        # Use runImmediately to run on existing contexts IMMEDIATELY!
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": script_content,
                "runImmediately": True,  # CRITICAL: Run immediately on existing contexts!
            },
        )

        # Also inject into runtime for immediate effect
        try:
            driver.execute_script(script_content)
        except Exception as e:
            # This is expected for about:blank or other special pages
            logger.debug(f"Script injection failed on current page (likely about:blank): {e}")

        logger.debug("Complete anti-detection script injected into main target")

        # Store the script in driver for later use
        driver._antidetect_script = script_content

    except Exception as e:
        logger.warning(f"Failed to inject complete anti-detection script: {e}")
