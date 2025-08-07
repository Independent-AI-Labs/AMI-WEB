"""Anti-detection features for ChromeDriver."""

import re
import shutil
from pathlib import Path

from loguru import logger


class ChromeDriverPatcher:
    """Patches ChromeDriver binary to avoid detection."""

    def __init__(self, chromedriver_path: str):
        self.original_path = Path(chromedriver_path)
        # Create a patched version with a different name
        self.chromedriver_path = self.original_path.parent / "chromedriver_patched.exe"
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

            # Find and replace the CDC injection code
            # The pattern matches: {window.cdc_... = ...;}
            match = re.search(rb"\{window\.cdc.*?;\}", content)

            if match:
                target_bytes = match[0]
                # Replace with harmless console.log padded to same length
                new_bytes = b'{console.log("chromedriver")}'.ljust(len(target_bytes), b" ")
                new_content = content.replace(target_bytes, new_bytes)

                if new_content != content:
                    # Write the patched binary
                    with self.chromedriver_path.open("wb") as f:
                        f.write(new_content)
                    logger.info("ChromeDriver patched successfully")
                    return True
                logger.warning("Failed to patch ChromeDriver: replacement failed")
                return False
            logger.warning("CDC injection code not found in ChromeDriver")
            return False

        except Exception as e:
            logger.error(f"Error patching ChromeDriver: {e}")
            return False

    def restore(self):
        """Restore the original ChromeDriver from backup."""
        if self.backup_path and self.backup_path.exists():
            shutil.copy2(self.backup_path, self.chromedriver_path)
            logger.info("ChromeDriver restored from backup")


def get_anti_detection_arguments() -> list[str]:
    """
    Get Chrome arguments for anti-detection.

    Returns a list of Chrome arguments that help avoid detection.
    """
    return [
        # Disable automation features
        "--disable-blink-features=AutomationControlled",
        # Exclude switches that indicate automation
        "--exclude-switches=enable-automation",
        # Disable the automation extension
        "--disable-dev-shm-usage",
        # Set user agent to remove HeadlessChrome
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
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
        "--window-size=1920,1080",
        # Set language
        "--lang=en-US,en;q=0.9",
    ]


def get_anti_detection_prefs() -> dict:
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


def get_anti_detection_experimental_options() -> dict:
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


def setup_anti_detection_capabilities() -> dict:
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


def execute_anti_detection_scripts(driver) -> None:
    """
    Execute JavaScript to further mask automation.

    This should be called after the driver is initialized.
    """
    scripts = [
        # Remove webdriver property
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """,
        # Modify navigator.plugins to look normal
        """
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        """,
        # Modify navigator.languages
        """
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        """,
        # Add chrome runtime
        """
        window.chrome = {
            runtime: {}
        };
        """,
        # Modify permissions
        """
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """,
    ]

    for script in scripts:
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        except Exception as e:
            logger.warning(f"Failed to execute anti-detection script: {e}")
