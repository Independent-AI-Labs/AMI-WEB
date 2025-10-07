"""Test profile directory isolation to verify each profile gets a unique directory."""

from pathlib import Path
from typing import Any

import pytest

from browser.backend.core.browser.options import BrowserOptionsBuilder
from browser.backend.core.management.profile_manager import ProfileManager


class TestProfileIsolation:
    """Test that profiles use completely separate directories without conflicts."""

    def test_profile_manager_unique_paths(self, tmp_path: Path) -> None:
        """Test that ProfileManager returns unique paths for different profiles."""
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))

        # Create multiple profiles
        profile1_dir = manager.create_profile("profile1", "First profile")
        profile2_dir = manager.create_profile("profile2", "Second profile")
        profile3_dir = manager.create_profile("profile3", "Third profile")

        # Verify all paths are different
        assert profile1_dir != profile2_dir
        assert profile1_dir != profile3_dir
        assert profile2_dir != profile3_dir

        # Verify all directories exist and are separate
        assert profile1_dir.exists()
        assert profile2_dir.exists()
        assert profile3_dir.exists()

        # Verify they are siblings in the same parent directory
        assert profile1_dir.parent == profile2_dir.parent == profile3_dir.parent

        # Verify profile names match directory names
        assert profile1_dir.name == "profile1"
        assert profile2_dir.name == "profile2"
        assert profile3_dir.name == "profile3"

    def test_profile_directory_no_collision(self, tmp_path: Path) -> None:
        """Test that profile directories don't share lock files."""
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))

        # Create two profiles
        profile1_dir = manager.create_profile("profile1")
        profile2_dir = manager.create_profile("profile2")

        # Create lock files in profile1
        (profile1_dir / "SingletonLock").touch()
        (profile1_dir / "SingletonSocket").touch()
        (profile1_dir / "SingletonCookie").touch()

        # Verify profile2 doesn't have these locks
        assert not (profile2_dir / "SingletonLock").exists()
        assert not (profile2_dir / "SingletonSocket").exists()
        assert not (profile2_dir / "SingletonCookie").exists()

        # Create locks in profile2
        (profile2_dir / "SingletonLock").touch()

        # Verify both directories have their own lock files
        assert (profile1_dir / "SingletonLock").exists()
        assert (profile2_dir / "SingletonLock").exists()

        # Verify they are different files
        assert profile1_dir / "SingletonLock" != profile2_dir / "SingletonLock"

    def test_options_builder_unique_user_data_dirs(self, tmp_path: Path) -> None:
        """Test that BrowserOptionsBuilder sets unique user-data-dir for each profile."""
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))

        # Create profiles
        manager.create_profile("profile1")
        manager.create_profile("profile2")

        # Build options for each profile
        builder1 = BrowserOptionsBuilder(profile_manager=manager)
        options1 = builder1.build(headless=True, profile="profile1")

        builder2 = BrowserOptionsBuilder(profile_manager=manager)
        options2 = builder2.build(headless=True, profile="profile2")

        # Extract user-data-dir arguments
        def get_user_data_dir(options: Any) -> str | None:
            arg_val: str
            for arg_val in options.arguments:
                if arg_val.startswith("--user-data-dir="):
                    return arg_val.split("=", 1)[1]
            return None

        dir1 = get_user_data_dir(options1)
        dir2 = get_user_data_dir(options2)

        # Verify both have user-data-dir set
        assert dir1 is not None, "Profile1 should have user-data-dir set"
        assert dir2 is not None, "Profile2 should have user-data-dir set"

        # Verify they are different
        assert dir1 != dir2, f"User data directories must be different: {dir1} vs {dir2}"

        # Verify they match the expected profile paths
        assert "profile1" in dir1
        assert "profile2" in dir2

    def test_temp_profiles_unique_dirs(self) -> None:
        """Test that temporary profiles (no name) get unique directories."""
        builder1 = BrowserOptionsBuilder()
        builder2 = BrowserOptionsBuilder()

        # Build options without profile names (creates temp directories)
        options1 = builder1.build(headless=True, profile=None)
        options2 = builder2.build(headless=True, profile=None)

        # Extract user-data-dir arguments
        def get_user_data_dir(options: Any) -> str | None:
            arg_val: str
            for arg_val in options.arguments:
                if arg_val.startswith("--user-data-dir="):
                    return arg_val.split("=", 1)[1]
            return None

        dir1 = get_user_data_dir(options1)
        dir2 = get_user_data_dir(options2)

        # Verify both have user-data-dir set
        assert dir1 is not None
        assert dir2 is not None

        # Verify they are different (temp directories should be unique)
        assert dir1 != dir2, f"Temporary directories must be unique: {dir1} vs {dir2}"

        # Verify both contain the chrome_temp prefix
        assert "chrome_temp_" in dir1
        assert "chrome_temp_" in dir2

        # Cleanup temp directories
        builder1.cleanup_temp_profile()
        builder2.cleanup_temp_profile()

    def test_concurrent_profile_creation(self, tmp_path: Path) -> None:
        """Test that concurrent profile operations don't cause collisions."""
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))

        # Create multiple profiles in sequence (simulating concurrent access)
        profiles = []
        for i in range(5):
            profile_dir = manager.create_profile(f"concurrent_{i}", f"Profile {i}")
            profiles.append(profile_dir)

        # Verify all are unique
        unique_paths = {str(p) for p in profiles}
        assert len(unique_paths) == 5, "All profile paths must be unique"

        # Verify all exist
        for profile_dir in profiles:
            assert profile_dir.exists()

    def test_get_profile_dir_consistency(self, tmp_path: Path) -> None:
        """Test that get_profile_dir returns the same path consistently."""
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))

        # Create profile
        created_dir = manager.create_profile("test_profile")

        # Get the directory multiple times
        retrieved_dir1 = manager.get_profile_dir("test_profile")
        retrieved_dir2 = manager.get_profile_dir("test_profile")
        retrieved_dir3 = manager.get_profile_dir("test_profile")

        # All should be the same
        assert created_dir == retrieved_dir1
        assert retrieved_dir1 == retrieved_dir2
        assert retrieved_dir2 == retrieved_dir3

    def test_profile_path_structure(self, tmp_path: Path) -> None:
        """Test that profile paths follow the expected structure."""
        base_dir = tmp_path / "profiles"
        manager = ProfileManager(base_dir=str(base_dir))

        profile_name = "test_structure"
        profile_dir = manager.create_profile(profile_name)

        # Expected path: base_dir / profile_name
        expected_path = base_dir / profile_name

        assert profile_dir == expected_path
        assert profile_dir.parent == base_dir
        assert profile_dir.name == profile_name

    @pytest.mark.asyncio
    async def test_multiple_instances_same_profile(self, tmp_path: Path) -> None:
        """Test that launching multiple instances with the same profile causes issues.

        This test documents the EXPECTED behavior: Chrome should prevent
        multiple instances from using the same user-data-dir simultaneously.
        """
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))
        manager.create_profile("shared_profile")

        builder1 = BrowserOptionsBuilder(profile_manager=manager)
        builder2 = BrowserOptionsBuilder(profile_manager=manager)

        options1 = builder1.build(headless=True, profile="shared_profile")
        options2 = builder2.build(headless=True, profile="shared_profile")

        # Extract user-data-dir from both
        def get_user_data_dir(options: Any) -> str | None:
            arg_val: str
            for arg_val in options.arguments:
                if arg_val.startswith("--user-data-dir="):
                    return arg_val.split("=", 1)[1]
            return None

        dir1 = get_user_data_dir(options1)
        dir2 = get_user_data_dir(options2)

        # Both should point to the SAME directory (this is the problem!)
        assert dir1 == dir2, "Same profile should use same directory"

        # This demonstrates the issue: if two BrowserInstances try to launch
        # with the same profile simultaneously, they'll conflict because
        # Chrome locks the user-data-dir

    def test_profile_reuse_after_cleanup(self, tmp_path: Path) -> None:
        """Test that a profile can be reused after proper cleanup."""
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))
        profile_dir = manager.create_profile("reusable")

        # Simulate lock file creation (from first instance)
        lock_file = profile_dir / "SingletonLock"
        lock_file.touch()

        assert lock_file.exists()

        # Cleanup stale locks
        builder = BrowserOptionsBuilder(profile_manager=manager)
        builder._cleanup_stale_locks(profile_dir)

        # Lock should be removed
        assert not lock_file.exists()

        # Now the profile can be used again
        reused_dir = manager.get_profile_dir("reusable")
        assert reused_dir == profile_dir
        assert reused_dir.exists()

    @pytest.mark.asyncio
    async def test_concurrent_same_profile_race_condition(self, tmp_path: Path) -> None:
        """Test the race condition when two instances try to use the same profile concurrently.

        This test demonstrates the BUG: If two BrowserInstance.launch() calls happen
        concurrently for the same profile, both will try to use the same user-data-dir,
        causing Chrome to fail with "user data directory is already in use".

        The issue is in ChromeManager.get_or_create_instance() lines 145-150:
        - It checks if an instance with the profile already exists
        - BUT if two requests come in before either is added to _standalone_instances,
          both will pass the check and try to launch with the same profile directory
        """
        manager = ProfileManager(base_dir=str(tmp_path / "profiles"))
        manager.create_profile("shared")

        # Simulate two concurrent requests by building options for the same profile
        builder1 = BrowserOptionsBuilder(profile_manager=manager)
        builder2 = BrowserOptionsBuilder(profile_manager=manager)

        # Both build options for the same profile
        options1 = builder1.build(headless=True, profile="shared")
        options2 = builder2.build(headless=True, profile="shared")

        # Extract user-data-dir from both
        def get_user_data_dir(options: Any) -> str | None:
            arg_val: str
            for arg_val in options.arguments:
                if arg_val.startswith("--user-data-dir="):
                    return arg_val.split("=", 1)[1]
            return None

        dir1 = get_user_data_dir(options1)
        dir2 = get_user_data_dir(options2)

        # THIS IS THE BUG: Both point to the same directory
        assert dir1 == dir2, "Same profile uses same directory"
        assert dir1 is not None and "shared" in dir1

        # If both BrowserInstance objects tried to launch Chrome simultaneously,
        # the second would fail with: "user data directory is already in use"
        # because Chrome creates a SingletonLock in the profile directory.

        # The solution is to add locking in ChromeManager to ensure only one
        # instance launch per profile can happen at a time.
