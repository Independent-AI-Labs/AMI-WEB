"""Integration test to verify instance reuse logic with profiles."""

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_instance_reuse_with_profile() -> None:
    """Test that manager reuses existing instances with the same profile."""

    # Initialize the manager
    manager = ChromeManager()
    await manager.initialize()

    try:
        # First call: create instance with profile="default"
        print("\n1. First call: get_or_create_instance(profile='default')")
        instance1 = await manager.get_or_create_instance(profile="default", headless=True)
        print(f"   - Instance ID: {instance1.id}")
        print(f"   - Profile: {instance1._profile_name}")
        print(f"   - Instance is alive: {instance1.is_alive()}")

        # Second call: get_or_create_instance with same profile="default"
        print("\n2. Second call: get_or_create_instance(profile='default')")
        instance2 = await manager.get_or_create_instance(profile="default", headless=True)
        print(f"   - Instance ID: {instance2.id}")
        print(f"   - Profile: {instance2._profile_name}")
        print(f"   - Instance is alive: {instance2.is_alive()}")

        # Check if they are the same instance
        print("\n3. Comparison:")
        print(f"   - Same instance object? {instance1 is instance2}")
        print(f"   - Same instance ID? {instance1.id == instance2.id}")

        # Check manager's standalone instances
        print("\n4. Manager state:")
        print(f"   - Standalone instances count: {len(manager._standalone_instances)}")
        print(f"   - Standalone instance IDs: {list(manager._standalone_instances.keys())}")

        # Assertions
        assert instance1 is instance2, "Should return the same instance object"
        assert instance1.id == instance2.id, "Should have the same instance ID"
        assert len(manager._standalone_instances) == 1, "Should have exactly one standalone instance"

        print("\n" + "=" * 80)
        print("FINDING: ✓ Manager CORRECTLY reuses the existing instance")
        print("         The same instance object was returned for both calls.")
        print("=" * 80)

    finally:
        # Cleanup
        print("\nCleaning up...")
        await manager.shutdown()
        print("Done.")
