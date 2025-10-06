"""Test case to reproduce Chrome launch failure with profile conflicts."""

import pytest
from loguru import logger

from browser.backend.core.management.manager import ChromeManager


class TestProfileConflict:
    """Test to reproduce the 'user data directory is already in use' error."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_headless_pool_then_nonheadless_profile(self) -> None:
        """
        Reproduce: Launch headless Chrome from pool, then launch non-headless with profile.

        Expected: Should fail with "user data directory is already in use" if both
        instances try to use the same profile directory.

        This tests the scenario:
        1. Get instance from pool (headless=True, profile=None)
        2. Get instance with explicit profile (headless=True initially to test, profile="test_profile")
        """
        manager = ChromeManager(config_file="config.test.yaml")
        await manager.initialize()

        # Create test profile first
        test_profile_dir = manager.profile_manager.create_profile("test_profile", "Test profile for conflict testing")
        logger.info(f"Created test profile at: {test_profile_dir}")

        # Check if any pool instances are using this directory (they shouldn't be!)
        for worker_id, worker in manager.pool._workers.items():
            worker_profile = worker.instance._profile_name
            worker_temp = worker.instance._options_builder.get_temp_profile_dir()
            if worker_profile == "test_profile" or (worker_temp and "test_profile" in str(worker_temp)):
                logger.error(f"PROBLEM: Pool worker {worker_id} is using test_profile! profile={worker_profile}, temp={worker_temp}")
            else:
                logger.info(f"Pool worker {worker_id} OK: profile={worker_profile}, temp={worker_temp}")

        instance1 = None
        instance2 = None

        try:
            # Step 1: Launch headless instance from pool
            logger.info("=== Step 1: Launching headless instance from pool ===")

            # Check pool stats before
            pool_stats = await manager.get_pool_stats()
            logger.info(f"Pool stats before instance1: {pool_stats}")

            instance1 = await manager.get_or_create_instance(
                headless=True,
                profile=None,  # Use pool - should get temp directory
                use_pool=True,
                anti_detect=False,
            )
            logger.info(f"Instance 1 ID: {instance1.id}")
            logger.info(f"Instance 1 profile: {instance1._profile_name}")
            logger.info(f"Instance 1 temp dir: {instance1._options_builder.get_temp_profile_dir()}")

            # List all pool instances
            for worker_id, worker in manager.pool._workers.items():
                logger.info(
                    f"Pool worker {worker_id}: profile={worker.instance._profile_name}, temp_dir={worker.instance._options_builder.get_temp_profile_dir()}"
                )

            # Step 2: Launch non-headless instance with explicit profile
            logger.info("=== Step 2: Launching non-headless instance with profile ===")

            # Check if test_profile directory exists and if it has any locks
            import subprocess

            profile_dir = manager.profile_manager.base_dir / "test_profile"
            logger.info(f"Profile directory exists: {profile_dir.exists()}")
            if profile_dir.exists():
                lock_files = list(profile_dir.glob("Singleton*"))
                logger.info(f"Lock files in profile: {lock_files}")
                # Check if any process is using the directory
                result = subprocess.run(["fuser", str(profile_dir)], capture_output=True, text=True, timeout=2, check=False)
                logger.info(f"fuser result: returncode={result.returncode}, " f"stdout={result.stdout.strip()}, stderr={result.stderr.strip()}")

            instance2 = await manager.get_or_create_instance(
                headless=True,  # Try headless first to see if it's a headless vs non-headless issue
                profile="test_profile",  # Explicit profile - should NOT use pool
                use_pool=False,  # Forced standalone for profiles
                anti_detect=False,
            )
            logger.info(f"Instance 2 ID: {instance2.id}")
            logger.info(f"Instance 2 profile: {instance2._profile_name}")
            logger.info(f"Instance 2 temp dir: {instance2._options_builder.get_temp_profile_dir()}")

            # If we get here without error, instances are properly isolated
            assert instance1.id != instance2.id, "Instances should have different IDs"
            assert instance1._profile_name is None, "Instance 1 should not have a profile"
            assert instance2._profile_name == "test_profile", "Instance 2 should have test_profile"

            # Verify both instances are alive
            assert instance1.is_alive(), "Instance 1 should be alive"
            assert instance2.is_alive(), "Instance 2 should be alive"

            logger.info("=== SUCCESS: Both instances launched without conflict ===")

        except Exception as e:
            logger.error(f"=== FAILURE: {type(e).__name__}: {e} ===")
            raise

        finally:
            # Clean up
            if instance1:
                await instance1.terminate()
            if instance2:
                await instance2.terminate()

            # Clean up test profile
            manager.profile_manager.delete_profile("test_profile")

            await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
