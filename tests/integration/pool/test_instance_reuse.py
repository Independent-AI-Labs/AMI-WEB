"""Integration test to verify instance reuse logic with profiles."""

from loguru import logger
import pytest

from browser.backend.core.management.manager import ChromeManager


pytestmark = pytest.mark.xdist_group(name="browser_lifecycle")


@pytest.mark.asyncio
async def test_instance_reuse_with_profile() -> None:
    """Test that manager reuses existing instances with the same profile."""

    # Initialize the manager
    manager = ChromeManager()
    await manager.initialize()

    try:
        # First call: create instance with profile="default"
        logger.info("\n1. First call: get_or_create_instance(profile='default')")
        instance1 = await manager.get_or_create_instance(profile="default", headless=True)
        logger.info(f"   - Instance ID: {instance1.id}")
        logger.info(f"   - Profile: {instance1._profile_name}")
        logger.info(f"   - Instance is alive: {instance1.is_alive()}")

        # Second call: get_or_create_instance with same profile="default"
        logger.info("\n2. Second call: get_or_create_instance(profile='default')")
        instance2 = await manager.get_or_create_instance(profile="default", headless=True)
        logger.info(f"   - Instance ID: {instance2.id}")
        logger.info(f"   - Profile: {instance2._profile_name}")
        logger.info(f"   - Instance is alive: {instance2.is_alive()}")

        # Check if they are the same instance
        logger.info("\n3. Comparison:")
        logger.info(f"   - Same instance object? {instance1 is instance2}")
        logger.info(f"   - Same instance ID? {instance1.id == instance2.id}")

        # Check manager's standalone instances
        logger.info("\n4. Manager state:")
        logger.info(f"   - Standalone instances count: {len(manager._standalone_instances)}")
        logger.info(f"   - Standalone instance IDs: {list(manager._standalone_instances.keys())}")

        # Assertions
        assert instance1 is instance2, "Should return the same instance object"
        assert instance1.id == instance2.id, "Should have the same instance ID"
        assert len(manager._standalone_instances) == 1, "Should have exactly one standalone instance"

        logger.info("\n" + "=" * 80)
        logger.info("FINDING: ✓ Manager CORRECTLY reuses the existing instance")
        logger.info("         The same instance object was returned for both calls.")
        logger.info("=" * 80)

    finally:
        # Cleanup
        logger.info("\nCleaning up...")
        await manager.shutdown()
        logger.info("Done.")
