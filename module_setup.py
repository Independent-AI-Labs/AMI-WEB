#!/usr/bin/env python
"""Browser module setup - delegates to Base and optionally provisions Chrome.

Uses stdlib logging only; third-party imports are deferred until after venv exists.
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Get this module's root
MODULE_ROOT = Path(__file__).resolve().parent


def copy_platform_config() -> None:
    """Copy platform-specific config if config.yaml doesn't exist."""
    config_path = MODULE_ROOT / "config.yaml"

    if not config_path.exists():
        # Determine platform config
        if sys.platform == "win32":
            platform_config = MODULE_ROOT / "configs" / "config.win.yaml"
        elif sys.platform == "darwin":
            platform_config = MODULE_ROOT / "configs" / "config.osx.yaml"
        else:  # Linux
            platform_config = MODULE_ROOT / "configs" / "config.linux.yaml"

        if platform_config.exists():
            logger.info(f"Copying platform config from {platform_config.name}")
            shutil.copy2(platform_config, config_path)
            logger.info(f"[OK] Created config.yaml from {platform_config.name}")
        else:
            logger.warning(f"[WARNING] Platform config not found: {platform_config}")
            # Fall back to config.sample.yaml if it exists
            sample_config = MODULE_ROOT / "config.sample.yaml"
            if sample_config.exists():
                shutil.copy2(sample_config, config_path)
                logger.info("[OK] Created config.yaml from config.sample.yaml")
    else:
        logger.info("[OK] config.yaml already exists")


def get_chrome_paths_from_config() -> tuple[Path | None, Path | None]:
    """Get Chrome and ChromeDriver paths from config."""
    # Try config.yaml first, then config.sample.yaml
    config_path = MODULE_ROOT / "config.yaml"
    if not config_path.exists():
        config_path = MODULE_ROOT / "config.sample.yaml"

    if not config_path.exists():
        # Default paths if no config found
        return None, None

    try:
        # Defer third-party import until needed
        try:
            import yaml  # type: ignore  # noqa: PLC0415
        except Exception:
            logger.warning("[WARNING] PyYAML not available; cannot parse config. Skipping Chrome path detection.")
            return None, None

        with config_path.open() as f:
            config = yaml.safe_load(f)

        chrome_path = config.get("backend", {}).get("browser", {}).get("chrome_binary_path")
        chromedriver_path = config.get("backend", {}).get("browser", {}).get("chromedriver_path")

        if chrome_path:
            # Convert relative paths to absolute
            chrome_path = MODULE_ROOT / chrome_path[2:] if chrome_path.startswith("./") else Path(chrome_path)

        if chromedriver_path:
            # Convert relative paths to absolute
            chromedriver_path = MODULE_ROOT / chromedriver_path[2:] if chromedriver_path.startswith("./") else Path(chromedriver_path)

        return chrome_path, chromedriver_path
    except Exception as e:
        logger.warning(f"[WARNING] Could not parse config: {e}")
        return None, None


def setup_chrome_if_needed() -> None:
    """Check if Chrome is installed at configured locations, and set it up if not."""
    # Get paths from config
    chrome_path, chromedriver_path = get_chrome_paths_from_config()

    if not chrome_path or not chromedriver_path:
        logger.warning("[WARNING] Chrome paths not configured in config.yaml")
        logger.info("Using default locations from config.sample.yaml")
        # Fallback to sample config defaults
        if sys.platform == "win32":
            chrome_path = MODULE_ROOT / "build" / "chromium-win" / "chrome.exe"
            chromedriver_path = MODULE_ROOT / "build" / "chromedriver-win64" / "chromedriver.exe"
        elif sys.platform == "darwin":
            chrome_path = MODULE_ROOT / "build" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
            chromedriver_path = MODULE_ROOT / "build" / "chromedriver"
        else:  # Linux
            chrome_path = MODULE_ROOT / "build" / "chrome-linux" / "chrome"
            chromedriver_path = MODULE_ROOT / "build" / "chromedriver"

    # Check if both executables exist
    chrome_exists = chrome_path.exists() if chrome_path else False
    chromedriver_exists = chromedriver_path.exists() if chromedriver_path else False

    if not chrome_exists or not chromedriver_exists:
        logger.info("\n" + "=" * 60)
        logger.info("Chrome/ChromeDriver not found at configured locations:")
        if not chrome_exists:
            logger.error(f"  Chrome: {chrome_path} (NOT FOUND)")
        if not chromedriver_exists:
            logger.error(f"  ChromeDriver: {chromedriver_path} (NOT FOUND)")
        logger.info("Setting up Chrome...")
        logger.info("=" * 60)

        # Run the Chrome setup script
        setup_chrome_script = MODULE_ROOT / "scripts" / "setup_chrome.py"
        if setup_chrome_script.exists():
            result = subprocess.run([sys.executable, str(setup_chrome_script)], check=False)
            if result.returncode == 0:
                logger.info("[OK] Chrome and ChromeDriver installed successfully")
            else:
                logger.error("[ERROR] Failed to install Chrome/ChromeDriver")
                logger.info("You can manually run: python browser/scripts/setup_chrome.py")
                return
        else:
            logger.error(f"[ERROR] setup_chrome.py script not found at {setup_chrome_script}")
            return
    else:
        logger.info("\n[OK] Chrome and ChromeDriver found at configured locations:")
        logger.info(f"  Chrome: {chrome_path}")
        logger.info(f"  ChromeDriver: {chromedriver_path}")

    return


def main() -> int:
    """Run setup for browser module by calling base module_setup.py directly."""
    # Find base module_setup.py
    base_setup = MODULE_ROOT.parent / "base" / "module_setup.py"
    if not base_setup.exists():
        logger.error("ERROR: Cannot find base/module_setup.py")
        sys.exit(1)

    # Call base module_setup.py with appropriate arguments
    cmd = [sys.executable, str(base_setup), "--project-dir", str(MODULE_ROOT), "--project-name", "Browser Module"]

    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        return result.returncode

    # Copy platform-specific config if needed
    copy_platform_config()

    # After successful base setup, set up Chrome if needed
    setup_chrome_if_needed()

    return 0


if __name__ == "__main__":
    sys.exit(main())
