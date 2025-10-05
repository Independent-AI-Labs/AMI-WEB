"""Test restoring a non-existent session to reproduce the error."""

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_restore_nonexistent_session() -> None:
    """Test that restoring a non-existent session produces the correct error."""

    manager = ChromeManager(config_file="config.test.yaml")
    await manager.initialize()

    try:
        # Try to restore a session that doesn't exist
        print("\nAttempting to restore non-existent session...")
        await manager.session_manager.restore_session(session_id="nonexistent-session-id-12345", manager=manager, profile_override="default")

        # If we get here, the test failed
        pytest.fail("Expected SessionError but restore succeeded")

    except Exception as e:
        print(f"\nERROR TYPE: {type(e).__name__}")
        print(f"ERROR MESSAGE: {e}")

    finally:
        await manager.shutdown()
