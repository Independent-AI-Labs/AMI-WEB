"""Unit tests for default profile functionality."""

import json
from pathlib import Path

import pytest

from browser.backend.core.management.profile_manager import ProfileManager

pytestmark = pytest.mark.xdist_group(name="profile")


@pytest.fixture
def profile_dir(tmp_path: Path) -> Path:
    """Create a temporary profile directory."""
    return tmp_path / "profiles"


@pytest.fixture
def manager(profile_dir: Path) -> ProfileManager:
    """Create a ProfileManager instance."""
    return ProfileManager(base_dir=str(profile_dir))


def test_ensure_default_profile_creates_if_not_exists(manager: ProfileManager, profile_dir: Path) -> None:
    """Test that ensure_default_profile creates default profile if it doesn't exist."""
    # Should not exist initially
    assert not (profile_dir / "default").exists()
    assert "default" not in manager.profiles

    # Call ensure_default_profile
    result_path = manager.ensure_default_profile()

    # Check it was created
    assert result_path == profile_dir / "default"
    assert result_path.exists()
    assert "default" in manager.profiles
    assert manager.profiles["default"]["description"] == "Default profile for session persistence with HTTPS certificate exceptions"


def test_ensure_default_profile_returns_existing(manager: ProfileManager) -> None:
    """Test that ensure_default_profile returns existing profile if it exists."""
    # Create default profile first
    first_path = manager.ensure_default_profile()
    first_created_at = manager.profiles["default"]["created_at"]

    # Call again
    second_path = manager.ensure_default_profile()

    # Should return same path and not recreate
    assert second_path == first_path
    assert manager.profiles["default"]["created_at"] == first_created_at


def test_ensure_default_profile_loads_from_metadata(profile_dir: Path) -> None:
    """Test that ensure_default_profile works with existing metadata."""
    # Create metadata file manually
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "default").mkdir(exist_ok=True)
    metadata = {
        "default": {
            "description": "Existing default",
            "created_at": "2025-01-01T00:00:00",
            "last_used": "2025-01-01T00:00:00",
        }
    }
    with (profile_dir / "profiles.json").open("w") as f:
        json.dump(metadata, f)

    # Create manager (should load existing metadata)
    manager = ProfileManager(base_dir=str(profile_dir))

    # Ensure default profile
    result_path = manager.ensure_default_profile()

    # Should return existing profile
    assert result_path == profile_dir / "default"
    assert "default" in manager.profiles
    assert manager.profiles["default"]["description"] == "Existing default"


def test_ensure_default_profile_persistence(manager: ProfileManager, profile_dir: Path) -> None:
    """Test that default profile is persisted to metadata."""
    manager.ensure_default_profile()

    # Check metadata file was created
    metadata_file = profile_dir / "profiles.json"
    assert metadata_file.exists()

    # Load and verify
    with metadata_file.open() as f:
        metadata = json.load(f)

    assert "default" in metadata
    assert "created_at" in metadata["default"]
    assert "description" in metadata["default"]
