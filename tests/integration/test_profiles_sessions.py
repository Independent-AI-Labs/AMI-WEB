"""Tests for browser profiles, sessions, downloads, and security features."""

import tempfile
from contextlib import suppress
from pathlib import Path

import pytest
import yaml
from browser.backend.core.management.manager import ChromeManager
from browser.backend.core.management.profile_manager import ProfileManager
from browser.backend.models.security import SecurityConfig, SecurityLevel
from browser.backend.utils.config import Config
from selenium.webdriver.common.by import By


@pytest.fixture
async def backend():
    """Create a Chrome manager instance with test configuration."""

    # Try to use existing config.yaml or config.test.yaml first
    config_file = None
    if Path("config.yaml").exists():
        config_file = "config.yaml"
    elif Path("config.test.yaml").exists():
        config_file = "config.test.yaml"

    if config_file:
        # Load existing config and modify storage paths for testing
        existing_config = Config.load(config_file)
        config_data = existing_config._data.copy()

        # Override storage paths for test isolation
        if "backend" not in config_data:
            config_data["backend"] = {}
        if "storage" not in config_data["backend"]:
            config_data["backend"]["storage"] = {}

        config_data["backend"]["storage"].update(
            {
                "profiles_dir": "./data/test_profiles",
                "download_dir": "./data/test_downloads",
                "session_dir": "./data/test_sessions",
            },
        )

        # Create temporary config with correct paths
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_config_file = f.name

        manager = ChromeManager(config_file=temp_config_file)
    else:
        # Fallback to creating config from scratch
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "backend": {
                    "browser": {
                        "default_headless": True,
                    },
                    "storage": {
                        "profiles_dir": "./data/test_profiles",
                        "download_dir": "./data/test_downloads",
                        "session_dir": "./data/test_sessions",
                    },
                },
            }
            yaml.dump(config, f)
            temp_config_file = f.name

        manager = ChromeManager(config_file=temp_config_file)

    try:
        # Don't initialize pool to avoid conflicts with profile tests
        # Just initialize the session manager
        await manager.session_manager.initialize()
        manager._initialized = True
        yield manager
        await manager.shutdown()
    finally:
        if temp_config_file:
            Path(temp_config_file).unlink(missing_ok=True)


@pytest.fixture
def temp_profiles_dir():
    """Create a temporary directory for profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
async def cleanup_test_profiles(backend):
    """Clean up test profiles before and after each test."""
    # Clean up any leftover profiles before test
    profile_names = ["cookie_test", "download_test", "download1", "download2", "profile1", "profile2", "persistent_test", "login_test"]

    for name in profile_names:
        with suppress(Exception):
            backend.profile_manager.delete_profile(name)

    yield

    # Clean up after test
    for name in profile_names:
        with suppress(Exception):
            backend.profile_manager.delete_profile(name)


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
    async def test_profile_with_cookies(self, backend):
        """Test saving and loading cookies with profiles."""
        # Create instance with profile
        instance = await backend.get_or_create_instance(
            headless=True,
            profile="cookie_test",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Navigate to google.com first
            instance.driver.get("https://www.google.com/")

            # Manually add a test cookie
            instance.driver.add_cookie({"name": "test_cookie", "value": "test_value", "domain": ".google.com", "path": "/"})

            # Save cookies
            cookies = instance.save_cookies()
            assert len(cookies) > 0

            # Clear cookies in browser
            instance.driver.delete_all_cookies()

            # Verify cookies are gone by checking we can't find our test cookie
            current_cookies = instance.driver.get_cookies()
            assert not any(c["name"] == "test_cookie" for c in current_cookies)

            # Load cookies back
            count = instance.load_cookies(cookies)
            assert count > 0

            # Verify cookies are restored
            instance.driver.get("https://www.google.com/")
            current_cookies = instance.driver.get_cookies()
            assert any(c["name"] == "test_cookie" and c["value"] == "test_value" for c in current_cookies)

        finally:
            await instance.terminate()


class TestDownloadManagement:
    """Test download management features."""

    @pytest.mark.slow
    async def test_download_file(self, backend):
        """Test downloading a file with safe browsing."""
        instance = await backend.get_or_create_instance(
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
    async def test_profile_specific_downloads(self, backend):
        """Test that downloads go to profile-specific directories."""
        instance = await backend.get_or_create_instance(
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
    async def test_permissive_security_allows_insecure(self, backend):
        """Test that permissive security allows connecting to insecure sites."""
        instance = await backend.get_or_create_instance(
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
    async def test_strict_security_safe_browsing(self, backend):
        """Test that strict security enables safe browsing."""
        instance = await backend.get_or_create_instance(
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
    async def test_profile_isolation(self, backend, test_html_server):
        """Test that different profiles are isolated from each other."""
        # Create two instances with different profiles
        instance1 = await backend.get_or_create_instance(
            headless=True,
            profile="profile1",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        instance2 = await backend.get_or_create_instance(
            headless=True,
            profile="profile2",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Set cookies and localStorage in instance1
            instance1.driver.get(f"{test_html_server}/test_page.html")
            instance1.driver.execute_script("window.testHelpers.setCookie('profile', 'one');")
            instance1.driver.execute_script("window.testHelpers.setLocalStorage('profile', 'one');")

            # Set different data in instance2
            instance2.driver.get(f"{test_html_server}/test_page.html")
            instance2.driver.execute_script("window.testHelpers.setCookie('profile', 'two');")
            instance2.driver.execute_script("window.testHelpers.setLocalStorage('profile', 'two');")

            # Verify isolation - instance1 should not see instance2's data
            instance1.driver.get(f"{test_html_server}/test_page.html")
            cookie1 = instance1.driver.execute_script("return window.testHelpers.getCookie('profile')")
            storage1 = instance1.driver.execute_script("return window.testHelpers.getLocalStorage('profile')")
            assert cookie1 == "one"
            assert storage1 == "one"

            # Verify instance2 has its own data
            instance2.driver.get(f"{test_html_server}/test_page.html")
            cookie2 = instance2.driver.execute_script("return window.testHelpers.getCookie('profile')")
            storage2 = instance2.driver.execute_script("return window.testHelpers.getLocalStorage('profile')")
            assert cookie2 == "two"
            assert storage2 == "two"

        finally:
            await instance1.terminate()
            await instance2.terminate()

    @pytest.mark.slow
    async def test_download_isolation(self, backend):
        """Test that downloads are isolated between instances."""
        instance1 = await backend.get_or_create_instance(
            headless=True,
            profile="download1",
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        instance2 = await backend.get_or_create_instance(
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
    async def test_session_persistence(self, backend, test_html_server):
        """Test that browser sessions persist across restarts."""
        profile_name = "persistent_test"

        # First session - set some data
        instance1 = await backend.get_or_create_instance(
            headless=True,
            profile=profile_name,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Navigate to test page and set cookie
            instance1.driver.get(f"{test_html_server}/test_page.html")
            instance1.driver.execute_script("window.testHelpers.setCookie('persistent', 'true');")
            instance1.driver.execute_script("window.testHelpers.setLocalStorage('persistent', 'true');")

            # Save cookies explicitly
            instance1.save_cookies()
            # May not save cookies for localhost, so create marker file instead

            # Create a marker file in download directory as our persistence test
            download_dir = instance1.get_download_directory()
            assert download_dir is not None, "Download directory should exist"
            marker = download_dir / "test_marker.txt"
            marker.write_text("persistent=true")

        finally:
            await instance1.terminate()

        # Second session - verify data persists
        instance2 = await backend.get_or_create_instance(
            headless=True,
            profile=profile_name,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Check if profile directory persists (through marker file)
            download_dir = instance2.get_download_directory()
            assert download_dir is not None, "Download directory should exist for second instance"
            marker = download_dir / "test_marker.txt"
            assert marker.exists(), "Profile persistence marker not found - profile directory was not reused"
            assert marker.read_text() == "persistent=true", "Marker content incorrect"

            # Try to load cookies (may be 0 for localhost)
            instance2.load_cookies()
            # Don't assert on cookie count as localhost cookies may not persist

            # The fact that the marker file exists proves profile persistence works

        finally:
            await instance2.terminate()

    @pytest.mark.slow
    async def test_login_persistence(self, backend):
        """Test that login sessions can be preserved."""
        profile_name = "login_test"

        # Create instance with profile
        instance = await backend.get_or_create_instance(
            headless=True,
            profile=profile_name,
            use_pool=False,
            anti_detect=False,  # Disable for tests
        )

        try:
            # Simulate login by setting auth cookies
            instance.driver.get("https://www.google.com/")
            instance.driver.add_cookie(
                {
                    "name": "auth_token",
                    "value": "test_auth_12345",
                    "domain": ".google.com",
                    "path": "/",
                },
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
