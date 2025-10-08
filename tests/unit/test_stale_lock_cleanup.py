"""Test stale lock file cleanup."""

from pathlib import Path

from browser.backend.core.browser.options import BrowserOptionsBuilder


def test_cleanup_stale_locks(tmp_path: Path) -> None:
    """Test that stale lock files are removed."""
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()

    # Create fake stale lock files
    (profile_dir / "SingletonLock").touch()
    (profile_dir / "SingletonSocket").touch()
    (profile_dir / "SingletonCookie").touch()

    locks_before = list(profile_dir.glob("Singleton*"))
    assert len(locks_before) == 3, "Should have 3 lock files"

    # Run cleanup
    builder = BrowserOptionsBuilder()
    builder._cleanup_stale_locks(profile_dir)

    # Locks should be removed (no process using them)
    locks_after = list(profile_dir.glob("Singleton*"))
    assert len(locks_after) == 0, "Stale locks should be removed"


def test_cleanup_stale_lock_symlinks(tmp_path: Path) -> None:
    """Test that stale lock symlinks (like Chrome creates) are removed."""
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()

    # Create symlinks like Chrome does (pointing to non-existent targets)
    (profile_dir / "SingletonLock").symlink_to("non-existent-target")
    (profile_dir / "SingletonSocket").symlink_to(tmp_path / "non-existent-socket")
    (profile_dir / "SingletonCookie").symlink_to("12345678901234567890")

    locks_before = list(profile_dir.glob("Singleton*"))
    assert len(locks_before) == 3, "Should have 3 lock symlinks"

    # Verify they're broken symlinks
    assert (profile_dir / "SingletonLock").is_symlink()
    assert not (profile_dir / "SingletonLock").exists()

    # Run cleanup
    builder = BrowserOptionsBuilder()
    builder._cleanup_stale_locks(profile_dir)

    # Broken symlinks should be removed
    locks_after = list(profile_dir.glob("Singleton*"))
    assert len(locks_after) == 0, "Stale lock symlinks should be removed"
