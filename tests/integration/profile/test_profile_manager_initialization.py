"""Integration tests for ProfileManager initialization paths.

These tests verify that ProfileManager methods correctly load metadata from disk
before performing operations, preventing bugs where self.profiles is empty but
the metadata file exists.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from browser.backend.core.management.profile_manager import ProfileManager
from browser.backend.utils.exceptions import ProfileError

pytestmark = pytest.mark.xdist_group(name="profile")


@pytest.fixture
def profile_dir(tmp_path: Path) -> Path:
    """Create a temporary profile directory."""
    return tmp_path / "profiles"


@pytest.fixture
def existing_metadata(profile_dir: Path) -> dict[str, Any]:
    """Create existing metadata file on disk - returns the metadata dict."""
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Create profile directories
    (profile_dir / "test_profile").mkdir(exist_ok=True)
    (profile_dir / "source_profile").mkdir(exist_ok=True)

    # Write metadata file
    metadata = {
        "test_profile": {
            "description": "Test profile",
            "created_at": "2025-01-01T00:00:00",
            "last_used": "2025-01-01T00:00:00",
        },
        "source_profile": {
            "description": "Source profile",
            "created_at": "2025-01-02T00:00:00",
            "last_used": "2025-01-02T00:00:00",
        },
    }

    with (profile_dir / "profiles.json").open("w") as f:
        json.dump(metadata, f)

    return metadata


@pytest.fixture
def _existing_metadata(existing_metadata: dict[str, Any]) -> dict[str, Any]:
    """Side-effect fixture that creates metadata file - use when return value not needed."""
    return existing_metadata


def test_get_profile_dir_loads_existing_metadata(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that get_profile_dir loads metadata from disk before checking if profile exists."""
    # Create manager with empty self.profiles (metadata not loaded)
    manager = ProfileManager(base_dir=str(profile_dir))
    assert manager.profiles == {}  # Not loaded yet

    # Call get_profile_dir - should load metadata and find existing profile
    result = manager.get_profile_dir("test_profile")

    # Should return path without trying to create
    assert result == profile_dir / "test_profile"
    assert "test_profile" in manager.profiles
    assert manager.profiles["test_profile"]["description"] == "Test profile"


def test_get_profile_dir_raises_for_nonexistent(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that get_profile_dir raises error if profile not found in metadata."""
    manager = ProfileManager(base_dir=str(profile_dir))

    # Profile doesn't exist in metadata - should raise error, not auto-create
    with pytest.raises(ProfileError, match="Profile 'new_profile' not found"):
        manager.get_profile_dir("new_profile")


def test_delete_profile_loads_existing_metadata(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that delete_profile loads metadata before checking if profile exists."""
    manager = ProfileManager(base_dir=str(profile_dir))
    assert manager.profiles == {}  # Not loaded yet

    # Delete existing profile
    result = manager.delete_profile("test_profile")

    assert result is True
    assert not (profile_dir / "test_profile").exists()
    assert "test_profile" not in manager.profiles


def test_delete_profile_returns_false_for_nonexistent(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that delete_profile returns False for non-existent profile."""
    manager = ProfileManager(base_dir=str(profile_dir))

    result = manager.delete_profile("nonexistent")

    assert result is False


def test_list_profiles_loads_existing_metadata(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that list_profiles loads metadata before returning list."""
    manager = ProfileManager(base_dir=str(profile_dir))
    assert manager.profiles == {}  # Not loaded yet

    # List profiles - should load metadata
    profiles = manager.list_profiles()

    assert len(profiles) == 2
    profile_names = {p["name"] for p in profiles}
    assert profile_names == {"test_profile", "source_profile"}

    # Find test_profile
    test_prof = next(p for p in profiles if p["name"] == "test_profile")
    assert test_prof["description"] == "Test profile"
    assert test_prof["exists"] is True


def test_copy_profile_loads_existing_metadata(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that copy_profile loads metadata before checking if profiles exist."""
    manager = ProfileManager(base_dir=str(profile_dir))
    assert manager.profiles == {}  # Not loaded yet

    # Copy existing profile
    result = manager.copy_profile("source_profile", "dest_profile")

    assert result == profile_dir / "dest_profile"
    assert result.exists()
    assert "dest_profile" in manager.profiles


def test_copy_profile_source_not_found(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that copy_profile raises error for non-existent source."""
    manager = ProfileManager(base_dir=str(profile_dir))

    with pytest.raises(ProfileError, match="Source profile nonexistent not found"):
        manager.copy_profile("nonexistent", "dest_profile")


def test_copy_profile_dest_already_exists(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that copy_profile raises error when destination already exists."""
    manager = ProfileManager(base_dir=str(profile_dir))

    with pytest.raises(ProfileError, match="Destination profile test_profile already exists"):
        manager.copy_profile("source_profile", "test_profile")


def test_ensure_default_profile_when_exists_in_metadata(profile_dir: Path) -> None:
    """Test that ensure_default_profile finds existing default profile in metadata."""
    # Create metadata with default profile
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "default").mkdir(exist_ok=True)

    metadata = {
        "default": {
            "description": "Default profile for session persistence with HTTPS certificate exceptions",
            "created_at": "2025-01-01T00:00:00",
            "last_used": "2025-01-01T00:00:00",
        }
    }

    with (profile_dir / "profiles.json").open("w") as f:
        json.dump(metadata, f)

    # Create manager with empty self.profiles
    manager = ProfileManager(base_dir=str(profile_dir))
    assert manager.profiles == {}

    # Should find existing default profile
    result = manager.ensure_default_profile()

    assert result == profile_dir / "default"
    assert "default" in manager.profiles
    # Should not have recreated - timestamp should match
    assert manager.profiles["default"]["created_at"] == "2025-01-01T00:00:00"


def test_ensure_default_profile_creates_if_not_exists(profile_dir: Path) -> None:
    """Test that ensure_default_profile creates default profile if not in metadata."""
    profile_dir.mkdir(parents=True, exist_ok=True)

    manager = ProfileManager(base_dir=str(profile_dir))

    # Should create default profile
    result = manager.ensure_default_profile()

    assert result == profile_dir / "default"
    assert result.exists()
    assert "default" in manager.profiles
    assert "certificate" in manager.profiles["default"]["description"].lower()


def test_metadata_persists_across_manager_instances(profile_dir: Path) -> None:
    """Test that metadata saved by one manager instance is loaded by another."""
    profile_dir.mkdir(parents=True, exist_ok=True)

    # First manager creates a profile
    manager1 = ProfileManager(base_dir=str(profile_dir))
    manager1.create_profile("persistent_profile", "This should persist")

    # Second manager should load it
    manager2 = ProfileManager(base_dir=str(profile_dir))
    profiles = manager2.list_profiles()

    assert len(profiles) == 1
    assert profiles[0]["name"] == "persistent_profile"
    assert profiles[0]["description"] == "This should persist"


def test_get_profile_dir_updates_last_used(profile_dir: Path, existing_metadata: dict[str, Any]) -> None:
    """Test that get_profile_dir updates last_used timestamp."""
    manager = ProfileManager(base_dir=str(profile_dir))

    original_last_used = existing_metadata["test_profile"]["last_used"]

    # Get profile dir - should update last_used
    manager.get_profile_dir("test_profile")

    # Load metadata from file
    with (profile_dir / "profiles.json").open() as f:
        updated_metadata = json.load(f)

    assert updated_metadata["test_profile"]["last_used"] != original_last_used


def test_concurrent_profile_operations_after_initialization(profile_dir: Path, _existing_metadata: dict[str, Any]) -> None:
    """Test that multiple operations work correctly after metadata is loaded."""
    manager = ProfileManager(base_dir=str(profile_dir))

    # First operation loads metadata
    profiles = manager.list_profiles()
    assert len(profiles) == 2

    # Subsequent operations should use loaded metadata
    path = manager.get_profile_dir("test_profile")
    assert path.exists()

    # Create new profile
    new_path = manager.create_profile("another_profile", "Another one")
    assert new_path.exists()

    # List again - should show all 3
    profiles = manager.list_profiles()
    assert len(profiles) == 3


def test_empty_metadata_file_initializes_correctly(profile_dir: Path) -> None:
    """Test that ProfileManager handles empty metadata file correctly."""
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Create empty metadata file
    with (profile_dir / "profiles.json").open("w") as f:
        json.dump({}, f)

    manager = ProfileManager(base_dir=str(profile_dir))

    # Should be able to create profiles
    path = manager.create_profile("first_profile", "First")
    assert path.exists()

    profiles = manager.list_profiles()
    assert len(profiles) == 1
