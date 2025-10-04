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
