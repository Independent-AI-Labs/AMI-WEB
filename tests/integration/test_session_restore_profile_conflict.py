"""Test session restore with profile already in use - reproduce the actual error."""

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_session_restore_with_profile_in_use() -> None:
    """Reproduce: session restore fails when profile is already in use by another instance."""

    manager = ChromeManager(config_file="config.test.yaml")
    await manager.initialize()

    try:
        # Create test profile
        manager.profile_manager.create_profile("conflict_test", "Test profile")

        # Launch instance 1 with the profile
        print("\n[1] Launching instance 1 with profile='conflict_test'...")
        instance1 = await manager.get_or_create_instance(headless=True, profile="conflict_test", use_pool=False)
        print(f"    Instance 1 ID: {instance1.id}")

        # Navigate somewhere
        assert instance1.driver is not None
        instance1.driver.get("https://www.google.com/")

        # Save session
        print("\n[2] Saving session...")
        session_id = await manager.save_session(instance1.id, "test_session")
        print(f"    Session ID: {session_id}")

        # DON'T terminate instance1 - keep it running

        # Try to restore the session (should reuse instance1, not create new one)
        print("\n[3] Attempting to restore session while instance 1 still running...")
        restored = await manager.session_manager.restore_session(
            session_id=session_id,
            manager=manager,
            profile_override=None,  # Use saved profile
        )

        print(f"    Restored instance ID: {restored.id}")
        print(f"    Same as instance 1? {restored.id == instance1.id}")

        # Clean up
        await instance1.terminate()

    except Exception as e:
        print(f"\nERROR TYPE: {type(e).__name__}")
        print(f"ERROR MESSAGE: {e}")
        raise

    finally:
        await manager.shutdown()
        manager.profile_manager.delete_profile("conflict_test")
