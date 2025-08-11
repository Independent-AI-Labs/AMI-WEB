"""Tests for browser profiles, sessions, downloads, and security features."""

import tempfile
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By

from chrome_manager.core.manager import ChromeManager
from chrome_manager.core.profile_manager import ProfileManager
from chrome_manager.models.security import SecurityConfig, SecurityLevel


@pytest.fixture
async def chrome_manager():
    """Create a Chrome manager instance with test configuration."""
    import tempfile
    from pathlib import Path

    import yaml

    # Create a temporary config file with proper paths
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "chrome_manager": {
                "browser": {
                    "chrome_binary_path": "./chromium-win/chrome.exe",
                    "chromedriver_path": "./chromedriver.exe",
                    "default_headless": True,
                },
                "storage": {
                    "profiles_dir": "./test_profiles",
                    "download_dir": "./test_downloads",
                },
            }
        }
        yaml.dump(config, f)
        config_file = f.name

    try:
        manager = ChromeManager(config_file=config_file)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    finally:
        Path(config_file).unlink(missing_ok=True)


@pytest.fixture
def temp_profiles_dir():
    """Create a temporary directory for profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestProfileManagement:
    """Test browser profile management features."""

    async def test_create_and_use_profile(self, temp_profiles_dir):
        """Test creating and using a browser profile."""
        profile_manager = ProfileManager(base_dir=str(temp_profiles_dir))

        # Create a profile
        profile_dir = profile_manager.create_profile("test_profile", "Test profile for unit tests")
        assert profile_dir.exists()
        assert (temp_profiles_dir / "test_profile").exists()

        # List profiles
        profiles = profile_manager.list_profiles()
        assert len(profiles) == 1
        assert profiles[0]["name"] == "test_profile"
        assert profiles[0]["description"] == "Test profile for unit tests"

        # Get profile directory
        retrieved_dir = profile_manager.get_profile_dir("test_profile")
        assert retrieved_dir == profile_dir

        # Delete profile
        deleted = profile_manager.delete_profile("test_profile")
        assert deleted
        assert not profile_dir.exists()

    async def test_copy_profile(self, temp_profiles_dir):
        """Test copying a profile."""
        profile_manager = ProfileManager(base_dir=str(temp_profiles_dir))

        # Create original profile
        original_dir = profile_manager.create_profile("original", "Original profile")

        # Add some data to the original
        test_file = original_dir / "test.txt"
        test_file.write_text("test data")

        # Copy profile
        copied_dir = profile_manager.copy_profile("original", "copied")
        assert copied_dir.exists()

        # Verify copied data
        copied_test_file = copied_dir / "test.txt"
        assert copied_test_file.exists()
        assert copied_test_file.read_text() == "test data"

        # Verify both profiles exist
        profiles = profile_manager.list_profiles()
        expected_profile_count = 2
        assert len(profiles) == expected_profile_count
        names = {p["name"] for p in profiles}
        assert names == {"original", "copied"}

    @pytest.mark.slow
    async def test_profile_with_cookies(self, chrome_manager):
        """Test saving and loading cookies with profiles."""
        # Create instance with profile
        instance = await chrome_manager.get_or_create_instance(
            headless=True,
            profile="cookie_test",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Navigate to a site that sets cookies
            instance.driver.get("https://httpbin.org/cookies/set?test_cookie=test_value")

            # Save cookies
            cookies = instance.save_cookies()
            assert len(cookies) > 0

            # Clear cookies in browser
            instance.driver.delete_all_cookies()

            # Verify cookies are gone
            instance.driver.get("https://httpbin.org/cookies")
            assert "test_cookie" not in instance.driver.page_source

            # Load cookies back
            count = instance.load_cookies(cookies)
            assert count > 0

            # Verify cookies are restored
            instance.driver.get("https://httpbin.org/cookies")
            assert "test_cookie" in instance.driver.page_source

        finally:
            await instance.terminate()


class TestDownloadManagement:
    """Test download management features."""

    @pytest.mark.slow
    async def test_download_file(self, chrome_manager):
        """Test downloading a file with safe browsing."""
        instance = await chrome_manager.get_or_create_instance(
            headless=True,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Get download directory
            download_dir = instance.get_download_directory()
            assert download_dir is not None
            assert download_dir.exists()

            # Clear any existing downloads
            instance.clear_downloads()

            # Download a test file
            instance.driver.get("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf")

            # Find and click download link if present
            links = instance.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                if "dummy.pdf" in link.get_attribute("href") or "":
                    link.click()
                    break

            # Wait for download to complete
            downloaded_file = instance.wait_for_download(timeout=10)

            if downloaded_file:
                assert downloaded_file.exists()
                assert downloaded_file.suffix == ".pdf"

                # List downloads
                downloads = instance.list_downloads()
                assert len(downloads) > 0
                assert downloads[0]["name"] == downloaded_file.name

            # Clean up
            cleared = instance.clear_downloads()
            assert cleared >= 0

        finally:
            await instance.terminate()

    @pytest.mark.slow
    async def test_profile_specific_downloads(self, chrome_manager):
        """Test that downloads go to profile-specific directories."""
        instance = await chrome_manager.get_or_create_instance(
            headless=True,
            profile="download_test",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            download_dir = instance.get_download_directory()
            assert download_dir is not None
            assert "download_test" in str(download_dir)

        finally:
            await instance.terminate()


class TestSecurityConfiguration:
    """Test security and TLS configuration."""

    async def test_security_levels(self):
        """Test different security level presets."""
        # Test strict security
        strict = SecurityConfig.from_level(SecurityLevel.STRICT)
        assert strict.ignore_certificate_errors is False
        assert strict.safe_browsing_enabled is True
        assert strict.safe_browsing_enhanced is True
        assert strict.site_isolation_enabled is True

        # Test permissive security
        permissive = SecurityConfig.from_level(SecurityLevel.PERMISSIVE)
        assert permissive.ignore_certificate_errors is True
        assert permissive.allow_running_insecure_content is True
        assert permissive.safe_browsing_enabled is False
        assert permissive.disable_web_security is True

    async def test_security_to_chrome_args(self):
        """Test converting security config to Chrome arguments."""
        config = SecurityConfig(
            ignore_certificate_errors=True,
            allow_insecure_localhost=True,
            disable_web_security=True,
        )

        args = config.to_chrome_args()
        assert "--ignore-certificate-errors" in args
        assert "--allow-insecure-localhost" in args
        assert "--disable-web-security" in args

    @pytest.mark.slow
    async def test_permissive_security_allows_insecure(self, chrome_manager):
        """Test that permissive security allows connecting to insecure sites."""
        instance = await chrome_manager.get_or_create_instance(
            headless=True,
            security_config=SecurityConfig.from_level(SecurityLevel.PERMISSIVE),
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # This should work with permissive security even if cert is invalid
            instance.driver.get("https://self-signed.badssl.com/")

            # Should be able to access the page
            assert "badssl.com" in instance.driver.title.lower()

        finally:
            await instance.terminate()

    @pytest.mark.slow
    async def test_strict_security_safe_browsing(self, chrome_manager):
        """Test that strict security enables safe browsing."""
        instance = await chrome_manager.get_or_create_instance(
            headless=True,
            security_config=SecurityConfig.from_level(SecurityLevel.STRICT),
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Verify security config is applied
            security_config = instance.get_security_config()
            assert security_config is not None
            assert security_config.safe_browsing_enabled is True
            assert security_config.download_protection_enabled is True

        finally:
            await instance.terminate()


class TestSessionIsolation:
    """Test session and instance isolation."""

    @pytest.mark.slow
    async def test_profile_isolation(self, chrome_manager):
        """Test that different profiles are isolated from each other."""
        # Create two instances with different profiles
        instance1 = await chrome_manager.get_or_create_instance(
            headless=True,
            profile="profile1",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        instance2 = await chrome_manager.get_or_create_instance(
            headless=True,
            profile="profile2",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Set a cookie in instance1
            instance1.driver.get("https://httpbin.org/cookies/set?profile=one")

            # Set a different cookie in instance2
            instance2.driver.get("https://httpbin.org/cookies/set?profile=two")

            # Verify isolation - instance1 should not see instance2's cookie
            instance1.driver.get("https://httpbin.org/cookies")
            assert '"profile": "one"' in instance1.driver.page_source
            assert '"profile": "two"' not in instance1.driver.page_source

            # Verify instance2 has its own cookie
            instance2.driver.get("https://httpbin.org/cookies")
            assert '"profile": "two"' in instance2.driver.page_source
            assert '"profile": "one"' not in instance2.driver.page_source

        finally:
            await instance1.terminate()
            await instance2.terminate()

    @pytest.mark.slow
    async def test_download_isolation(self, chrome_manager):
        """Test that downloads are isolated between instances."""
        instance1 = await chrome_manager.get_or_create_instance(
            headless=True,
            profile="download1",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        instance2 = await chrome_manager.get_or_create_instance(
            headless=True,
            profile="download2",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Get download directories
            dir1 = instance1.get_download_directory()
            dir2 = instance2.get_download_directory()

            # Directories should be different
            assert dir1 != dir2
            assert "download1" in str(dir1)
            assert "download2" in str(dir2)

            # Each instance has its own download directory
            assert dir1.exists()
            assert dir2.exists()

        finally:
            await instance1.terminate()
            await instance2.terminate()


class TestPersistentSessions:
    """Test persistent browser sessions."""

    @pytest.mark.slow
    async def test_session_persistence(self, chrome_manager):
        """Test that browser sessions persist across restarts."""
        profile_name = "persistent_test"

        # First session - set some data
        instance1 = await chrome_manager.get_or_create_instance(
            headless=True,
            profile=profile_name,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Navigate and set cookies
            instance1.driver.get("https://httpbin.org/cookies/set?persistent=true")

            # Save cookies explicitly
            cookies = instance1.save_cookies()
            assert len(cookies) > 0

        finally:
            await instance1.terminate()

        # Second session - verify data persists
        instance2 = await chrome_manager.get_or_create_instance(
            headless=True,
            profile=profile_name,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Load saved cookies
            loaded = instance2.load_cookies()
            assert loaded > 0

            # Verify cookies persist
            instance2.driver.get("https://httpbin.org/cookies")
            assert "persistent" in instance2.driver.page_source

        finally:
            await instance2.terminate()

    @pytest.mark.slow
    async def test_login_persistence(self, chrome_manager):
        """Test that login sessions can be preserved."""
        profile_name = "login_test"

        # Create instance with profile
        instance = await chrome_manager.get_or_create_instance(
            headless=True,
            profile=profile_name,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Simulate login by setting auth cookies
            instance.driver.get("https://httpbin.org/")
            instance.driver.add_cookie(
                {
                    "name": "auth_token",
                    "value": "test_auth_12345",
                    "domain": "httpbin.org",
                    "path": "/",
                }
            )

            # Save the session
            saved_cookies = instance.save_cookies()

            # Find auth cookie
            auth_cookie = next((c for c in saved_cookies if c["name"] == "auth_token"), None)
            assert auth_cookie is not None
            assert auth_cookie["value"] == "test_auth_12345"

        finally:
            await instance.terminate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
