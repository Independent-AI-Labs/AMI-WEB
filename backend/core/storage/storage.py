"""Browser storage management - cookies, localStorage, downloads."""

import json
import time
from pathlib import Path
from typing import Any

from browser.backend.utils.exceptions import InstanceError
from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver

DOWNLOAD_CHECK_INTERVAL = 0.5  # seconds


class BrowserStorage:
    """Manages browser storage - cookies, downloads, localStorage."""

    def __init__(self, instance_id: str, config: Any = None, download_dir: Path | None = None, profile_name: str | None = None):
        self.instance_id = instance_id
        self._config = config
        self._download_dir = download_dir
        self._profile_name = profile_name

        # Ensure download directory exists
        if self._download_dir:
            self._download_dir.mkdir(parents=True, exist_ok=True)

    def set_download_directory(self, path: Path) -> None:
        """Set the download directory."""
        self._download_dir = path
        self._download_dir.mkdir(parents=True, exist_ok=True)

    def get_download_directory(self) -> Path | None:
        """Get the download directory path."""
        return self._download_dir

    def list_downloads(self) -> list[dict[str, Any]]:
        """List all files in the download directory."""
        if not self._download_dir or not self._download_dir.exists():
            return []

        downloads = []
        for file in self._download_dir.iterdir():
            if file.is_file() and not file.name.endswith(".crdownload"):
                stat = file.stat()
                downloads.append({"name": file.name, "path": str(file), "size": stat.st_size, "modified": stat.st_mtime, "created": stat.st_ctime})

        return sorted(downloads, key=lambda x: x["modified"], reverse=True)

    def wait_for_download(self, filename: str | None = None, timeout: int = 30) -> Path | None:
        """Wait for a download to complete."""
        if not self._download_dir:
            logger.error("No download directory configured")
            return None

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check for specific file
            if filename:
                file_path = self._download_dir / filename
                if file_path.exists() and not str(file_path).endswith(".crdownload"):
                    return file_path
            else:
                # Get the most recent file
                files = [f for f in self._download_dir.iterdir() if f.is_file() and not f.name.endswith(".crdownload")]
                if files:
                    return max(files, key=lambda f: f.stat().st_mtime)

            time.sleep(DOWNLOAD_CHECK_INTERVAL)

        return None

    def clear_downloads(self) -> int:
        """Clear all files from the download directory."""
        if not self._download_dir or not self._download_dir.exists():
            return 0

        count = 0
        for file in self._download_dir.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file}: {e}")

        logger.info(f"Cleared {count} downloads from {self._download_dir}")
        return count

    def save_cookies(self, driver: WebDriver) -> list[dict[str, Any]]:
        """Save cookies from the current session."""
        if not driver:
            raise InstanceError("Browser not initialized")

        cookies = driver.get_cookies()

        # Save to profile if configured
        if self._profile_name:
            self._save_cookies_to_profile(cookies)

        return cookies

    def _save_cookies_to_profile(self, cookies: list[dict[str, Any]]) -> None:
        """Save cookies to profile directory."""
        if not self._profile_name:
            return

        # Save cookies to a JSON file in the profile directory

        # Use configured profiles directory or default
        profiles_base = Path(self._config.get("backend.storage.profiles_dir", "./data/browser_profiles")) if self._config else Path("./data/browser_profiles")
        profile_dir = profiles_base / self._profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        cookies_file = profile_dir / "cookies.json"

        with cookies_file.open("w") as f:
            json.dump(cookies, f, indent=2)

        logger.debug(f"Saved {len(cookies)} cookies to profile {self._profile_name}")

    def _load_cookies_from_profile(self) -> list[dict[str, Any]] | None:
        """Load cookies from profile directory."""
        if not self._profile_name:
            return None

        # Load cookies from JSON file in the profile directory

        # Use configured profiles directory or default
        profiles_base = Path(self._config.get("backend.storage.profiles_dir", "./data/browser_profiles")) if self._config else Path("./data/browser_profiles")
        cookies_file = profiles_base / self._profile_name / "cookies.json"

        if not cookies_file.exists():
            logger.debug(f"No cookies file found for profile {self._profile_name}")
            return None

        try:
            with cookies_file.open() as f:
                cookies = json.load(f)
            logger.debug(f"Loaded {len(cookies)} cookies from profile {self._profile_name}")
            return cookies  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"Failed to load cookies from profile: {e}")
            return None

    def load_cookies(self, driver: WebDriver, cookies: list[dict[str, Any]] | None = None, navigate_to_domain: bool = True) -> int:
        """Load cookies into the browser."""
        if not driver:
            raise InstanceError("Browser not initialized")

        # Load from profile if no cookies provided
        if not cookies:
            cookies = self._load_cookies_from_profile()

        if not cookies:
            return 0

        # Group cookies by domain
        cookies_by_domain: dict[str, list[dict[str, Any]]] = {}
        for cookie in cookies:
            domain = cookie.get("domain", "")
            if domain:
                if domain not in cookies_by_domain:
                    cookies_by_domain[domain] = []
                cookies_by_domain[domain].append(cookie)

        total_added = 0
        for domain, domain_cookies in cookies_by_domain.items():
            added = self._add_cookies_for_domain(driver, domain, domain_cookies, navigate_to_domain)
            total_added += added

        logger.info(f"Loaded {total_added} cookies into browser")
        return total_added

    def _add_cookies_for_domain(self, driver: WebDriver, domain: str, cookies: list[dict[str, Any]], navigate: bool) -> int:
        """Add cookies for a specific domain."""
        if navigate:
            # Navigate to domain to set cookies
            url = f"https://{domain.lstrip('.')}"
            try:
                driver.get(url)
            except Exception as e:
                logger.warning(f"Failed to navigate to {url}: {e}")
                return 0

        count = 0
        for cookie in cookies:
            try:
                # Remove domain from cookie if navigated
                if navigate and "domain" in cookie:
                    cookie_copy = cookie.copy()
                    del cookie_copy["domain"]
                    driver.add_cookie(cookie_copy)
                else:
                    driver.add_cookie(cookie)
                count += 1
            except Exception as e:
                logger.debug(f"Failed to add cookie: {e}")

        return count

    def get_local_storage(self, driver: WebDriver) -> dict[str, Any]:
        """Get localStorage data from current page."""
        if not driver:
            return {}

        try:
            result: dict[str, Any] = driver.execute_script(
                """
                var items = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            """,
            )
            return result
        except Exception as e:
            logger.debug(f"Failed to get localStorage: {e}")
            return {}

    def set_local_storage(self, driver: WebDriver, data: dict[str, Any]) -> None:
        """Set localStorage data on current page."""
        if not driver:
            return

        try:
            for key, value in data.items():
                driver.execute_script("localStorage.setItem(arguments[0], arguments[1]);", key, value)
        except Exception as e:
            logger.debug(f"Failed to set localStorage: {e}")

    def clear_local_storage(self, driver: WebDriver) -> None:
        """Clear localStorage on current page."""
        if not driver:
            return

        try:
            driver.execute_script("localStorage.clear();")
        except Exception as e:
            logger.debug(f"Failed to clear localStorage: {e}")
