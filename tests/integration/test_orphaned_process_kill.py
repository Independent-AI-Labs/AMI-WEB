"""Test orphaned Chrome process detection and killing.

This test uses the saved session at browser/data/sessions/43cd2f3c-5661-4f05-8cb0-ebea2cba397f
which requires the 'default' profile. It verifies that BROWSER_KILL_ORPHANED=true
properly kills orphaned Chrome processes holding profile locks.
"""

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_orphaned_process_killed_with_env_var(tmp_path: Path) -> None:
    """Test that orphaned Chrome process is killed when BROWSER_KILL_ORPHANED=true."""
    # Use the existing saved session that requires the 'default' profile
    session_id = "43cd2f3c-5661-4f05-8cb0-ebea2cba397f"

    # Get the browser module root
    test_file = Path(__file__).resolve()
    browser_root = test_file.parent.parent.parent

    # Use absolute paths for storage directories
    session_dir = browser_root / "data" / "sessions"
    profiles_dir = browser_root / "data" / "profiles"

    # Verify the session exists
    session_file = session_dir / session_id / "session.json"
    assert session_file.exists(), f"Session {session_id} not found at {session_file}"

    # Find any orphaned Chrome processes using the default profile
    profile_dir = profiles_dir / "default"
    orphaned_pids = []

    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True, timeout=5)

        for line in result.stdout.splitlines():
            if "chrome" in line.lower() and str(profile_dir) in line:
                parts = line.split()
                if len(parts) >= 2:
                    orphaned_pids.append(int(parts[1]))
    except (subprocess.SubprocessError, ValueError):
        pass

    # If there are orphaned processes, this test will verify they get killed
    print(f"\nFound {len(orphaned_pids)} orphaned Chrome process(es) using default profile: {orphaned_pids}")

    # Set the environment variable to enable orphaned process killing
    os.environ["BROWSER_KILL_ORPHANED"] = "true"

    try:
        # Create manager with absolute storage paths
        config_overrides = {
            "backend.storage.session_dir": str(session_dir),
            "backend.storage.profiles_dir": str(profiles_dir),
        }

        manager = ChromeManager(config_overrides=config_overrides)
        await manager.initialize()

        # Try to restore the session - this should kill any orphaned process
        # and successfully launch a new browser with the profile
        instance = await manager.restore_session(session_id)

        # Verify instance is alive
        assert instance is not None
        assert instance.is_alive()

        # Verify the old orphaned processes are gone
        if orphaned_pids:
            for old_pid in orphaned_pids:
                try:
                    # Try to check if process still exists
                    os.kill(old_pid, 0)
                    # If we get here, process still exists - that's bad
                    pytest.fail(f"Orphaned process {old_pid} should have been killed but is still running")
                except ProcessLookupError:
                    # Process is gone - this is what we expect
                    print(f"✓ Orphaned process {old_pid} was successfully killed")

        # Terminate the instance
        await manager.terminate_instance(instance.id)
        await manager.shutdown()

    finally:
        # Clean up env var
        os.environ.pop("BROWSER_KILL_ORPHANED", None)


@pytest.mark.asyncio
async def test_orphaned_process_error_without_env_var(tmp_path: Path) -> None:
    """Test that restoring fails with helpful error when orphaned process exists and BROWSER_KILL_ORPHANED=false."""
    # Use the existing saved session that requires the 'default' profile
    session_id = "43cd2f3c-5661-4f05-8cb0-ebea2cba397f"

    # Get the browser module root
    test_file = Path(__file__).resolve()
    browser_root = test_file.parent.parent.parent

    # Use absolute paths for storage directories
    session_dir = browser_root / "data" / "sessions"
    profiles_dir = browser_root / "data" / "profiles"

    # Verify the session exists
    session_file = session_dir / session_id / "session.json"
    assert session_file.exists(), f"Session {session_id} not found at {session_file}"

    # First, create an orphaned process by launching and not properly terminating
    os.environ.pop("BROWSER_KILL_ORPHANED", None)  # Ensure it's not set

    config_overrides = {
        "backend.storage.session_dir": str(session_dir),
        "backend.storage.profiles_dir": str(profiles_dir),
    }

    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    # Launch with default profile
    _ = await manager1.get_or_create_instance(headless=True, profile="default", use_pool=False)

    # Get the PID of the Chrome process
    profile_dir = profiles_dir / "default"
    singleton_lock = profile_dir / "SingletonLock"

    # Force close manager without proper cleanup to create orphan
    # (simulate crash or abrupt termination)
    manager1._standalone_instances.clear()  # Remove tracking without cleanup
    await manager1.pool.shutdown()

    # Now try to restore session without BROWSER_KILL_ORPHANED set
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    # This should fail with a helpful error message
    with pytest.raises(RuntimeError) as exc_info:
        await manager2.restore_session(session_id)

    error_msg = str(exc_info.value)
    assert "locked" in error_msg.lower() or "orphaned" in error_msg.lower()
    assert "BROWSER_KILL_ORPHANED" in error_msg

    # Clean up - force kill the orphaned process
    if singleton_lock.exists() and singleton_lock.is_symlink():
        link_target = str(singleton_lock.readlink())
        if "-" in link_target:
            _, pid_str = link_target.rsplit("-", 1)
            pid = int(pid_str)
            try:
                os.kill(pid, 9)  # SIGKILL
                print(f"✓ Cleaned up orphaned process {pid}")
            except ProcessLookupError:
                pass

    await manager2.shutdown()


if __name__ == "__main__":
    import tempfile

    # Run the tests
    tmp_dir = Path(tempfile.gettempdir())
    asyncio.run(test_orphaned_process_killed_with_env_var(tmp_dir))
    asyncio.run(test_orphaned_process_error_without_env_var(tmp_dir))
