#!/usr/bin/env python
"""Browser module setup - uses base AMIModuleSetup and sets up Chrome."""

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# Get this module's root
MODULE_ROOT = Path(__file__).resolve().parent


def copy_platform_config():
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
            print(f"Copying platform config from {platform_config.name}")
            shutil.copy2(platform_config, config_path)
            print(f"[OK] Created config.yaml from {platform_config.name}")
        else:
            print(f"[WARNING] Platform config not found: {platform_config}")
            # Fall back to config.sample.yaml if it exists
            sample_config = MODULE_ROOT / "config.sample.yaml"
            if sample_config.exists():
                shutil.copy2(sample_config, config_path)
                print("[OK] Created config.yaml from config.sample.yaml")
    else:
        print("[OK] config.yaml already exists")


def get_chrome_paths_from_config():
    """Get Chrome and ChromeDriver paths from config."""
    # Try config.yaml first, then config.sample.yaml
    config_path = MODULE_ROOT / "config.yaml"
    if not config_path.exists():
        config_path = MODULE_ROOT / "config.sample.yaml"

    if not config_path.exists():
        # Default paths if no config found
        return None, None

    try:
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
        print(f"[WARNING] Could not parse config: {e}")
        return None, None


def setup_chrome_if_needed():
    """Check if Chrome is installed at configured locations, and set it up if not."""
    # Get paths from config
    chrome_path, chromedriver_path = get_chrome_paths_from_config()

    if not chrome_path or not chromedriver_path:
        print("[WARNING] Chrome paths not configured in config.yaml")
        print("Using default locations from config.sample.yaml")
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
        print("\n" + "=" * 60)
        print("Chrome/ChromeDriver not found at configured locations:")
        if not chrome_exists:
            print(f"  Chrome: {chrome_path} (NOT FOUND)")
        if not chromedriver_exists:
            print(f"  ChromeDriver: {chromedriver_path} (NOT FOUND)")
        print("Setting up Chrome...")
        print("=" * 60)

        # Run the Chrome setup script
        setup_chrome_script = MODULE_ROOT / "scripts" / "setup_chrome.py"
        if setup_chrome_script.exists():
            result = subprocess.run([sys.executable, str(setup_chrome_script)], check=False)
            if result.returncode == 0:
                print("[OK] Chrome and ChromeDriver installed successfully")
            else:
                print("[ERROR] Failed to install Chrome/ChromeDriver")
                print("You can manually run: python browser/scripts/setup_chrome.py")
                return False
        else:
            print("[ERROR] setup_chrome.py script not found at", setup_chrome_script)
            return False
    else:
        print("\n[OK] Chrome and ChromeDriver found at configured locations:")
        print(f"  Chrome: {chrome_path}")
        print(f"  ChromeDriver: {chromedriver_path}")

    return True


def main():
    """Run setup for browser module by calling base setup.py directly."""
    # Find base setup.py
    base_setup = MODULE_ROOT.parent / "base" / "setup.py"
    if not base_setup.exists():
        print("ERROR: Cannot find base/setup.py")
        sys.exit(1)

    # Call base setup.py with appropriate arguments
    cmd = [sys.executable, str(base_setup), "--project-dir", str(MODULE_ROOT), "--project-name", "Browser Module"]

    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        return result.returncode

    # Copy platform-specific config if needed
    copy_platform_config()

    # After successful base setup, set up Chrome if needed
    if not setup_chrome_if_needed():
        print("\n[WARNING] Chrome setup failed, but module setup is complete")
        print("You may need to manually set up Chrome before running browser tests")

    return 0


if __name__ == "__main__":
    sys.exit(main())
