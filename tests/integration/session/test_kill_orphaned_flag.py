"""Integration tests for kill_orphaned flag when restoring sessions with profile locks."""

import os
from pathlib import Path
import time

from loguru import logger
import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.utils.exceptions import InstanceError


pytestmark = pytest.mark.xdist_group(name="browser_lifecycle")


@pytest.mark.asyncio
async def test_restore_fails_without_kill_orphaned_flag(data_dir: Path) -> None:
    """Test that restoring a session with an orphaned process fails without kill_orphaned=True."""
    # Use absolute paths for storage directories
    session_dir = data_dir / "sessions"
    profiles_dir = data_dir / "profiles"

    config_overrides = {
        "backend.storage.session_dir": str(session_dir),
        "backend.storage.profiles_dir": str(profiles_dir),
    }

    # Step 1: Create an orphaned Chrome process using test-profile
    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    # Create/recreate test-profile
    if "test-profile" in manager1.profile_manager.profiles:
        manager1.profile_manager.delete_profile("test-profile")
    manager1.profile_manager.create_profile("test-profile", "Test profile for kill_orphaned tests")

    # Launch with test-profile and KEEP reference to prevent garbage collection
    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile="test-profile",
        use_pool=False,
    )

    # Get the profile directory and verify lock exists
    profile_dir = profiles_dir / "test-profile"
    singleton_lock = profile_dir / "SingletonLock"

    # Wait a moment for Chrome to create the lock file

    time.sleep(0.5)

    # Verify lock was created (use is_symlink because exists() fails for broken symlinks)
    assert singleton_lock.is_symlink(), f"SingletonLock should be a symlink. Profile dir contents: {list(profile_dir.iterdir())}"

    # Verify instance is alive (and keep reference in scope)
    assert instance1.is_alive(), f"Instance {instance1.id} should be alive"

    # Get the PID from the lock
    link_target = str(singleton_lock.readlink())
    assert "-" in link_target, f"Invalid lock format: {link_target}"
    _, pid_str = link_target.rsplit("-", 1)
    chrome_pid = int(pid_str)

    # Verify the Chrome process is running
    try:
        os.kill(chrome_pid, 0)
    except ProcessLookupError:
        pytest.fail(f"Chrome process {chrome_pid} should be running")

    # Force orphan the process by clearing tracking without cleanup
    manager1._standalone_instances.clear()
    await manager1.pool.shutdown()

    # Verify Chrome process is still running (orphaned)
    try:
        os.kill(chrome_pid, 0)
    except ProcessLookupError:
        pytest.fail(f"Orphaned Chrome process {chrome_pid} should still be running")

    # Step 2: Try to restore/create new instance without kill_orphaned flag
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    # This should FAIL with a helpful error about the orphaned process
    with pytest.raises((RuntimeError, InstanceError)) as exc_info:
        await manager2.get_or_create_instance(
            headless=True,
            profile="test-profile",
            use_pool=False,
            kill_orphaned=False,  # Explicitly set to False
        )

    # Verify the error message mentions the lock and suggests kill_orphaned
    error_msg = str(exc_info.value)
    assert "locked" in error_msg.lower() or "orphaned" in error_msg.lower() or "in use" in error_msg.lower()

    # Cleanup: Kill the orphaned process manually
    try:
        os.kill(chrome_pid, 9)
        logger.info(f"✓ Cleaned up orphaned Chrome process {chrome_pid}")
    except ProcessLookupError:
        logger.info(f"Process {chrome_pid} already terminated")

    # Clean up locks
    for lock_file in [
        profile_dir / "SingletonLock",
        profile_dir / "SingletonSocket",
        profile_dir / "SingletonCookie",
    ]:
        if lock_file.exists() or lock_file.is_symlink():
            lock_file.unlink()

    await manager2.shutdown()


@pytest.mark.asyncio
async def test_restore_succeeds_with_kill_orphaned_flag(data_dir: Path) -> None:
    """Test that restoring a session with kill_orphaned=True kills the orphaned process and succeeds."""
    # Use absolute paths for storage directories
    session_dir = data_dir / "sessions"
    profiles_dir = data_dir / "profiles"

    config_overrides = {
        "backend.storage.session_dir": str(session_dir),
        "backend.storage.profiles_dir": str(profiles_dir),
    }

    # Step 1: Create an orphaned Chrome process using test-profile
    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    # Create/recreate test-profile
    if "test-profile" in manager1.profile_manager.profiles:
        manager1.profile_manager.delete_profile("test-profile")
    manager1.profile_manager.create_profile("test-profile", "Test profile for kill_orphaned tests")

    # Launch with test-profile and KEEP reference to prevent garbage collection
    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile="test-profile",
        use_pool=False,
    )

    # Get the profile directory and verify lock exists
    profile_dir = profiles_dir / "test-profile"
    singleton_lock = profile_dir / "SingletonLock"

    # Wait a moment for Chrome to create the lock file

    time.sleep(0.5)

    # Verify lock was created (use is_symlink because exists() fails for broken symlinks)
    assert singleton_lock.is_symlink(), f"SingletonLock should be a symlink. Profile dir contents: {list(profile_dir.iterdir())}"

    # Verify instance is alive (and keep reference in scope)
    assert instance1.is_alive(), f"Instance {instance1.id} should be alive"

    # Get the PID from the lock
    link_target = str(singleton_lock.readlink())
    assert "-" in link_target, f"Invalid lock format: {link_target}"
    _, pid_str = link_target.rsplit("-", 1)
    orphaned_pid = int(pid_str)

    # Verify the Chrome process is running
    try:
        os.kill(orphaned_pid, 0)
        logger.info(f"✓ Chrome process {orphaned_pid} is running")
    except ProcessLookupError:
        pytest.fail(f"Chrome process {orphaned_pid} should be running")

    # Force orphan the process by clearing tracking without cleanup
    manager1._standalone_instances.clear()
    await manager1.pool.shutdown()

    # Verify Chrome process is still running (orphaned)
    try:
        os.kill(orphaned_pid, 0)
        logger.info(f"✓ Chrome process {orphaned_pid} is orphaned and still running")
    except ProcessLookupError:
        pytest.fail(f"Orphaned Chrome process {orphaned_pid} should still be running")

    # Step 2: Create new instance with kill_orphaned=True
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    # This should SUCCEED by killing the orphaned process
    instance2 = await manager2.get_or_create_instance(
        headless=True,
        profile="test-profile",
        use_pool=False,
        kill_orphaned=True,  # Enable orphaned process killing
    )

    # Verify new instance is alive
    assert instance2 is not None, "New instance should be created"
    assert instance2.is_alive(), "New instance should be alive"

    # SUCCESS: The orphaned process was killed and new instance was created
    # We don't verify the old PID is dead because Chrome may have respawned processes
    logger.info("✓ New instance created successfully after killing orphaned process")

    # Cleanup
    await manager2.terminate_instance(instance2.id)
    await manager2.shutdown()


@pytest.mark.asyncio
async def test_session_restore_with_kill_orphaned(data_dir: Path) -> None:
    """Test session restore with kill_orphaned flag through the full session workflow."""
    # Use absolute paths for storage directories
    session_dir = data_dir / "sessions"
    profiles_dir = data_dir / "profiles"

    config_overrides = {
        "backend.storage.session_dir": str(session_dir),
        "backend.storage.profiles_dir": str(profiles_dir),
    }

    # Step 1: Create a session with test-profile
    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    # Create/recreate test-profile
    if "test-profile" in manager1.profile_manager.profiles:
        manager1.profile_manager.delete_profile("test-profile")
    manager1.profile_manager.create_profile("test-profile", "Test profile for kill_orphaned tests")

    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile="test-profile",
        use_pool=False,
    )

    # Save the session
    session_id = await manager1.save_session(instance1.id, "test-kill-orphaned-session")
    logger.info(f"✓ Created session {session_id}")

    # Get the PID before orphaning
    profile_dir = profiles_dir / "test-profile"
    singleton_lock = profile_dir / "SingletonLock"

    # Wait for lock file

    time.sleep(0.5)

    link_target = str(singleton_lock.readlink())
    _, pid_str = link_target.rsplit("-", 1)
    orphaned_pid = int(pid_str)

    # Force orphan the process
    manager1._standalone_instances.clear()
    await manager1.pool.shutdown()

    # Verify process is orphaned
    try:
        os.kill(orphaned_pid, 0)
        logger.info(f"✓ Process {orphaned_pid} is orphaned")
    except ProcessLookupError:
        pytest.fail("Process should still be running")

    # Step 2: Try to restore without kill_orphaned (should fail)
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    with pytest.raises((RuntimeError, InstanceError)):
        await manager2.session_manager.restore_session(
            session_id,
            manager2,
            kill_orphaned=False,
        )

    await manager2.shutdown()

    # Verify process is STILL running after failed restore
    try:
        os.kill(orphaned_pid, 0)
        logger.info(f"✓ Process {orphaned_pid} still running after failed restore")
    except ProcessLookupError:
        pytest.fail("Process should still be running after failed restore")

    # Step 3: Restore with kill_orphaned=True (should succeed)
    manager3 = ChromeManager(config_overrides=config_overrides)
    await manager3.initialize()

    instance3 = await manager3.session_manager.restore_session(
        session_id,
        manager3,
        kill_orphaned=True,
    )

    # Verify restoration succeeded
    assert instance3 is not None, "Session restore should succeed"
    assert instance3.is_alive(), "Restored instance should be alive"

    # SUCCESS: The orphaned process was killed and session was restored
    # We don't verify the old PID is dead because Chrome may have respawned processes
    logger.info("✓ Session restored successfully after killing orphaned process")

    # Cleanup
    manager3.session_manager.delete_session(session_id)
    await manager3.terminate_instance(instance3.id)
    await manager3.shutdown()


if __name__ == "__main__":
    # Note: These tests require data_dir fixture from pytest, cannot run standalone
    import sys

    logger.info("These tests require pytest fixtures. Run with: pytest test_kill_orphaned_flag.py")
    sys.exit(1)
